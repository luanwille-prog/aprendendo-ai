# Rotina · Aprendendo AI

Você é o orquestrador. Siga os passos na ordem, sem pular. Regras gerais:

- Trabalhe na branch `claude/biblioteca`. Use `python3`.
- Variáveis de shell não persistem entre comandos: anote os valores (`HOJE`, `MODO`) e escreva-os literalmente nos comandos seguintes.
- Não leia `transcricao.txt` inteira, exceto no plano B.
- Subagentes vão em ondas de no máximo 8, todos da onda numa única mensagem (chamadas paralelas).
- Comandos longos (`detectar.py`, `extrair.py`, `capturar_frames.py`): use timeout de 600000 ms.

## 0. Preparar

```bash
git checkout claude/biblioteca && git pull --ff-only origin claude/biblioteca
pip install -q -r requirements.txt 2>/dev/null || pip install -q --break-system-packages -r requirements.txt
python3 scripts/estado.py hoje
python3 scripts/estado.py modo
```

Anote `HOJE` (primeira saída) e `MODO` (`backfill` ou `diario`).

O `requirements.txt` instala o yt-dlp e um `ffmpeg` estático (pacote `imageio-ffmpeg`), então não é preciso `apt-get`. Se `pip install` falhar por falta de rede, pare e relate: o ambiente precisa de acesso à internet (YouTube, i.ytimg.com, googlevideo.com e api.apify.com).

## 1. Detectar

- `MODO` = `backfill`: `python3 scripts/detectar.py --backfill 7`
- `MODO` = `diario`: `python3 scripts/detectar.py`

Se a fila tiver 0 vídeos: rode `git status --short`; se `data/` mudou (shorts ignorados), faça commit e push com a mensagem `estado: HOJE`. Encerre respondendo "nenhum vídeo novo".

## 2. Extrair

```bash
python3 scripts/extrair.py --fila trabalho/HOJE/fila.json
```

Leia `trabalho/HOJE/extracao.json`. A lista `ok` define os vídeos das próximas etapas. Se `ok` estiver vazia, vá direto ao passo 10 (só estado e rodapé).

## 3. Triar

Para cada id em `ok`, leia só `trabalho/HOJE/<id>/meta.json` (título, descrição, capítulos). Estime a complexidade de 1 a 5 e escolha o modelo do analista:

- `sonnet`: padrão.
- `opus`: estimativa 5 (pesquisa acadêmica, treino de modelos, matemática, arquitetura interna de modelos).

Grave `trabalho/HOJE/triagem.json` no formato `{"<id>": {"estimada": 3, "modelo": "sonnet", "motivo": "..."}}`.

## 4. Analisar (subagente `analista-video`)

Leia os nomes em `data/glossario.json` (campo `nome` de cada entrada). Para cada id, dispare o subagente `analista-video` com `model` igual ao da triagem e a mensagem:

> Pasta: trabalho/HOJE/<id>. Conceitos já no glossário: <nomes separados por vírgula, ou "nenhum">.

Depois de cada onda, confira com `python3 scripts/validar.py analise trabalho/HOJE/<id>/analise.json --meta trabalho/HOJE/<id>/meta.json`. Para cada vídeo sem `ok`: dispare o analista mais uma vez, citando os erros. Se falhar de novo:

```bash
python3 scripts/estado.py falha --id <id> --titulo "<titulo de meta.json>" --publicado-ts <publicado_ts de meta.json> --etapa analise --erro "<resumo do erro>"
```

e remova o id das etapas seguintes.

## 5. Explicar (subagente `explicador`)

Para cada vídeo com `analise.json` válido, monte a lista de conceitos a explicar: todos os `avancado`, e também os `intermediario` quando `complexidade >= 4`, excluindo os que já estão em `data/glossario.json` (compare pelo nome em minúsculas). Se a lista estiver vazia, pule o vídeo. Caso contrário, dispare `explicador` com:

> Pasta: trabalho/HOJE/<id>. Conceitos: <nomes separados por vírgula>.

Falha do explicador não bloqueia o vídeo: ele sai sem a caixa de analogia. Anote para o relatório.

## 6. Capturar frames

```bash
python3 scripts/capturar_frames.py --dia trabalho/HOJE
```

Anote a contagem por fonte (`video`, `storyboard`, `thumbnail`, `sem_imagem`) para o relatório.

## 7. Curar (subagente `curador-prints`)

Para cada vídeo, dispare `curador-prints` com `Pasta: trabalho/HOJE/<id>.` Falha do curador não bloqueia: o script usa o frame do meio.

## 8. Consolidar

```bash
python3 scripts/consolidar.py --dia trabalho/HOJE
```

Leia `trabalho/HOJE/publicados.json` (`{id: edicao}`).

## 9. Editar

Para cada edição que aparece em `publicados.json`:

1. Leia `data/videos/<id>.json` de **todos** os vídeos daquela edição (inclusive de execuções anteriores).
2. Escreva `data/dias/<edicao>.json` seguindo `schemas/dia.schema.json`:
   - `titulo`: o fio do dia em até 70 caracteres (ex.: "O dia das software factories").
   - `abertura`: 2 a 4 frases ligando os talks, dizendo o que o leitor vai aprender.
   - `ordem`: todos os ids da edição, do mais acessível ao mais denso, agrupando temas parecidos.
   - `conceitos_novos`: nomes dos conceitos explicados pela primeira vez nessa edição.
3. Valide: `python3 scripts/validar.py dia data/dias/<edicao>.json`.
4. Revise cada `data/videos/<id>.json` da edição contra as regras de escrita dos agentes (sem travessão de aparte, sem "não é X, é Y", sem superlativo vazio, jargão traduzido). Corrija o texto no próprio arquivo sem mudar a estrutura.

## 10. Publicar

```bash
python3 scripts/estado.py execucao --videos <quantidade em publicados.json>
python3 scripts/montar_site.py
git add data site && git commit -m "edição HOJE: <N> vídeo(s)" && git push origin claude/biblioteca
```

Se o push falhar, rode `git pull --rebase origin claude/biblioteca` e tente de novo uma vez. Se falhar de novo, pare e relate: **não** marque os vídeos como processados.

Só depois do push:

```bash
python3 scripts/estado.py processado --arquivo trabalho/HOJE/publicados.json
python3 scripts/estado.py backfill-concluido   # só se MODO = backfill
python3 scripts/montar_site.py
git add data site && git commit -m "estado: HOJE" && git push origin claude/biblioteca
```

## 11. Relatório final

Responda com:

- vídeos publicados por edição;
- vídeos em pendentes e o motivo;
- contagem de prints por fonte;
- se os subagentes rodaram em paralelo ou se foi usado o plano B;
- modelos usados por etapa.

## Plano B (sem subagentes)

Se a ferramenta de subagentes não existir nesta sessão ou recusar os tipos `analista-video`, `explicador` ou `curador-prints`, execute você mesmo os passos 4, 5 e 7, um vídeo por vez: leia o arquivo `.claude/agents/<agente>.md` correspondente e siga as instruções dele para cada pasta. Registre no relatório que o plano B foi usado.
