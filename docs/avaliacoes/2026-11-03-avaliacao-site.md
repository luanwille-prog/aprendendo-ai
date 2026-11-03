# Avaliação de melhorias do site: 3 nov 2026

> **Status:** tudo aplicado em 3 nov 2026 (P0 a P4). Conteúdo retroativo gerado e aplicado com `scripts/enriquecer.py`: campos didáticos dos 277 talks, essenciais das 25 edições, analogias de 72 termos e alt de 1.160 prints. A tabela de aliases está em `data/aliases.json`. A partir de agora, a rotina diária (`ROTINA.md` e os prompts em `.claude/agents/`) já gera esses campos.

Rodada feita por 5 agentes especialistas, todos só leitura: UX Researcher, UI Designer, Accessibility Auditor, Corporate Training Designer (didática) e Persona Walkthrough (duas personas). Os achados marcados com ✔ foram conferidos à mão depois.

## Diagnóstico em 3 linhas

1. **Cada bloco é bom.** A leitura crítica, o "número só com o minuto", as analogias, o "Antes de ler" e a fidelidade ao Quadro Anotado nas peças estão acima da média. A base de acessibilidade também é boa.
2. **O problema é escala.** O site foi pensado para cerca de 5 talks por dia e hoje tem 277 talks em 25 edições, uma delas com 57 ✔. A edição de 02/11 tem uns 87 mil px no celular e mais de 60 min de leitura, e não diz por onde começar.
3. **O site informa, mas forma pouco.** Não há perguntas, revisão, prática nem ligação entre talks. Os conceitos centrais (Eval, MCP, RAG, Trace) nunca recebem explicação.

---

## P0. Bugs (corrigir já, esforço P)

| # | Problema | Evidência | Correção |
|---|---|---|---|
| 1 | **387 links "Ajuda saber antes" quebrados** ✔ | `templates/_video.html.j2:105` gera `#g-{{p\|lower\|slug}}` a partir de texto livre. Exemplo: `#g-agente-de-ia` não existe. | Em `montar_site.py`, resolver cada pré-requisito contra `glossario.json` (via `chave()`) e criar link só quando o termo existe. Teste pytest que falha com âncora interna quebrada. |
| 2 | **Palestrante grudado no título** ✔ | `scripts/comum.py:91` `titulo_e_palestrante` só separa em " — ", mas o YouTube usa " - ". Resultado: h2 em caixa alta com "… - ADAM NAHARI, APOLLO" e o chip de palestrante nunca aparece. | Separar também na última ocorrência de " - " ou " \| " quando o lado direito parecer nome. Testar com títulos que têm hífen legítimo. |
| 3 | **"Continuar" perde o backlog** ✔ | `templates/app.js:17-27` pega o primeiro talk não estudado entre todos, do mais novo para o mais antigo. Quando sai edição nova, os talks pendentes da anterior somem do caminho. | Guardar `ultimo:<id>`/edição em andamento e retomar dela. Na home: "Você deixou 12 talks de 2 nov", com a opção de arquivar. |
| 4 | **Checkbox com rótulo diferente do visível** (WCAG 2.5.3, nível A) | `_video.html.j2:120`: o `aria-label` "Marcar X como estudado" difere do texto "Marquei como estudado". | Tirar o `aria-label` e pôr o título num `<span class="sr">`. |
| 5 | **Glossário com cartões esticados** | `estilo.css:206`: o grid sem `align-items` deixa caixas vazias enormes. | `.glossario{align-items:start}` |
| 6 | **Sem 404 próprio** | `edicoes/2026-11-03.html` devolve o 404 do GitHub, em inglês. | Gerar `404.html` com links para a última edição e para o glossário. |

## P1. Ganhos rápidos de UI, UX e acessibilidade (esforço P)

- **Tirar o excesso de laranja e de caixa alta** (guia, princípio 3):
  - `.tese` passa para `--ink-2`.
  - `h3{text-transform:none}`.
  - Links de lista em tinta com sublinhado laranja.
- **Orientação no celular:**
  - "↑ Índice" no rodapé de cada talk.
  - Anterior e próxima edição também no topo.
  - Índice recolhido em `<details>` abaixo de 1100px. Hoje o 1º talk começa a 2.208px.
- **Home:**
  - Subir "Ler a edição" e "Continuar" para logo depois da meta. Hoje ficam 3 telas abaixo no celular.
  - Recolher a lista de talks depois do 5º.
  - Não mostrar a barra quando houver "0 de N".
- **Tempo de leitura em vez de duração dos vídeos:** "≈ 5 min" por talk e "≈ 60 min" por edição. Datas no formato "Publicada em 3 nov · talks de 2 nov".
- **Tese em português embaixo do título em inglês** no índice e na home. Hoje a escolha é feita só pelo título em inglês.
- **Acessibilidade:**
  - Tirar `aria-label` das `section`. Hoje são cerca de 45 landmarks "Resumo" por edição e mais 25 "Letra X" no glossário.
  - `--orange-ink` no `aria-current` e no risco do índice. Hoje o contraste é 2,06:1.
  - Regra `forced-colors` no filtro.
  - Aviso "abre no YouTube, nova aba".
  - `scroll-margin-top` maior no glossário.
