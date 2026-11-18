# Job Search — Protocolo de Busca e Correspondência de Vagas

## Comandos Firecrawl
- Busca: `firecrawl search "<termos>" --limit <N> --json`
  - Exemplo: `firecrawl search "junior AI developer Portugal" --limit 5 --json`
- Detalhes da vaga: `firecrawl scrape <url> --format markdown`

## Fluxo de Busca (sempre FRESCO)
1. Ler `data/user-profile.md` para extrair área, localização, nível e habilidades.
2. Rodar `firecrawl search` com os termos otimizados **de uma só vez** (nunca carregar resultados de uma busca antiga).
3. Parse JSON para extrair: URL, título, empresa, localização, descrição.
4. Para as vagas mais promissoras, rodar `firecrawl scrape` para obter descrição + requisitos.
5. **Correspondência de habilidades e METRICA:** usar `data/skills-metric.md`
   (níveis, uso de IA, localização, salário, capacitação). Marcar os fatores.
6. **Filtragem:** reter `Score ≥ 60` como "compativel".
7. **Verificação de Links:** antes de salvar, confirma o link (HTTP 2xx). Se 403/429, aguardar 30–60s e repetir; se persistir, registrar no `erros` e pular.
8. Salvar em `data/job-search-results.md` sempre com `Data da busca: <data atual>`.

## Formato de Resposta
```json
{
  "estado": "sucesso" | "erro",
  "resumo": "Nº de vagas encontradas",
  "dados": [
    {
      "titulo": "...",
      "empresa": "...",
      "localizacao": "...",
      "link": "...",
      "habilidades_correspondentes": ["..."],
      "habilidades_faltantes": ["..."],
      "contagem_correspondencia": "X de Y",
      "score_metrics": 76,            // de 0..100 (skills-metric.md)
      "filtro": "entrada|júnior|IA|capacitacao",
      "status_link": "200 | 403 | 429 | expira"
    }
  ],
  "erros": ["..." (se houver)]
}
```
