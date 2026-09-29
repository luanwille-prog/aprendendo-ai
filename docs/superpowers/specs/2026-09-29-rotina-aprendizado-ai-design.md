# Rotina diária de aprendizado AI Engineer · Design

- **Data:** 2026-09-29
- **Status:** aprovado em conversa, aguardando revisão da spec escrita
- **Guia visual:** "Guia · Quadro Anotado" (PDF, v1, set 2026), copiado para `docs/guia-quadro-anotado.pdf`

## 1. Objetivo

Transformar os talks publicados no canal do YouTube **AI Engineer** (`@aiDotEngineer`, channel ID `UCLKPca3kwwd-B59HNr-_lvA`) em material de estudo diário, em português, para um leitor que usa IA na prática mas ainda não tem base técnica profunda.

Todo dia às 07:00 (America/Sao_Paulo) uma rotina na nuvem detecta os vídeos novos, extrai legenda e prints, sintetiza cada vídeo em um bloco curto, explica conceitos difíceis com analogias e publica tudo numa página única que acumula os dias.

**Critérios de sucesso**

- Nenhum vídeo do canal fica sem bloco (pendentes são reprocessados até 3 vezes).
- Um dia típico (cerca de 5 vídeos de ~20 min) é entregue em 10 a 15 minutos.
- Cada bloco é lido em 3 a 5 minutos e explica todo jargão na primeira ocorrência.
- O visual segue o Quadro Anotado sem variação entre dias.
- Custo de tokens de um dia típico em torno de 80 mil tokens.

**Dados medidos do canal (2026-09-29):** média de ~5 vídeos por dia, duração média de 20 minutos, todos com legenda automática em inglês (`en` e `en-orig`). Os últimos 7 dias somam cerca de 35 vídeos. O RSS do canal retorna apenas os 15 vídeos mais recentes.

## 2. Decisões tomadas

| Tema | Decisão |
|---|---|
| Execução | Rotina agendada do Claude Code na nuvem (claude.ai/code/routines), consumindo a assinatura do usuário |
| Parte mecânica | Scripts Python determinísticos. Modelos só fazem o trabalho de julgamento e escrita |
| Transcrição | Legenda automática do YouTube primeiro; Apify como fallback. Sem Whisper |
| Entrega | Página única acumulando os dias, publicada no GitHub Pages |
| Repositório | Público no GitHub, nome `aprendendo-ai` |
| HTML | Gerado por script a partir de JSON. Nenhum modelo escreve HTML |
| Idioma | Português do Brasil. Termos técnicos mantidos em inglês com tradução na primeira ocorrência, ex.: "eval (avaliação)" |

## 3. Arquitetura

### 3.1 Estrutura do repositório

```
aprendendo-ai/
├── CLAUDE.md                     # visão geral do projeto para sessões interativas
├── ROTINA.md                     # instrução do orquestrador (a receita da rotina)
├── .claude/agents/
│   ├── analista-video.md         # model: sonnet
│   ├── explicador.md             # model: opus
│   └── curador-prints.md         # model: haiku
├── scripts/
│   ├── detectar.py               # lista vídeos novos (RSS ou backfill via yt-dlp)
│   ├── extrair.py                # legenda, capítulos, descrição, duração
│   ├── capturar_frames.py        # frames candidatos por momento
│   ├── validar.py                # valida os JSON dos agentes contra o schema
│   ├── consolidar.py             # junta análise, explicação e prints em data/videos/<id>.json
│   ├── montar_site.py            # JSON -> HTML no template Quadro Anotado
│   └── estado.py                 # leitura/escrita de processados e pendentes
├── templates/                    # template HTML/CSS do Quadro Anotado
├── schemas/                      # JSON Schema de cada saída de agente
├── data/
│   ├── processados.json          # vídeos já publicados
│   ├── pendentes.json            # vídeos com falha e número de tentativas
│   ├── glossario.json            # conceitos já explicados
│   ├── videos/<id>.json          # resultado final de cada vídeo
│   └── dias/<AAAA-MM-DD>.json    # abertura e ordem de leitura de cada dia
├── site/                         # saída publicada (index.html, dias/, img/)
├── tests/                        # testes dos scripts
└── docs/
```