- **Filtro de temas no celular** rolando na horizontal. Hoje ocupa 4 linhas.

## P2. Estrutura da edição (esforço M, maior impacto em hábito)

1. **Edição em camadas: "Essenciais" e "Radar".**
   - O orquestrador escolhe 2 ou 3 `essenciais` (com `por_que`) em `dia.schema.json`.
   - Os essenciais aparecem completos. O resto entra recolhido, só com tese e as 3 frases.
   - Isso resolve ao mesmo tempo o volume (Marina, 15 min por dia), o "o que importa" (Rafael) e a página de 87 mil px.
   - Edições com mais de 8 talks também podem ser divididas por tema.
2. **Layout em 2 colunas no desktop** (texto + print), como o guia p.5 pede. Hoje `.ideia` empilha os dois, e a coluna única dobra a altura.
3. **Home com prints:** 2 ou 3 polaroides da edição em destaque e uma miniatura por cartão. Hoje a home é só texto e o destaque tem cerca de 45% vazio.
4. **Prints legíveis:** tocar para ampliar com link para o arquivo cheio, extrair a 1280px com `srcset` ou recortar o slide.
   - O `curador-prints` passa a gravar uma `descricao` para usar no `alt`. Hoje os 67 prints da edição têm `alt=""` e contêm dados (WCAG 1.1.1).

## P3. Didática: mudar onde o conteúdo nasce (schemas e prompts)

1. **Recuperação ativa e revisão espaçada:**
   - Campo `perguntas` em `analise.schema.json`, com 3 perguntas: lembrar, aplicar e criticar. Cada uma com resposta em `<details>`.
   - `montar_site.py` monta um "Revise" no fim da edição com perguntas de 1, 7 e 30 dias atrás. É determinístico e não custa chamada de modelo.
2. **Explicar o núcleo do campo:**
   - Hoje o explicador ignora termo `basico` e termo que já está no glossário. Por isso Eval (45 aparições), MCP (45), Human in the loop (44), Sandbox, Trace, RAG e Embedding nunca ganharam analogia.
   - A regra nova: termo com 3 ou mais aparições e sem analogia é explicado.
   - Rodar um backfill dos cerca de 30 termos mais frequentes.
3. **Canonizar o glossário:**
   - Juntar duplicatas (Skill/Skills, "LLM-as-a-judge"/"LLM judge"/"LLM as a judge", Harness/Agent harness) com uma tabela de aliases.
   - Passar `nome | tradução canônica` ao analista. Hoje há 23 traduções diferentes para Eval.
   - O explicador escolhe os pré-requisitos da lista do glossário.
4. **Perfil do leitor:** `analista-video.md` e `explicador.md` descrevem quem "usa IA no trabalho, sem base técnica profunda". Por isso as ações viram "peça ao financeiro…".
   - Reescrever o perfil para quem quer aprender a construir.
   - Novo campo `experimento`: 15 a 45 min, do que precisa, passos e como saber que deu certo.
5. **Objetivo por talk:** "Depois deste talk você consegue…", com verbo observável. A abertura da edição traz 2 ou 3 objetivos do dia.
6. **Escala de complexidade:** 177 dos 277 talks estão no nível 3. Pôr exemplos ancorados por nível no prompt.
7. **Conexões:**
   - "Talks relacionados" calculado no `montar_site.py` pelos conceitos em comum.
   - `dialoga_com` (complementa ou contradiz), anotado pelo orquestrador.
   - Páginas de trilha por tema com "comece por aqui". Hoje "agentes" tem 96 talks espalhados.

## P4. Médio prazo

- **Página "Talks"** com busca client-side (título, palestrante, tese) e filtro por talk, não por edição. Hoje o filtro "Agentes" bate em 23 de 24 edições.
- **Gatilho de retorno:**
  - RSS (barato e estático).
  - Contador de "talks nesta semana" ou de dias seguidos.
  - "Semana em 5 ideias" para quem lê uma vez por semana.
- **Glossário mais leve:**
  - Destacar os termos que têm analogia.
  - Recolher os que aparecem uma vez só (452).
  - "Aparece em" com no máximo 3 itens e "+N".
- **Progresso entre aparelhos:** exportar e importar por link ou código. Hoje fica só no localStorage.

## Fora do escopo, mas vale saber

- O `git log` reclama de `._pack-*.idx` em `.git/objects/pack`. São arquivos AppleDouble que o macOS cria no SSD externo, e podem ser removidos.
- O commit "edição 2026-11-03" publica a edição datada de 2026-11-02, porque a data é a dos vídeos. Isso explica a confusão de datas na home.

## Não verificado

- Leitor de tela real (VoiceOver/NVDA), forced colors real no Windows e zoom de 400%.
- O axe rodou só na home, no glossário e na edição de 02/11.
- O walkthrough de personas é uma simulação qualitativa: são hipóteses, não dados de uso.
