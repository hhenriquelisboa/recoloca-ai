#!/usr/bin/env python3
"""
Gilbert — Orquestrador (CLI fiel ao Zed)
Carrega personas/skills, gerencia quiz/perfil, despacha Scout via subprocess (equivalente a delegate_task).
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# ─── Config ───
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PERSONAS_DIR = ROOT / "personas"
SKILLS_DIR = ROOT / "skills"

# ─── Utilidades de leitura ───
def read_md(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

def load_user_profile() -> str:
    return read_md(DATA_DIR / "user-profile.md")

def load_quiz() -> str:
    return read_md(DATA_DIR / "personality-quiz.md")

def save_quiz(content: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "personality-quiz.md").write_text(content, encoding="utf-8")

def save_user_profile(content: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "user-profile.md").write_text(content, encoding="utf-8")

def quiz_is_complete(quiz_content: str) -> bool:
    return "Concluído: true" in quiz_content

def parse_quiz(quiz_content: str) -> Dict[str, str]:
    """Extrai campos do quiz (formato chave: valor)."""
    data = {}
    for line in quiz_content.splitlines():
        if ":" in line and not line.startswith("#"):
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    return data

def build_user_profile_from_quiz(quiz_data: Dict[str, str]) -> str:
    """Gera user-profile.md a partir do quiz + mapeamento de funções alvo."""
    area = quiz_data.get("Área de interesse", "").lower()
    nivel = quiz_data.get("Nível de experiência", "").lower()
    
    # Mapeamento simplificado (o completo está no Plano.md)
    funcoes_map = {
        ("frontend", "júnior"): "Desenvolvedor Frontend, Desenvolvedor UI Júnior, Desenvolvedor Web",
        ("backend", "júnior"): "Desenvolvedor Backend, Desenvolvedor API Júnior, Desenvolvedor de Software",
        ("ciência de dados", "júnior"): "Analista de Dados, Cientista de Dados Júnior, Analista BI",
        ("full stack", "júnior"): "Desenvolvedor Full Stack, Desenvolvedor Web Júnior",
        ("devops", "júnior"): "Engenheiro DevOps Júnior, Suporte Cloud, SysAdmin",
    }
    funcoes = funcoes_map.get((area, nivel), "A definir conforme área e nível")
    
    lines = [
        "# Perfil do Usuário",
        f"Área de interesse: {quiz_data.get('Área de interesse', '')}",
        f"Nível de experiência: {quiz_data.get('Nível de experiência', '')}",
        f"Habilidades técnicas: {quiz_data.get('Habilidades técnicas', '')}",
        f"Preferências de trabalho: {quiz_data.get('Preferências de trabalho', '')}",
        f"Localização: {quiz_data.get('Localização', '')}",
        f"Proficiência em inglês: {quiz_data.get('Proficiência em inglês', '')}",
        f"Tipo de empresa: {quiz_data.get('Tipo de empresa', '')}",
        f"Expectativa salarial: {quiz_data.get('Expectativa salarial', '')}",
        f"Disponibilidade para mudança: {quiz_data.get('Disponibilidade para mudança', '')}",
        f"Portfólio/certificações: {quiz_data.get('Portfólio/certificações', '')}",
        f"Funções alvo: {funcoes}",
        "Concluído: true",
    ]
    return "\n".join(lines)

# ─── Perguntas do Quiz ───
QUIZ_QUESTIONS = [
    "Qual área da tecnologia você deseja atuar (ex: desenvolvimento, dados, QA, DevOps, UX/UI)?",
    "Qual seu nível de experiência prévia na área tech (iniciante, intermediário, avançado)?",
    "Quais suas principais habilidades técnicas atuais?",
    "Tem preferência por modalidade de trabalho (presencial, remoto, híbrido)?",
    "Qual sua localização atual em Portugal (ou pretende se mudar para qual região)?",
    "Qual seu nível de proficiência em inglês (básico, intermediário, avançado, fluente)?",
    "Prefere trabalhar em startups, empresas de médio porte ou grandes corporações?",
    "Qual sua expectativa salarial aproximada (em euros)?",
    "Tem disponibilidade para mudar de cidade dentro de Portugal?",
    "Já possui portfólio, projetos ou certificações relevantes para a área tech?",
]

QUIZ_FIELDS = [
    "Área de interesse",
    "Nível de experiência",
    "Habilidades técnicas",
    "Preferências de trabalho",
    "Localização",
    "Proficiência em inglês",
    "Tipo de empresa",
    "Expectativa salarial",
    "Disponibilidade para mudança",
    "Portfólio/certificações",
]

# ─── Gilbert: falas teatrais ───
SAUDACAO = """Ah, mais um viajante em busca de ouro e glória no reino da tecnologia lusitana? Pois bem, sou Gilbert — Sátiro, Bardo, e agora Maestro da Guilda dos Renegados! Prepare-se, pois cada passo seu será um espetáculo, cada palavra uma nota, e cada busca uma oferenda à Rainha Corvo! *(Faz um floreio amplo com sua batuta ornamentada de penas negras, criando pequenas ilusões visuais e sons de harpa ao redor)*"""

QUIZ_AUSENTE = """Mas que tragédia teatral se desenrola diante de meus olhos! Um herói sem história, um bardo sem canções! Antes que possamos compor nossa sinfonia de sucesso profissional, permita-me conduzir você por uma jornada de autodescoberta! Responda minhas dez perguntas e transformaremos seu destino em uma obra-prima!"""

MENU = """Agora, caro viajante, o palco é seu! Que papel deseja interpretar em nosso grande espetáculo?

