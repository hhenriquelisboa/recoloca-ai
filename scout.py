#!/usr/bin/env python3
"""
Scout — Agente de Busca de Vagas (sub-agente despachado pelo Gilbert)
Recebe envelope de despacho, executa Firecrawl, aplica skills-metric, retorna JSON.
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"

def run_firecrawl_search(query: str, limit: int = 10) -> List[Dict]:
    """Executa firecrawl search e retorna lista de resultados."""
    firecrawl_path = "/c/nvm4w/nodejs/firecrawl"
    cmd = ["bash", firecrawl_path, "search", query, "--limit", str(limit), "--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return [{"error": f"Firecrawl search failed: {result.stderr}"}]
        data = json.loads(result.stdout)
        # Firecrawl retorna: {"success": true, "data": {"web": [...]}}
        if data.get("success") and "data" in data and "web" in data["data"]:
            return data["data"]["web"]
        return []
    except subprocess.TimeoutExpired:
        return [{"error": "Firecrawl search timeout"}]
    except json.JSONDecodeError:
        return [{"error": f"Firecrawl output not JSON: {result.stdout[:200]}"}]
    except Exception as e:
        return [{"error": f"Firecrawl exception: {e}"}]

def run_firecrawl_scrape(url: str) -> Dict:
    """Executa firecrawl scrape para obter detalhes da vaga."""
    firecrawl_path = "/c/nvm4w/nodejs/firecrawl"
    cmd = ["bash", firecrawl_path, "scrape", url, "--format", "markdown", "--only-main-content"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return {"error": f"Scrape failed: {result.stderr}", "content": ""}
        return {"content": result.stdout, "error": None}
    except subprocess.TimeoutExpired:
        return {"error": "Scrape timeout", "content": ""}
    except Exception as e:
        return {"error": f"Scrape exception: {e}", "content": ""}

def check_link_status(url: str) -> str:
    """Verifica HTTP status do link (200, 403, 429, etc.)."""
    try:
        import requests
        r = requests.head(url, allow_redirects=True, timeout=10)
        return str(r.status_code)
    except Exception:
        return "unknown"

# ─── Indeed jk= link converter ───
def convert_indeed_link(url: str) -> str:
    """Converte link Indeed jk= para URL do anúncio direto se possível."""
    parsed = urlparse(url)
    if "indeed" not in parsed.netloc:
        return url
    
    qs = parse_qs(parsed.query)
    if "jk" in qs:
        jk = qs["jk"][0]
        # Tenta construir URL do anúncio direto
        # indeed.com/viewjob?jk=XXXX
        new_query = urlencode({"jk": jk}, doseq=True)
        new_parsed = parsed._replace(path="/viewjob", query=new_query)
        return urlunparse(new_parsed)
    return url

def extract_job_urls_from_search_page(content: str, base_domain: str) -> List[str]:
    """Extrai URLs de vagas individuais de uma página de busca."""
    urls = []
    # Padrões comuns para links de vagas
    patterns = [
        r'href=["\'](/job/[^"\']+)["\']',
        r'href=["\'](/position/[^"\']+)["\']',
        r'href=["\'](/vacancy/[^"\']+)["\']',
        r'href=["\'](/career/[^"\']+)["\']',
        r'href=["\'](/emprego/[^"\']+)["\']',
        r'href=["\'](/viewjob\?jk=[^"\']+)["\']',
        r'href=["\'](https://[^"\']+/job/[^"\']+)["\']',
        r'href=["\'](https://[^"\']+/position/[^"\']+)["\']',
        r'href=["\'](https://[^"\']+/vacancy/[^"\']+)["\']',
    ]
    for pat in patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        for m in matches:
            if m.startswith("http"):
                urls.append(m)
            elif m.startswith("/"):
                urls.append(f"https://{base_domain}{m}")
    return list(set(urls))

def is_search_page(url: str) -> bool:
    """Detecta se é página de busca (lista) vs anúncio individual."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    netloc = parsed.netloc.lower()
    
    # Páginas de busca têm padrões específicos
    search_patterns = [
        "/jobs", "/q-", "/search", "/ofertas", "/vagas", "/empregos",
        "/srch_il", "/job/search", "/jobs/search", "/list", "/browse",
        "/jobs/",  # Glassdoor /Job/... search pages
    ]
    # Páginas de anúncio individual - padrões mais específicos
    job_patterns = [
        "/viewjob", 
        "/job/",  # generic but need to exclude search
        "/position/", 
        "/vacancy/", 
        "/career/", 
        "/emprego/",
        "/job-",  # job-12345
        "/vaga-",
    ]
    
    # Verifica se é claramente uma página de busca
    is_search = any(p in path for p in search_patterns)
    
    # Verifica se é claramente um anúncio individual
    # Mas exclui se for padrão de busca do Glassdoor (/Job/...SRCH...)
    if "glassdoor" in netloc and "/job/" in path and "srch" in path.lower():
        return True
    if "linkedin" in netloc and "/jobs/" in path and ("search" in path or "guest" in path):
        return True
    
    is_job = any(p in path for p in job_patterns)
    
    # Se tem padrão de job E não é busca, é anúncio
    if is_job and not is_search:
        return False
    return is_search

