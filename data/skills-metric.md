# Métrica de Habilidades — "Skills Metric"

## Objetivo
Avaliar e comparar vagas de tecnologia por **quão compatíveis elas são com
o perfil de quem está em transição de carreira**. O foco são três regras
douradas:

1. **Entrada/Júnior** — ou programa de graduação/estágio/training;
2. **Uso de Inteligência Artificial** — a IA aparece como ferramenta ou
   requisito da vaga (não como único foco);
3. **Possibilidade de capacitação** — a empresa dá formação, treino ou
   rota de transição de carreira.

## Perfil de Referência (o que o score deve prestar atenção)
- Área: AI, backend, análise de dados
- Nível: transição de carreira → candidatura de entrada/junior
- Habilidades: AI, Python, SQL, análise de dados, Office, Photoshop
- Modalidade: híbrido ou remoto
- Localização: Setúbal e região Sul
- Salário esperado: ~1500€
- Preferência: empresa que dá formação/rodas de transição de carreira

## Tabela de Fatores (pesos)
| # | Fator | Peso | 10 = perfeito | 5 = mediano | 3 = fraco | 0 = ausente |
|---|-------|------|---------------|-------------|-----------|-------------|
| 1 | Nível de experiência (entry/junior) | 20% | entry, junior, graduation | pleno | sênior | senior |
| 2 | Uso de Inteligência Artificial | 15% | AI = ferramenta/requisito | AI mencionada | pouco | nenhum |
| 3 | Correspondência técnica (Python, SQL, dados, IA) | 15% | Python+SQL+dados+IA | parcial | pouco | pouco |
| 4 | Localização compatível (Sul/Setúbal + híbrido/remoto) | 10% | 100% remoto ou Sul/Setúbal | Lisboa/Porto | Lisboa | obrigatórioLisboa |
| 5 | Salário compatível (~1500€) | 10% | ≤1500€ | 1500-2000€ | >2000€ | não especificado |
| 6 | Capacitação / transição de carreira | 15% | programa de graduação/estágio/formação | roteiro de formação | nenhum | nenhum |
| 7 | Consistência do link/fonte | 5% | 200 + fonte estável | 200/agregador | 403/429 | morto/expira |

## Fórmula
```
Score = Σ (fator_i × peso_i)          (cada fator em 0..10)
Resultado final = Score × 10           (0..100)
```

## Como usar (no agente Scout)
1. Para cada vaga, marcar os fatores acima.
2. Mantêm apenas `Score ≥ 60` como "compativel".
3. Classificar por Score e listar os top 5.
4. Separar os três filtros: **Entrada/Junior**, **Uso de IA**, **Capacitação**.

## Decodificação do resultado
- **≥ 75** → "Ótimo alinhamento" — candidatar-se com prioridade
- **60–74** → "Bom alinhamento" — candidatar-se com moderação
- **< 60** → "Atenção" — verificar se corresponde ao objetivo

## Nota importante sobre capacitação
Encontrar a vaga "ideal" é só o meio. Em Portugal, o **Fundo Europeu Social
Plus (FES)**, por via do **IEFP** (Instituto do Emprego e Formação
Profissional), financia cursos de capacitação e seletivos para quem está em
transição de carreira. O agente deve indicar apenas a vaga + a empresa, e
recomendar a consulta ao **IEFP** para verificar redes de formação
paga/apoio a transição de carreira.