**a)** Buscar vagas de emprego em Portugal
**b)** Responder o quiz (ou continuar o quiz pendente)

Escolha com sabedoria!"""

DESPACHO_SCOUT = """Com um floreio de minha batuta ornamentada, invoco as forças do caos organizado! Surja, ó agente Scout, e traga até mim as oportunidades que aguardam nos reinos da tecnologia lusitana! Que sua busca seja fecunda e seus resultados dignos de uma oferenda à Rainha Corvo!"""

# ─── Despacho do Scout via subprocess (equivalente a delegate_task) ───
def dispatch_scout(profile: str, context: str) -> Dict[str, Any]:
    """Chama scout.py como sub-processo passando envelope JSON no stdin."""
    envelope = {
        "perfil_usuario": profile,
        "contexto": context,
    }
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scout.py")],
            input=json.dumps(envelope, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
        )
        if result.returncode != 0:
            return {
                "estado": "erro",
                "resumo": f"Scout falhou com código {result.returncode}",
                "dados": [],
                "erros": [result.stderr[:500]] if result.stderr else ["Erro desconhecido no Scout"],
            }
        # Parse JSON da stdout
        stdout = result.stdout.strip()
        # Extrai JSON se houver texto extra
        import re
        json_match = re.search(r'\{.*\}', stdout, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        return {
            "estado": "erro",
            "resumo": "Scout excedeu tempo limite (5 min)",
            "dados": [],
            "erros": ["Timeout"],
        }
    except json.JSONDecodeError as e:
        return {
            "estado": "erro",
            "resumo": "Falha ao parsear resposta do Scout",
            "dados": [],
            "erros": [f"JSON inválido: {e}. Saída: {result.stdout[:500]}"],
        }
    except Exception as e:
        return {
            "estado": "erro",
            "resumo": f"Erro ao invocar Scout: {e}",
            "dados": [],
            "erros": [str(e)],
        }

# ─── Fluxos principais ───
def run_quiz_interactive() -> None:
    """Conduz o quiz pergunta a pergunta."""
    quiz_content = load_quiz()
    quiz_data = parse_quiz(quiz_content)
    
    # Encontra próxima pergunta não respondida
    start_idx = 0
    for i, field in enumerate(QUIZ_FIELDS):
        if not quiz_data.get(field):
            start_idx = i
            break
    else:
        # Todas respondidas
        quiz_data["Concluído"] = "true"
        save_quiz("\n".join(f"{k}: {v}" for k, v in quiz_data.items()))
        profile = build_user_profile_from_quiz(quiz_data)
        save_user_profile(profile)
        print("\n✨ Quiz completo! Perfil gerado em data/user-profile.md\n")
        return
    
    print(SAUDACAO)
    print()
    print(QUIZ_AUSENTE)
    print()
    
    for i in range(start_idx, len(QUIZ_QUESTIONS)):
        field = QUIZ_FIELDS[i]
        question = QUIZ_QUESTIONS[i]
        current = quiz_data.get(field, "")
        prompt = f"\n{question}"
        if current:
            prompt += f" [{current}]"
        prompt += ": "
        
        answer = input(prompt).strip()
        if answer:
            quiz_data[field] = answer
        
        # Salva progresso a cada resposta
        quiz_lines = [f"{k}: {v}" for k, v in quiz_data.items()]
        quiz_lines.append("Concluído: false")
        save_quiz("\n".join(quiz_lines))
    
    # Finaliza
    quiz_data["Concluído"] = "true"
    save_quiz("\n".join(f"{k}: {v}" for k, v in quiz_data.items()))
    profile = build_user_profile_from_quiz(quiz_data)
    save_user_profile(profile)
    print("\n✨ Quiz completo! Perfil gerado em data/user-profile.md\n")

def show_menu() -> str:
    print(MENU)
    while True:
        choice = input("\nSua escolha (a/b): ").strip().lower()
        if choice in ("a", "b"):
            return choice
        print("Opção inválida. Digite 'a' ou 'b'.")

def run_search() -> None:
    """Dispara busca via Scout (sub-processo)."""
    profile = load_user_profile()
    if not profile or "Concluído: true" not in profile:
        print("⚠️ Perfil não encontrado ou incompleto. Execute o quiz primeiro (opção b).")
        return
    
    print(DESPACHO_SCOUT)
    print()
    print("🔍 Scout vasculhando a web via Firecrawl...\n")
    
    # Contexto para o Scout
    quiz_data = parse_quiz(load_quiz())
    profile_data = parse_quiz(load_user_profile())
    # Usa profile_data (user-profile.md) que tem os dados reais
    context = f"""Área: {profile_data.get('Área de interesse', quiz_data.get('Área de interesse', ''))}
