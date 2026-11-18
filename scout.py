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
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

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

def load_skills_metric() -> Dict:
    """Carrega e parseia skills-metric.md para pesos."""
    content = (DATA_DIR / "skills-metric.md").read_text(encoding="utf-8")
    # Parse simples da tabela de fatores
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

def score_vaga(vaga: Dict, profile: Dict, weights: Dict) -> Dict:
    """Aplica skills-metric.md a uma vaga. Retorna vaga com score e fatores."""
    # Extrai requisitos da vaga (do scrape ou busca)
    descricao = (vaga.get("description") or vaga.get("markdown") or "").lower()
    titulo = (vaga.get("title") or "").lower()
    empresa = (vaga.get("source") or vaga.get("url") or "").lower()
    localizacao_vaga = (vaga.get("location") or "").lower()
    
    # Perfil do usuário
    habilidades_user = [h.strip().lower() for h in profile.get("Habilidades técnicas", "").split(",")]
    area_user = profile.get("Área de interesse", "").lower()
    nivel_user = profile.get("Nível de experiência", "").lower()
    localizacao_user = profile.get("Localização", "").lower()
    salario_user = profile.get("Expectativa salarial", "").lower()
    
    # Fator 1: Nível (entry/junior = 10, pleno = 5, senior = 3)
    nivel_score = 3
    if any(w in titulo for w in ["junior", "júnior", "entry", "graduation", "graduate", "estágio", "trainee"]):
        nivel_score = 10
    elif any(w in titulo for w in ["pleno", "mid", "middle"]):
        nivel_score = 5
    
    # Fator 2: Uso de IA
    ia_score = 0
    if any(w in titulo + " " + descricao for w in ["ai engineer", "machine learning", "ia ", "inteligência artificial", "llm", "genai", "generative ai"]):
        ia_score = 10
    elif any(w in titulo + " " + descricao for w in ["ai", "artificial intelligence", "dados", "data scientist", "ml"]):
        ia_score = 6
    elif "ia" in descricao or "ai" in descricao:
        ia_score = 3
    
    # Fator 3: Correspondência técnica
    tech_matches = sum(1 for h in habilidades_user if h and h in descricao)
    tech_total = len([h for h in habilidades_user if h])
    tech_score = min(10, int((tech_matches / max(1, tech_total)) * 10)) if tech_total > 0 else 0
    
    # Fator 4: Localização
    loc_score = 3
    if "remoto" in localizacao_vaga or "remote" in localizacao_vaga:
        loc_score = 10
    elif "setúbal" in localizacao_vaga or "sul" in localizacao_vaga:
        loc_score = 10
    elif "lisboa" in localizacao_vaga or "porto" in localizacao_vaga:
        loc_score = 5
    
    # Fator 5: Salário
    sal_score = 3
    salario_text = str(vaga.get("salary", "")).lower()
    if "1500" in salario_text or "1200" in salario_text or "1300" in salario_text or "1400" in salario_text:
        sal_score = 10
    elif any(s in salario_text for s in ["2000", "2500", "3000"]):
        sal_score = 5
    
    # Fator 6: Capacitação
    cap_score = 0
    if any(w in descricao for w in ["graduate programme", "graduation", "training", "formação", "capacitação", "mentor", "onboarding", "programa de"]):
        cap_score = 10
    elif any(w in descricao for w in ["aprendizado", "desenvolvimento", "crescimento"]):
        cap_score = 5
    
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
    
    # Filtro
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
    
    # Monta query - usa múltiplas queries específicas como no original
    # Extrai área principal (primeira palavra antes de vírgula)
    area_main = area.split(",")[0].strip() if area else "tecnologia"
    queries = []
    if area_main:
        queries.append(f"{area_main} Portugal")
    queries.append("remote AI engineer Portugal")
    queries.append("remote backend developer Portugal")
    queries.append("junior AI engineer Portugal")
    queries.append("junior backend developer Portugal")
    queries.append("data analyst Portugal remoto")
    queries.append("junior data analyst Portugal")
    
    all_results = []
    for q in queries[:5]:  # limita a 5 queries
        raw_results = run_firecrawl_search(q, limit=8)
        if raw_results and not (len(raw_results) == 1 and "error" in raw_results[0]):
            all_results.extend(raw_results)
    
    # Domínios de job boards confiáveis
    JOB_BOARD_DOMAINS = [
        "linkedin.com", "glassdoor.com", "indeed.com", "remoterocketship.com",
        "crossover.com", "wellfound.com", "teamlyzer.com", "startup-insider.com",
        "builtin.com", "randstad.pt", "sapo.pt", "net-empregos.com",
        "itjobs.pt", "landing.jobs", "volkswagen-group.com", "accenture.com",
        "nokia.com", "sodexo.com", "iepf.pt",
    ]
    
    def is_job_board(url: str) -> bool:
        return any(domain in url.lower() for domain in JOB_BOARD_DOMAINS)
    
    # Filtra apenas job boards
    raw_results = [r for r in raw_results if is_job_board(r.get("url", "") or r.get("link", ""))]
    
    # Dedupe por URL
    seen = set()
    deduped = []
    for item in raw_results:
        url = item.get("url") or item.get("link") or ""
        if url and url not in seen:
            seen.add(url)
            deduped.append(item)
    raw_results = deduped
    
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
            import time
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
        }
        vagas_processadas.append(vaga_final)
    
    # Filtra score >= 45 (temporário para demo) e ordena
    vagas_filtradas = [v for v in vagas_processadas if v["score_metrics"] >= 45]
    vagas_filtradas.sort(key=lambda x: x["score_metrics"], reverse=True)
    top_vagas = vagas_filtradas[:5]
    
    # Debug: mostra scores de todas
    debug_scores = [(v["titulo"], v["score_metrics"], v["filtro"]) for v in vagas_processadas]
    
    return {
        "estado": "sucesso" if top_vagas else "erro",
        "resumo": f"Encontradas {len(top_vagas)} vagas compatíveis (score ≥ 45) de {len(vagas_processadas)} analisadas. Scores: {debug_scores}",
        "dados": top_vagas,
        "erros": [] if top_vagas else ["Nenhuma vaga atingiu score mínimo 45"],
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