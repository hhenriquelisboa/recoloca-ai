# Dispatch — Despacho de Agentes

## Tabela de Roteamento

- **a)** Quiz — Gilbert lida com o quiz diretamente
- **b)** Buscar vagas — Scout (quando implementado)

## Formato de Envelope de Despacho

Gilbert constrói este prompt para `spawn_agent`:

```
## DESPACHO: [NOME_DO_AGENTE]
### referencia_persona
[Conteúdo completo de personas/<nome_do_agente_minusculo>.md]

### tarefa
[Uma frase descrevendo o que o agente deve fazer]

### perfil_usuario
[Conteúdo de data/user-profile.md]

### contexto
[Contexto específico: ex: qual vaga para entrevistar, quais habilidades buscar cursos]

### saida_esperada
[Exatamente em que formato o agente deve retornar]
```

## Formato de Envelope de Resposta

Agente despachado retorna isto:

```
## RESPOSTA: [NOME_DO_AGENTE]
### estado
[sucesso | erro]

### resumo
[Resumo legível de 2-3 frases para o usuário]

### dados
[Resultados como listas numeradas com pares chave-valor. Sem tabelas markdown.]

### erros
[Apenas se estado for erro: o que deu errado]
```

## Especificações de Handoff por Agente

### Scout (Busca de Vagas)
- **Tarefa**: Buscar vagas de emprego para [area] em [localizacao]
- **Contexto**: Área, Localização, Nível e Habilidades do user-profile.md
- **Saída Esperada**: Lista de até 5 vagas com título, empresa, localização, link, habilidades correspondentes/em falta

## Regras de Tratamento de Erros

- Se `spawn_agent` falhar, Gilbert deve dizer ao usuário com toda a sua eloquência o que deu errado e retornar ao menu
- Se um agente despachado retornar estado "erro", Gilbert deve relatar o erro ao usuário com floreios dramáticos
- Nunca esconder erros do usuário — transforme cada falha em um drama teatral digno da Rainha Corvo!