Localização: {profile_data.get('Localização', quiz_data.get('Localização', ''))}
Nível: {profile_data.get('Nível de experiência', quiz_data.get('Nível de experiência', ''))}
Habilidades: {profile_data.get('Habilidades técnicas', quiz_data.get('Habilidades técnicas', ''))}"""
    
    result = dispatch_scout(profile, context)
    
    # Salva resultado
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%d de %B de %Y")
    profile_data = parse_quiz(load_user_profile())
    output_lines = [
        f"# Resultados da Busca de Vagas - Scout",
        f"**Data da busca:** {today}",
        f"**Perfil alvo:** {profile_data.get('Área de interesse', '')} | {profile_data.get('Nível de experiência', '')} | {profile_data.get('Localização', '')}",
        f"**Estado:** {result.get('estado', 'desconhecido')}",
        f"**Resumo:** {result.get('resumo', '')}",
        "",
    ]
    
    if result.get("dados"):
        output_lines.append("## Vagas Encontradas")
        for i, vaga in enumerate(result["dados"], 1):
            output_lines.append(f"\n### Vaga {i}: {vaga.get('titulo', 'Sem título')}")
            output_lines.append(f"**Empresa:** {vaga.get('empresa', 'Não informada')}")
            output_lines.append(f"**Localização:** {vaga.get('localizacao', 'Não informada')}")
            output_lines.append(f"**Link:** {vaga.get('link', 'Sem link')}")
            output_lines.append(f"**Habilidades correspondentes:** {', '.join(vaga.get('habilidades_correspondentes', []))}")
            output_lines.append(f"**Habilidades faltantes:** {', '.join(vaga.get('habilidades_faltantes', []))}")
            output_lines.append(f"**Correspondência:** {vaga.get('contagem_correspondencia', 'N/A')}")
            output_lines.append(f"**Score métricas:** {vaga.get('score_metrics', 'N/A')}")
            output_lines.append(f"**Filtro:** {vaga.get('filtro', 'N/A')}")
            output_lines.append(f"**Status link:** {vaga.get('status_link', 'N/A')}")
    
    if result.get("erros"):
        output_lines.append("\n## Erros")
        for err in result["erros"]:
            output_lines.append(f"- {err}")
    
    (DATA_DIR / "job-search-results.md").write_text("\n".join(output_lines), encoding="utf-8")
    
    # Apresenta ao usuário
    print(f"\n{result.get('resumo', 'Busca concluída.')}\n")
    if result.get("dados"):
        for i, vaga in enumerate(result["dados"][:5], 1):
            print(f"  {i}. {vaga.get('titulo')} — {vaga.get('empresa')} ({vaga.get('localizacao')})")
            print(f"     Score: {vaga.get('score_metrics')}/100 | Link: {vaga.get('link')}")
    if result.get("erros"):
        print("\n⚠️ Erros:")
        for err in result["erros"]:
            print(f"  - {err}")
    print(f"\n📄 Resultados completos salvos em data/job-search-results.md")

def main():
    if len(sys.argv) < 2:
        print("Uso: python gilbert.py [chat|search]")
        print("  chat   - Conversa interativa (quiz + menu)")
        print("  search - Dispara busca de vagas (Scout)")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "chat":
        quiz_content = load_quiz()
        if not quiz_is_complete(quiz_content):
            run_quiz_interactive()
        else:
            print(SAUDACAO)
            print()
            print("✨ Quiz já concluído! Perfil carregado.")
            print()
        
        while True:
            choice = show_menu()
            if choice == "a":
                run_search()
            elif choice == "b":
                run_quiz_interactive()
    
    elif cmd == "search":
        run_search()
    
    else:
        print(f"Comando desconhecido: {cmd}")

if __name__ == "__main__":
    main()