### 3.2 Branches e publicação

- A rotina só tem push garantido em branches com prefixo `claude/`. Por isso **`claude/biblioteca` é a branch padrão e única do repositório**: contém código, dados e site. Não existe `main`.
- O GitHub Pages publica a pasta `site/` via GitHub Actions (workflow de deploy do Pages), já que o modo "deploy from branch" só aceita raiz ou `/docs`. Como `claude/biblioteca` é a branch padrão, o environment `github-pages` aceita o deploy sem configuração extra.

### 3.3 Ambiente na nuvem

- **Rede:** nível *Custom*, liberando além da lista padrão: `youtube.com`, `www.youtube.com`, `*.googlevideo.com`, `i.ytimg.com`, `api.apify.com`.
- **Setup script (cacheado):** `apt-get install -y ffmpeg` e `pip install yt-dlp jsonschema jinja2 pillow pytest`. Precisa terminar em menos de 5 minutos.
- **Segredo:** `APIFY_TOKEN` configurado como credencial do ambiente.
- **Modelo da sessão principal:** Opus.
- **Agendamento:** diário, `0 10 * * *` em UTC (07:00 em Brasília, sem horário de verão).
- **Prompt da rotina:** curto, apenas "Execute a rotina conforme o ROTINA.md". Toda a lógica vive no repositório. O modo (backfill de 7 dias ou diário) é decidido pela flag `backfill_concluido` em `data/config.json`: a primeira execução na nuvem faz o backfill e liga a flag.
- **Timeouts:** comandos longos (download em lote) configurados com `BASH_MAX_TIMEOUT_MS=600000`.

## 4. Fluxo de uma execução

1. **Preparar:** checkout de `claude/biblioteca`, leitura de `processados.json` e `pendentes.json`.
2. **Detectar** (`detectar.py`): vídeos do RSS publicados até 00:00 de hoje (Brasília) e que não estão em `processados.json`, mais os pendentes com menos de 3 tentativas. Modo `--backfill 7` lista os últimos 7 dias via `yt-dlp` com corte por data (`--break-match-filters`), porque o RSS só tem os 15 mais recentes. Shorts são marcados como ignorados.
3. **Extrair** (`extrair.py`, em paralelo por vídeo): legenda `en-orig` (ou `en`) em json3, convertida em texto com timestamps; capítulos; descrição; duração. Fallback: actor da Apify para transcrição. Falha dupla leva o vídeo para `pendentes.json`. Vídeos com menos de 3 minutos são ignorados; premieres agendadas e lives em andamento são adiados sem gastar tentativa.
4. **Triar** (orquestrador, Opus): lê só título, descrição e capítulos de todos os vídeos do dia. Estima a complexidade e escolhe o modelo do analista: Sonnet por padrão, Opus quando a estimativa é 5 (pesquisa, treino de modelos, matemática). Não lê transcrições nesta etapa.
5. **Analisar** (subagente `analista-video`, modelo definido na triagem, um por vídeo, em paralelo, ondas de até 8): lê a transcrição completa e devolve o JSON da seção 5.1.
6. **Explicar** (subagente `explicador`, Opus): só para vídeos com `complexidade >= 4` ou com conceito de nível avançado que ainda não esteja em `glossario.json`. Recebe apenas os conceitos e os trechos de transcrição onde aparecem.
7. **Capturar** (`capturar_frames.py`): para o momento de cada ideia, baixa ~3 segundos em 720p com `yt-dlp --download-sections` e extrai 3 frames com `ffmpeg`. Fallback: storyboard do YouTube (quadros de 320x180); em último caso, a thumbnail do vídeo, usada no máximo uma vez por vídeo.
8. **Curar** (subagente `curador-prints`, Haiku, um por vídeo): olha os frames de cada momento e escolhe o que mostra conteúdo (slide, código, diagrama, demo) em vez do rosto do palestrante. Pode descartar um momento se nenhum frame servir.
9. **Validar** (`validar.py`): todo JSON de agente é validado contra o schema. Inválido: uma nova tentativa do agente; falhou de novo, vídeo vai para pendentes.
10. **Editar** (orquestrador, Opus): lê os resultados do dia e escreve `data/dias/<data>.json` (abertura com o fio que liga os talks, ordem de leitura, conceitos novos do dia). Revisa consistência e tamanho dos blocos contra as regras de escrita da seção 7.
11. **Publicar** (`montar_site.py`): gera o HTML, atualiza `glossario.json`, faz commit e push em `claude/biblioteca`. **Só depois do push** os vídeos entram em `processados.json` (commit seguinte).
12. **Plano B sem subagentes:** se a rotina não conseguir disparar subagentes, o orquestrador executa as etapas 5, 6 e 8 em sequência com as mesmas instruções dos arquivos de agente. Mais lento, mesmo resultado.

