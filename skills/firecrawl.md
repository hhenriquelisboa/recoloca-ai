# Firecrawl — Comandos e Política de Busca Atual

## Ferramenta primária
O agente **Scout** (busca de vagas) extrai ofertas via **Firecrawl CLI** (`firecrawl`), instalado no host. O orquestrador **Gilbert** (máestro) despacha o Scout seguindo `skills/dispatch.md`.

## Comandos

### Busca de vagas
```bash
firecrawl search "<termos>" --limit <N> --json
```
Exemplo:
```bash
firecrawl search "vagas de analista de dados Portugal" --limit 6 --json
```

### Extração de uma vaga / página
```bash
firecrawl scrape <url> --format markdown --only-main-content
firecrawl scrape <url> --summary
firecrawl scrape <url> -f links
```

## Política de atualização (A EXPERIÊNCIA)

1. **NuncaReuse resultados de uma busca antiga.** A cada nova execução, o Scout deve rodar `firecrawl search` de novo. Os resultados são temporários.
2. **Prefira páginas estáveis.** Equivale sistemas estáticos (site da empresa num "careers", portais de empregos) em vez de links coletados via `jk=` / `rc/clk` do Indeed, que **expiram em poucas horas** e não podem ser confiáveis em longo prazo.
3. **Mapeie referências do Indeed.** Se cair um link `jk=...` ou `rc/clk`, tente converter para o anúncio ou para a página de empregos da empresa; se não for possível, **marque como "link de referência (expira)"**.
4. **Verifique cada link antes de salvar.** Registrar o código HTTP (200 = válido). Se o status for 403/429, aguardar 30–60s e repetir; se persistir, registrar no campo `erros` e pular a URL.
5. **Data da busca é obrigatória** no cabeçalho de qualquer arquivo de resultados.

## Saída

- Resultados brutos em `.firecrawl/<data-da-busca>.json` (raw Firecrawl).
- Resumo consolidado em `data/job-search-results.md`.
