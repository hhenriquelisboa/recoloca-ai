# Recoloca-AI — Orquestrador de Vagas Tech em Portugal

> **Gilbert**, o Sátiro Bardo Maestro, conduz sua busca por oportunidades na tecnologia lusitana com teatralidade, caos organizado e uma batuta de penas negras da Raven Queen.

---

## 🎭 O que é

Sistema multi-agente para buscar vagas de emprego em **tecnologia em Portugal**, focado em **profissionais em transição de carreira**. Dois agentes:

| Agente | Papel | Tecnologia |
|--------|-------|------------|
| **Gilbert** (Maestro) | Interface com usuário, quiz de perfil, menu, orquestração | Python CLI (`gilbert.py`) |
| **Scout** (Rastreador) | Busca real via Firecrawl, scoring, filtragem | Python CLI (`scout.py`) + Firecrawl CLI |

**Armazenamento**: tudo em arquivos Markdown na pasta `data/` — sem banco de dados, sem cache, simplicidade radical.

---

## 🚀 Quickstart

```bash
# 1. Clone
git clone https://github.com/hhenriquelisboa/recoloca-ai.git
cd recoloca-ai

# 2. Dependências
# - Python 3.11+
# - Firecrawl CLI instalado globalmente (npm i -g firecrawl-cli)
#   Verifique: firecrawl --version

# 3. Busca direta (usa perfil já salvo em data/user-profile.md)
python gilbert.py search

# 4. Modo interativo (quiz + menu teatral)
python gilbert.py chat
```

---

## 📁 Estrutura

```
recoloca-ai/
├── gilbert.py                 # Orquestrador CLI (Maestro)
├── scout.py                   # Sub-agente de busca (Scout)
├── AGENTS.md                  # Inicialização: "Você É o Gilbert"
├── Plano.md                   # Spec completa do projeto
├── .gitignore
├── personas/
│   ├── gilbert.md             # Persona completa do Sátiro Bardo Maestro
│   └── scout.md               # Persona do rastreador implacável
├── skills/
│   ├── dispatch.md            # Protocolo envelope despacho/resposta
│   ├── firecrawl.md           # Comandos CLI + política de links
│   └── job-search.md          # Fluxo busca + correspondência + score
└── data/
    ├── personality-quiz.md    # Template quiz (10 perguntas)
    ├── user-profile.md        # Perfil consolidado (já preenchido)
    ├── skills-metric.md       # Tabela de pesos scoring 0-100
    ├── job-search-results.md  # Última busca bruta
    └── vagas-entrada-ia-capacitacao.md  # Curado score ≥ 60
```

---

## 🎯 Como funciona

### 1. Quiz de Perfil (10 perguntas)
```
Área de interesse → Nível → Habilidades → Modalidade → Localização → 
Inglês → Tipo empresa → Salário → Mudança → Portfolio
```
Salvo em `data/user-profile.md` com **mapeamento de funções alvo** (33 categorias: Frontend Júnior/Pleno/Sênior, Backend, Data, Mobile, DevOps, Full Stack, Governança, UX/UI, Liderança, RH, Marketing, Produto, Cibersegurança).

### 2. Busca Multi-Query (Scout)
Executa 5 queries Firecrawl otimizadas:
- `{área} Portugal`
- `remote AI engineer Portugal`
- `remote backend developer Portugal`
- `junior AI engineer Portugal`
- `junior data analyst Portugal`

### 3. Filtragem Inteligente
- **Domínios confiáveis**: LinkedIn, Glassdoor, Indeed, RemoteRocketship, Crossover, Wellfound, Teamlyzer, BuiltIn, Randstad, Sapo, ITJobs, Landing.Jobs, Volkswagen, Accenture, Nokia, IEFP
- **Dedupe** por URL
- **Scrape** detalhes de cada vaga

### 4. Skills Metric (Score 0–100)
| Fator | Peso | Critério 10/10 |
|-------|------|----------------|
| Nível entrada/júnior | 20% | junior, entry, graduation, trainee |
| Uso de IA | 15% | AI no título/requisitos |
| Match técnico (Python, SQL, dados, IA) | 15% | % skills do perfil na vaga |
| Localização (Sul/Setúbal + remoto/híbrido) | 10% | 100% remoto ou Setúbal |
| Salário ≤ 1500€ | 10% | faixa compatível |
| Capacitação/transição | 15% | graduate programme, formação, mentoria |
| Link válido (200) | 5% | HTTP 200 + fonte estável |

**Threshold**: ≥ 45 (demo) / ≥ 60 (produção) → "compatível"

### 5. Saída Teatral
Gilbert apresenta resultados com pompa:
```
  1. Junior AI & Data Engineer — Volkswagen Group Services
     Score: 76/100 | Lisboa | 1200–2460€ | Link verificado 200
  2. Technology Graduate Programme — Accenture Portugal
     Score: 66/100 | Lisboa | Programa graduação | Link 301
```

---

## 🛠 Requisitos

| Ferramenta | Versão | Install |
|------------|--------|---------|
| Python | 3.11+ | `python.org` ou `winget install Python.Python.3.11` |
| Firecrawl CLI | 1.18+ | `npm install -g firecrawl-cli` |
| Git | — | `winget install Git.Git` |

> **Nota**: O Firecrawl CLI precisa de conta gratuita em [firecrawl.dev](https://firecrawl.dev) para API key (`firecrawl login`).

---

## 🎪 Comandos

```bash
# Busca única (não-interativo)
python gilbert.py search

# Modo conversa completa: quiz → menu → busca → menu...
python gilbert.py chat

# Teste isolado do Scout
python scout.py --test
```

---

## 📊 Exemplo de resultado

```json
{
  "estado": "sucesso",
  "resumo": "Encontradas 3 vagas compatíveis (score ≥ 45) de 5 analisadas",
  "dados": [
    {
      "titulo": "Junior AI & Data Engineer",
      "empresa": "Volkswagen Group Services",
      "localizacao": "Lisboa (Portugal)",
      "link": "https://jobs.volkswagen-group.com/.../1416736933/",
      "habilidades_correspondentes": ["python", "sql", "ai", "dados"],
      "habilidades_faltantes": ["photoshop", "office"],
      "contagem_correspondencia": "4 de 6",
      "score_metrics": 76,
      "filtro": "entrada|IA|capacitacao",
      "status_link": "200"
    }
  ],
  "erros": []
}
```

---

## 🔮 Próximos passos (roadmap)

- [ ] **Curator** — Agente de busca de cursos/formações (IEFP, bootcamps, Alura)
- [ ] **Coach** — Simulador de entrevistas (6 despachos sequenciais)
- [ ] API FastAPI (`/chat`, `/search`, `/profile`) para bot Telegram/Discord
- [ ] Deploy Cloud Run / Railway / Fly.io
- [ ] Agendador diário (cron) com notificação de novas vagas
- [ ] Threshold de volta a 60 com queries de vaga individual (não agregador)

---

## 📜 Licença

MIT — Use, modifique, compartilhe. A Rainha Corvo aprova.

---

> *"Cada busca uma oferenda. Cada vaga uma nota. Cada carreira uma sinfonia."*  
> — **Gilbert**, Sátiro Bardo Maestro da Guilda dos Renegados