## 5. Agentes

### 5.1 `analista-video` (Sonnet; Opus quando a triagem estimar complexidade 5)

**Entrada:** metadados do vídeo, capítulos, transcrição com timestamps, lista de conceitos já em `glossario.json` (só nomes).

**Saída (JSON):**

```json
{
  "id": "474j-n1Ltxc",
  "tese": "uma linha, no tom de anotação",
  "tldr": ["frase 1", "frase 2", "frase 3"],
  "tema": "agentes | evals | infraestrutura | produto | modelos | ...",
  "complexidade": 3,
  "ideias": [
    {
      "titulo": "curto",
      "texto": "2 a 4 frases",
      "momento": { "t": 312, "descricao": "o que aparece na tela", "legenda": "o que o print prova, em uma linha" }
    }
  ],
  "conceitos": [
    { "nome": "eval", "traducao": "avaliação", "nivel": "basico | intermediario | avancado", "trecho_t": [312, 480] }
  ],
  "leitura_critica": "onde o talk é pitch de produto, onde falta evidência, quais limites",
  "acoes": ["ação prática 1", "ação prática 2"],
  "numeros": [ { "valor": "3x", "contexto": "mais rápido na inferência", "t": 845 } ]
}
```

Regras: 3 a 5 ideias, cada uma com um momento de conteúdo visual provável (vira o print); `acoes` concretas para quem usa IA no trabalho; números só se ditos no vídeo, sempre com o minuto.

### 5.2 `explicador` (Opus)

**Entrada:** conceitos marcados, trechos de transcrição correspondentes, perfil do leitor.

**Saída (JSON):** para cada conceito, `analogia` (uma frase no formato da caixa tracejada), `explicacao` (3 a 5 passos curtos), `pre_requisitos` (conceitos que ajudam a entender), `desenho` opcional (descrição de um diagrama simples que o template pode renderizar como fluxo de nós).

Conceitos que já existem em `glossario.json` não são reexplicados: o bloco aponta para a entrada existente.

### 5.3 `curador-prints` (Haiku)

**Entrada:** caminhos dos frames candidatos por momento e a descrição esperada.

**Saída (JSON):** para cada momento, o frame escolhido ou `null`, e uma nota curta do que o frame mostra.

### 5.4 Orquestrador (sessão principal, Opus)

Responsável por triagem, disparo, retentativas, edição do dia e controle de qualidade. Nunca lê transcrições inteiras, exceto no plano B.

## 6. A página

### 6.1 Estrutura

- **Topo:** dia mais recente aberto, com a abertura do editor e a ordem de leitura.
- **Dias anteriores:** recolhidos, com título e contagem de vídeos. O conteúdo de cada dia fica em `site/dias/<data>.html` e é carregado sob demanda ao abrir.
- **Aba Glossário:** todos os conceitos explicados, com analogia e link para o vídeo de origem.
- **Filtro por tema** e **checkbox "estudei"** por bloco, salvo em `localStorage` com try/catch (a página funciona igual sem ele).
- **Rodapé:** data e hora da última execução e lista de pendentes.