def load_skills_metric() -> Dict:
    weights = {
        "nivel": 0.20,
        "ia": 0.15,
        "tecnica": 0.15,
        "localizacao": 0.10,
        "salario": 0.10,
        "capacitacao": 0.15,
        "link": 0.05,
    }
    return weights

def extract_salary_from_text(text: str) -> str:
    """Extrai menção de salário do texto."""
    patterns = [
        r"€\s*[\d,.]+\s*[–-]\s*€?\s*[\d,.]+",  # €1200–€2000
        r"€\s*[\d,.]+\s*[–-]\s*[\d,.]+",        # €1200–2000
        r"[\d,.]+\s*[–-]\s*[\d,.]+\s*€",        # 1200–2000€
        r"salário[:\s]*€?\s*[\d,.]+",            # salário: €1500
        r"salary[:\s]*€?\s*[\d,.]+",             # salary: €1500
        r"remunera[çc][ao][:\s]*€?\s*[\d,.]+",  # remuneração: €1500
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return ""

def extract_requirements(text: str) -> List[str]:
    """Extrai requisitos técnicos do texto da vaga."""
    tech_keywords = [
        "python", "sql", "javascript", "typescript", "java", "c#", "go", "rust",
        "react", "vue", "angular", "node", "django", "flask", "fastapi",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "machine learning", "ml", "ai", "llm", "pytorch", "tensorflow",
        "pandas", "numpy", "spark", "kafka", "redis", "postgresql", "mysql",
        "git", "ci/cd", "jenkins", "github actions", "gitlab",
        "tableau", "power bi", "looker", "excel", "powerpoint",
        "photoshop", "figma", "jira", "confluence",
    ]
    found = []
    text_lower = text.lower()
    for kw in tech_keywords:
        if kw in text_lower:
            found.append(kw)
    return list(set(found))

def score_vaga(vaga: Dict, profile: Dict, weights: Dict) -> Dict:
    descricao = (vaga.get("description") or vaga.get("markdown") or "").lower()
    titulo = (vaga.get("titulo") or vaga.get("title") or "").lower()
    localizacao_vaga = (vaga.get("localizacao") or vaga.get("location") or "").lower()
    salary_text = (vaga.get("salary") or extract_salary_from_text(descricao) or "").lower()
    
    # Perfil do usuário
    habilidades_user = [h.strip().lower() for h in profile.get("Habilidades técnicas", "").split(",") if h.strip()]
    area_user = profile.get("Área de interesse", "").lower()
    nivel_user = profile.get("Nível de experiência", "").lower()
    localizacao_user = profile.get("Localização", "").lower()
    
    # Fator 1: Nível (entry/junior = 10, pleno = 5, senior = 3)
    nivel_score = 3
    if any(w in titulo for w in ["junior", "júnior", "entry", "graduation", "graduate", "estágio", "trainee", "iniciante"]):
        nivel_score = 10
    elif any(w in titulo for w in ["pleno", "mid", "middle", "intermediário"]):
        nivel_score = 5
    elif any(w in titulo for w in ["senior", "sênior", "lead", "principal", "staff"]):
        nivel_score = 3
    
    # Fator 2: Uso de IA (mais inclusivo)
    ia_score = 0
    ia_strong = ["ai engineer", "machine learning engineer", "ml engineer", "llm", "genai", "generative ai", "ia engineer", "engenheiro de ia", "ai developer", "desenvolvedor ia"]
    ia_medium = ["ai ", "artificial intelligence", "machine learning", "data scientist", "cientista de dados", "ml ", "inteligência artificial", "deep learning", "nlp", "computer vision"]
    ia_weak = ["ia", "ai", "dados", "data", "analytics", "análise"]
    # Graduate programmes often have AI/data tracks
    grad_keywords = ["graduate programme", "graduation program", "programa de graduação", "graduate", "trainee"]
    
    if any(w in titulo for w in ia_strong):
        ia_score = 10
    elif any(w in titulo + " " + descricao[:500] for w in ia_medium):
        ia_score = 7
    elif any(w.lower() in (titulo + " " + descricao).lower() for w in grad_keywords):
        ia_score = 6  # Graduate programmes often have AI/data tracks
    elif any(w in descricao for w in ia_weak):
        ia_score = 4
    
    # Fator 3: Correspondência técnica (mais generosa com skills relacionadas)
    # Mapeamento de skills relacionadas
    skill_aliases = {
        "análise de dados": ["data analysis", "data analytics", "análise de dados", "analytics", "pandas", "numpy"],
        "python": ["python", "pandas", "numpy", "django", "flask", "fastapi"],
        "sql": ["sql", "postgresql", "mysql", "database", "banco de dados"],
        "ai": ["ai", "ia", "machine learning", "ml", "deep learning", "llm", "genai"],
        "pacote office": ["excel", "powerpoint", "word", "office", "spreadsheet"],
        "photoshop": ["photoshop", "figma", "design", "adobe"],
    }
    
    tech_matches = 0
    for h in habilidades_user:
        if not h:
            continue
        h_lower = h.lower()
        # Match direto
        if h_lower in descricao:
            tech_matches += 1
        # Match por alias
        elif h_lower in skill_aliases:
            if any(alias in descricao for alias in skill_aliases[h_lower]):
                tech_matches += 1
    
    tech_total = len(habilidades_user)
    tech_score = min(10, int((tech_matches / max(1, tech_total)) * 10)) if tech_total > 0 else 0
    
    # Fator 4: Localização
    loc_score = 3
    if "remoto" in localizacao_vaga or "remote" in localizacao_vaga or "híbrido" in localizacao_vaga or "hybrid" in localizacao_vaga:
        loc_score = 10
    elif "setúbal" in localizacao_vaga or "sul" in localizacao_vaga:
        loc_score = 10
    elif "lisboa" in localizacao_vaga:
        loc_score = 5
    elif "porto" in localizacao_vaga:
        loc_score = 5
    
    # Fator 5: Salário (mais leniente - a maioria não lista salário em Portugal)
    sal_score = 5  # Default neutro já que a maioria não divulga
    salary_text = (vaga.get("salary") or extract_salary_from_text(descricao) or "").lower()
    sal_numbers = re.findall(r"(\d{3,5})", salary_text)
    if sal_numbers:
        try:
            sal_min = min(int(n) for n in sal_numbers)
            if sal_min <= 1500:
                sal_score = 10
            elif sal_min <= 2000:
                sal_score = 7
            elif sal_min <= 3000:
                sal_score = 5
            else:
                sal_score = 3
        except:
            pass
    
    # Fator 6: Capacitação (mais inclusivo)
    cap_score = 0
    cap_strong = ["graduate programme", "graduation program", "programa de graduação", "programa de trainee", "formação paga", "capacitação", "mentoria", "onboarding", "training program", "desenvolvimento de carreira", "plano de carreira"]
    cap_medium = ["aprendizado", "desenvolvimento profissional", "crescimento", "certificação", "curso", "bootcamp", "treinamento", "learning", "development"]
    
    if any(w in descricao for w in cap_strong):
        cap_score = 10
    elif any(w in descricao for w in cap_medium):
        cap_score = 6
    
    # Fator 7: Link
    link_status = vaga.get("link_status", "unknown")
    link_score = 5 if link_status == "200" else (3 if link_status in ("301", "302") else 0)
    
    # Score final
    raw_score = (
        nivel_score * weights["nivel"] +
        ia_score * weights["ia"] +
        tech_score * weights["tecnica"] +
        loc_score * weights["localizacao"] +
        sal_score * weights["salario"] +
        cap_score * weights["capacitacao"] +
        link_score * weights["link"]
    )
    final_score = int(raw_score * 10)
    
    # Filtros
    filtros = []
    if nivel_score >= 8: filtros.append("entrada")
    if ia_score >= 8: filtros.append("IA")
    if cap_score >= 8: filtros.append("capacitacao")
    filtro_str = "|".join(filtros) if filtros else "outro"
    
    return {
        **vaga,
        "score_metrics": final_score,
        "filtro": filtro_str,
        "nivel_score": nivel_score,
        "ia_score": ia_score,
        "tech_score": tech_score,
        "loc_score": loc_score,
        "sal_score": sal_score,
        "cap_score": cap_score,
        "link_score": link_score,
        "status_link": link_status,
        "extracted_salary": extract_salary_from_text(descricao),
        "extracted_requirements": extract_requirements(descricao),
    }

def parse_profile(profile_text: str) -> Dict:
    """Parse user-profile.md para dict."""
    data = {}
    for line in profile_text.splitlines():
        if ":" in line and not line.startswith("#"):
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    return data

def run_scout(dispatch_envelope: Dict) -> Dict:
    """Executa o fluxo completo do Scout."""
    profile_text = dispatch_envelope.get("perfil_usuario", "")
    context = dispatch_envelope.get("contexto", "")
    profile = parse_profile(profile_text)
    weights = load_skills_metric()
    
    # Extrai termos de busca do contexto
    area = ""
    localizacao = ""
    for line in context.splitlines():
        if line.startswith("Área:"):
            area = line.split(":", 1)[1].strip()
        elif line.startswith("Localização:"):
            localizacao = line.split(":", 1)[1].strip()
    
    # Monta queries otimizadas para vagas individuais (simples, sem site: que pode não funcionar bem)
    area_main = area.split(",")[0].strip() if area else "tecnologia"
    queries = [
        f"{area_main} junior Portugal",
        f"remote AI engineer Portugal junior",
        f"junior backend developer Portugal",
        f"junior data analyst Portugal remoto",
        f"graduate programme technology Portugal",
        f"trainee program technology Portugal",
        f"site:volkswagen-group.com junior AI data engineer",
        f"site:accenture.com graduate programme Portugal",
        f"site:nokia.com graduate programme Portugal",
        f"site:sodexo.com data analyst Portugal",
    ]
    
    all_results = []
    seen = set()  # Inicializa aqui para usar na extração de jk codes
    for q in queries[:6]:  # Aumenta para 6 queries
        raw_results = run_firecrawl_search(q, limit=5)  # Reduz limite
        if raw_results and not (len(raw_results) == 1 and "error" in raw_results[0]):
            all_results.extend(raw_results)
        time.sleep(1)  # Rate limit amigável
    
    # Extrai códigos jk= do Indeed diretamente dos resultados de busca
    # Muitas vezes a descrição já contém links viewjob?jk=
    for item in all_results:
        desc = item.get("description", "") or item.get("markdown", "")
        if "indeed" in (item.get("url", "") or item.get("link", "") or ""):
            jk_codes = re.findall(r'jk=([a-f0-9]{16})', desc)
            for jk in jk_codes[:3]:
                job_url = f"https://pt.indeed.com/viewjob?jk={jk}"
                if job_url not in seen:
                    all_results.append({"url": job_url, "link": job_url, "title": item.get("title", "Vaga Indeed"), "source": "Indeed (extraída)", "location": item.get("location", "")})
                    seen.add(job_url)
    
    # Domínios de job boards confiáveis + páginas de carreira de empresas
    JOB_BOARD_DOMAINS = [
        "linkedin.com", "glassdoor.com", "indeed.com", "remoterocketship.com",
        "crossover.com", "wellfound.com", "teamlyzer.com", "startup-insider.com",
        "builtin.com", "randstad.pt", "sapo.pt", "net-empregos.com",
        "itjobs.pt", "landing.jobs", "volkswagen-group.com", "accenture.com",
        "nokia.com", "sodexo.com", "iepf.pt",
        "jobs.volkswagen-group.com", "careers.volkswagen-group.com",
        "careers.accenture.com", "jobs.accenture.com",
        "careers.nokia.com", "jobs.nokia.com",
        "careers.sodexo.com", "jobs.sodexo.com",
    ]
    
    def is_job_board(url: str) -> bool:
        return any(domain in url.lower() for domain in JOB_BOARD_DOMAINS)
    
    # Filtra job boards + converte Indeed
    filtered = []
    search_page_urls = []  # URLs de páginas de busca para extrair vagas individuais
    for r in all_results:
        url = r.get("url") or r.get("link") or ""
        if not url or not is_job_board(url):
            continue
        # Converte Indeed jk=
        url = convert_indeed_link(url)
        r["url"] = url
        r["link"] = url
        # Separa páginas de busca para extrair vagas individuais depois
        if is_search_page(url):
            search_page_urls.append(url)
            continue
        filtered.append(r)
    
    # Extrai URLs de vagas individuais das páginas de busca (especialmente Indeed)
    for search_url in search_page_urls[:3]:  # Limita a 3 páginas de busca
        scrape_result = run_firecrawl_scrape(search_url)
        if not scrape_result.get("error"):
            content = scrape_result.get("content", "")
            parsed = urlparse(search_url)
            base_domain = parsed.netloc
            job_urls = extract_job_urls_from_search_page(content, base_domain)
            
            # Também extrai códigos jk= do Indeed das descrições
            if "indeed" in base_domain:
                jk_codes = re.findall(r'jk=([a-f0-9]{16})', content)
                for jk in jk_codes[:10]:
                    job_url = f"https://{base_domain}/viewjob?jk={jk}"
                    if job_url not in seen:
                        job_urls.append(job_url)
            
            for job_url in job_urls[:5]:  # Max 5 vagas por página de busca
                if is_job_board(job_url) and job_url not in seen:
                    filtered.append({"url": job_url, "link": job_url, "title": "Vaga extraída de busca", "source": "Extraída", "location": ""})
                    seen.add(job_url)
        time.sleep(1)
    
    # Dedupe (seen já foi inicializado acima)
    deduped = []
    for item in filtered:
        url = item.get("url") or item.get("link") or ""
        if url and url not in seen:
            seen.add(url)
            deduped.append(item)
    raw_results = deduped[:12]  # Limita para não estourar tempo
    
    if not raw_results or (len(raw_results) == 1 and "error" in raw_results[0]):
        return {
            "estado": "erro",
            "resumo": f"Falha na busca: {raw_results[0].get('error', 'sem resultados')}",
            "dados": [],
            "erros": [raw_results[0].get('error', 'Busca retornou vazio')],
        }
    
    # Processa cada resultado
    vagas_processadas = []
    for item in raw_results[:10]:
        url = item.get("url") or item.get("link") or ""
        if not url:
            continue
        
        # Verifica link
        link_status = check_link_status(url)
        if link_status in ("403", "429"):
            # Tenta novamente após espera
            time.sleep(30)
            link_status = check_link_status(url)
        
        # Scrape para detalhes
        scrape_result = run_firecrawl_scrape(url)
        descricao = scrape_result.get("content", "") if not scrape_result.get("error") else ""
        
        vaga_base = {
            "titulo": item.get("title", "Sem título"),
            "empresa": item.get("source", "Desconhecida"),
            "localizacao": item.get("location", "Não informada"),
            "link": url,
            "description": descricao,
            "salary": item.get("salary", ""),
            "link_status": link_status,
        }
        
        vaga_scored = score_vaga(vaga_base, profile, weights)
        
        # Extrai habilidades correspondentes/faltantes
        desc_lower = descricao.lower()
        habilidades_user = [h.strip().lower() for h in profile.get("Habilidades técnicas", "").split(",") if h.strip()]
        correspondentes = [h for h in habilidades_user if h in desc_lower]
        faltantes = [h for h in habilidades_user if h not in desc_lower]
        
        vaga_final = {
            "titulo": vaga_scored["titulo"],
            "empresa": vaga_scored["empresa"],
            "localizacao": vaga_scored["localizacao"],
            "link": vaga_scored["link"],
            "habilidades_correspondentes": correspondentes,
            "habilidades_faltantes": faltantes,
            "contagem_correspondencia": f"{len(correspondentes)} de {len(habilidades_user)}",
            "score_metrics": vaga_scored["score_metrics"],
            "filtro": vaga_scored["filtro"],
            "status_link": vaga_scored["status_link"],
            "salario_extraido": vaga_scored.get("extracted_salary", ""),
            "requisitos_extraidos": vaga_scored.get("extracted_requirements", []),
        }
        vagas_processadas.append(vaga_final)
    
    # Filtra score >= 58 (prático para dados reais) e ordena
    vagas_filtradas = [v for v in vagas_processadas if v["score_metrics"] >= 58]
    vagas_filtradas.sort(key=lambda x: x["score_metrics"], reverse=True)
    top_vagas = vagas_filtradas[:5]
    
    debug_scores = [(v["titulo"], v["score_metrics"], v["filtro"]) for v in vagas_processadas]
    
    return {
        "estado": "sucesso" if top_vagas else "erro",
        "resumo": f"Encontradas {len(top_vagas)} vagas compatíveis (score ≥ 58) de {len(vagas_processadas)} analisadas. Scores: {debug_scores}",
        "dados": top_vagas,
        "erros": [] if top_vagas else ["Nenhuma vaga atingiu score mínimo 58"],
    }

def main():
    """Entry point para teste direto ou chamado via delegate_task."""
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Teste rápido com perfil mock
        profile_mock = """# Perfil do Usuário
Área de interesse: AI, backend, análise de dados
Nível de experiência: Em transição de carreira com experiência operacional logística na Ceva Logistics/3M Sumare SP
Habilidades técnicas: AI, Python, SQL, Análise de dados, Pacote Office, Photoshop
Preferências de trabalho: Híbrido e remoto
Localização: Setúbal e região Sul
Proficiência em inglês: Avançado (intermediário em espanhol, nativo em português)
Tipo de empresa: Sim
Expectativa salarial: 1500€
Disponibilidade para mudança: Não
Portfólio/certificações: Estudando na Alura (backend) e Prepara Portugal (análise de dados)
Concluído: true"""
        
        envelope = {
            "perfil_usuario": profile_mock,
            "contexto": "Área: AI, backend, análise de dados\nLocalização: Setúbal e região Sul\nNível: transição de carreira\nHabilidades: AI, Python, SQL, Análise de dados",
        }
        result = run_scout(envelope)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Modo produção: lê envelope do stdin (JSON)
        import sys
        envelope = json.load(sys.stdin)
        result = run_scout(envelope)
        print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()