### 6.2 Bloco de vídeo (ritmo do guia)

1. Cabeçalho de seção: número vazado laranja, título em Barlow Condensed 900 caixa alta, tese em Covered By Your Grace laranja.
2. Chips: tema, duração, nível (●○○ a ●●●), palestrante e empresa, link do vídeo.
3. TL;DR em 3 frases.
4. Grid de 2 colunas: ideias-chave à esquerda, prints em moldura polaroide à direita (inclinação alternada até 0,6°), legenda e link `youtu.be/<id>?t=<s>` com o minuto.
5. Caixas tracejadas: `analogia` (quando houver explicação) e `leitura crítica` (sempre).
6. Painel de ação: lista com marcador →.

### 6.3 Regras visuais aplicadas

Tokens de cor, tipografia, papel pontilhado, componentes e checklist conforme o guia Quadro Anotado (páginas 2 a 11): tema claro padrão e escuro via tokens; laranja só em anotação; numeração só em sequência verdadeira; funciona em 400px sem rolagem lateral; foco visível e `prefers-reduced-motion` respeitado; imagens com `loading="lazy"`.

## 7. Regras de escrita (entram nos arquivos de agente)

Do guia, página 9:

- Frases curtas e diretas, voz ativa.
- Uma analogia por ideia difícil, sempre dentro da caixa rotulada.
- Número real só com a fonte (minuto do vídeo).
- Uma leitura crítica por bloco.
- Fechar com ação.
- Evitar: o molde "não é X, é Y"; travessões para apartes; frases de efeito com dois-pontos; superlativos vazios; jargão sem explicação na primeira vez; emoji como marcador.

## 8. Estado e tratamento de erros

| Situação | Comportamento |
|---|---|
| Legenda indisponível ou bloqueada | Fallback Apify. Falha dupla: vídeo em `pendentes.json`, nova tentativa nas próximas execuções, máximo 3 |
| Frame indisponível | Storyboard, depois thumbnail. O bloco sempre sai |
| JSON inválido | Uma retentativa do agente. Falhou de novo: pendente |
| Execução interrompida | `processados.json` só é atualizado após push bem-sucedido; a próxima execução retoma |
| Dia sem vídeo novo | Sem commit, encerra após a detecção |
| 3 tentativas esgotadas | Vídeo sai de pendentes e aparece no rodapé como "não processado" com link direto |

## 9. Validação

1. **Teste local** no Mac com 2 vídeos reais: valida scripts, template e tom. O usuário aprova o visual de um bloco antes de subir para a nuvem.
2. **Testes automáticos** (pytest): detecção e filtro por data, `estado.py` (processados e pendentes), validação de schema, montagem do site com dados de exemplo.
3. **Primeira execução na nuvem** via "Run now" com `--backfill 7` (~35 vídeos, estimativa 30 a 40 minutos, ~500 mil tokens). Medir: subagentes em paralelo funcionaram, houve bloqueio do YouTube, tempo total, tokens consumidos. O usuário revisa a página.
4. **Ativação** do agendamento diário só após a aprovação da etapa 3.

## 10. Riscos conhecidos

| Risco | Mitigação |
|---|---|
| YouTube bloqueia IP de datacenter para legenda e download | Apify para legenda; storyboard e thumbnail para imagem; medido na etapa 3 da validação |
| Subagentes não suportados dentro da rotina (não documentado) | Plano B sequencial descrito na etapa 12 do fluxo |
| Push para `claude/biblioteca` recusado | Branch com prefixo `claude/` tem push garantido pela documentação das rotinas |
| Consumo do plano em dias de muitos vídeos (pós-conferência) | Ondas de 8 vídeos; explicador só acima do limiar de complexidade; glossário evita reexplicação |
| Crescimento da página ao longo do ano | Dias anteriores em arquivos separados carregados sob demanda |

## 11. Fora do escopo

Notificação por e-mail ou mensagem, busca textual na página, outros canais além do AI Engineer, vídeos em outros idiomas, transcrição por Whisper.
