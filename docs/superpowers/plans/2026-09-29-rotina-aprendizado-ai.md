# Rotina diária de aprendizado AI Engineer · Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Uma rotina diária na nuvem que transforma os talks novos do canal AI Engineer em blocos de estudo em português, publicados numa página única no estilo Quadro Anotado.

**Architecture:** Scripts Python determinísticos fazem a parte mecânica (detectar, extrair legenda, capturar frames, validar, consolidar, montar HTML). Um orquestrador (sessão Opus da rotina, seguindo `ROTINA.md`) faz a triagem e dispara subagentes em paralelo: `analista-video` (Sonnet ou Opus), `explicador` (Opus) e `curador-prints` (Haiku). O site estático sai de `site/` na branch `claude/biblioteca` e é publicado pelo GitHub Pages.

**Tech Stack:** Python 3.11+, yt-dlp, ffmpeg, jsonschema, Jinja2, Pillow, pytest, GitHub Pages (Actions), rotinas do Claude Code na nuvem, Apify (`starvibe/youtube-video-transcript`) como fallback de transcrição.

**Spec:** `docs/superpowers/specs/2026-09-29-rotina-aprendizado-ai-design.md`

## Global Constraints

- Python >= 3.11; comandos usam `python3`. Local: venv em `.venv`.
- Dependências Python: `yt-dlp`, `jsonschema>=4.21`, `jinja2>=3.1`, `pillow>=10`, `pytest>=8`. Sem `requests`: HTTP via `urllib`.
- yt-dlp é chamado como `python3 -m yt_dlp` (função `ytdlp_base()`), nunca pelo binário.
- Fuso: `America/Sao_Paulo`. Edição diária = ontem; backfill agrupa pela data de publicação em Brasília.
- IDs de vídeo têm 11 caracteres; fixtures de teste usam IDs de 11 caracteres.
- Branch única e padrão: `claude/biblioteca`. Não existe `main`.
- Nenhum modelo escreve HTML. HTML só sai de `scripts/montar_site.py` + `templates/`.
- Todo texto visível ao leitor em português do Brasil; termo técnico em inglês com tradução na primeira ocorrência.
- Regras de escrita (guia, pág. 9): frases curtas, voz ativa; uma analogia por ideia difícil; número só com o minuto; uma leitura crítica por bloco; fechar com ação; proibido o molde "não é X, é Y", travessão para aparte, frase de efeito com dois-pontos, superlativo vazio, jargão sem explicação, emoji como marcador.
- Visual: tokens e componentes do guia Quadro Anotado (`docs/guia-quadro-anotado.pdf`): papel `#F1F1EF` pontilhado, Barlow Condensed 900 nos títulos, Barlow no corpo, Covered By Your Grace laranja (`#ED9556` traço / `#B4581A` texto) nas anotações; tema escuro via tokens; funciona em 400px sem rolagem lateral.
- Um vídeo só entra em `data/processados.json` depois do push do site.
- Máximo de 3 tentativas por vídeo pendente.
- Vídeos com menos de 180 s e shorts são ignorados; premieres/lives são adiados sem gastar tentativa.
- Ondas de no máximo 8 subagentes em paralelo.
- `trabalho/` é área temporária, fora do git.

## Review Focus

1. **Vídeo publicado entre 21:00 e 23:59 de Brasília** (já é o dia seguinte em UTC): precisa entrar na edição de ontem, não sumir. Teste em Task 3 (`ontem000001` publicado 02:30 UTC).
2. **Shorts, premieres agendadas e lives no feed:** shorts viram "ignorado", premiere/live ficam para o dia seguinte sem gastar tentativa. Testes em Task 3 e Task 4.
3. **Títulos com `&`, `<` e aspas** (ex.: "Weights & Biases"): precisam aparecer escapados e legíveis no HTML. Teste em Task 8.
4. **Agente devolve minuto além da duração do vídeo:** `validar.py` rejeita, o link nunca aponta para o vazio. Teste em Task 5.
5. **Nenhuma imagem possível** (vídeo, storyboard e thumbnail falham): o bloco sai sem print, com o link do minuto em texto. Testes em Task 6 e Task 8.

---

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `scripts/comum.py` | Caminhos, fuso, formatação, JSON, `ytdlp_base()` |
| `scripts/estado.py` | `processados.json`, `pendentes.json`, `config.json`, `execucao.json` + CLI |
| `scripts/detectar.py` | RSS / listagem do canal → `trabalho/<hoje>/fila.json` |
| `scripts/extrair.py` | Metadados + transcrição por vídeo → `meta.json`, `transcricao.txt` |
| `scripts/capturar_frames.py` | Frames por momento → `frames/`, `frames/manifesto.json` |
| `scripts/validar.py` | JSON Schema + checagens semânticas + CLI |
| `scripts/consolidar.py` | Junta tudo em `data/videos/<id>.json`, imagens em `site/img/`, glossário |
| `scripts/montar_site.py` | `data/` → `site/index.html`, `site/dias/*.html` |
| `schemas/*.schema.json` | Contratos de saída dos agentes e do editor |
| `templates/*` | HTML (Jinja2), CSS e JS do Quadro Anotado |
| `.claude/agents/*.md` | Instruções dos subagentes com modelo fixo |
| `ROTINA.md` | Receita do orquestrador |
| `CLAUDE.md` | Visão geral para sessões interativas |
| `.github/workflows/*.yml` | Deploy do Pages e testes |

---

### Task 1: Base do projeto e utilidades comuns

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `.gitignore`, `scripts/comum.py`, `tests/test_comum.py`, `data/.gitkeep`, `site/.gitkeep`

**Interfaces:**
- Consumes: nada.
- Produces (`scripts/comum.py`): constantes `RAIZ, DATA, SITE, TRABALHO, SCHEMAS, TEMPLATES, TZ, CANAL_ID, CANAL_URL, TEMAS: dict[str,str], MESES, SEMANA`; funções `ler_json(caminho, padrao=None)`, `gravar_json(caminho, dados) -> None`, `data_local(ts: float) -> date`, `hoje_local(agora: datetime|None=None) -> date`, `inicio_do_dia_utc(d: date) -> datetime`, `fmt_tempo(segundos) -> str`, `fmt_data(iso: str) -> str`, `fmt_datahora(iso: str) -> str`, `titulo_e_palestrante(titulo: str) -> tuple[str, str|None]`, `chave(nome: str) -> str`, `slug(texto: str) -> str`, `ytdlp_base() -> list[str]`.

- [ ] **Step 1: Renomear a branch e criar o ambiente**

```bash
cd "/Volumes/PortableSSD/Aprendendo AI"
git branch -m main claude/biblioteca
python3 -m venv .venv
```

- [ ] **Step 2: Criar arquivos de configuração**

`requirements.txt`:
```
yt-dlp
jsonschema>=4.21
jinja2>=3.1
pillow>=10
pytest>=8
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
pythonpath = scripts
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
trabalho/
*.tmp
.DS_Store
```

```bash
mkdir -p data site tests/fixtures scripts
touch data/.gitkeep site/.gitkeep
.venv/bin/pip install -q -r requirements.txt
```

- [ ] **Step 3: Escrever o teste que falha**

`tests/test_comum.py`:
```python
from datetime import date, datetime, timezone

from comum import (chave, data_local, fmt_data, fmt_datahora, fmt_tempo, gravar_json,
                   inicio_do_dia_utc, ler_json, slug, titulo_e_palestrante)


def test_data_local_vira_o_dia_em_brasilia():
    # 2026-09-29 02:30 UTC = 2026-09-28 23:30 em Brasília
    ts = datetime(2026, 9, 29, 2, 30, tzinfo=timezone.utc).timestamp()
    assert data_local(ts) == date(2026, 9, 28)


def test_inicio_do_dia_utc():
    assert inicio_do_dia_utc(date(2026, 9, 29)) == datetime(2026, 9, 29, 3, 0, tzinfo=timezone.utc)


def test_fmt_tempo():
    assert fmt_tempo(312) == "05:12"
    assert fmt_tempo(3725) == "1:02:05"
    assert fmt_tempo(None) == "00:00"


def test_fmt_data_e_datahora():
    assert fmt_data("2026-09-28") == "segunda, 28 set 2026"
    assert fmt_datahora("2026-09-29T10:12:00+00:00") == "29 set 2026, 07:12"


def test_json_ida_e_volta(tmp_path):
    p = tmp_path / "a" / "b.json"
    gravar_json(p, {"título": "ação"})
    assert ler_json(p) == {"título": "ação"}
    assert ler_json(tmp_path / "nao.json", {}) == {}


def test_titulo_e_palestrante():
    assert titulo_e_palestrante("Get Out of the Model's Way — Kevin Hou, Google Antigravity") == (
        "Get Out of the Model's Way", "Kevin Hou, Google Antigravity")
    assert titulo_e_palestrante("Keynote sem autor") == ("Keynote sem autor", None)


def test_chave_e_slug():
    assert chave("  LLM-as-Judge   ação ") == "llm-as-judge ação"
    assert slug("llm-as-judge ação") == "llm-as-judge-acao"
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_comum.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'comum'`

- [ ] **Step 5: Implementar `scripts/comum.py`**

```python
"""Utilidades compartilhadas pelos scripts da rotina Aprendendo AI."""
from __future__ import annotations

import json
import re
import shutil
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
SITE = RAIZ / "site"
TRABALHO = RAIZ / "trabalho"
SCHEMAS = RAIZ / "schemas"
TEMPLATES = RAIZ / "templates"

TZ = ZoneInfo("America/Sao_Paulo")
CANAL_ID = "UCLKPca3kwwd-B59HNr-_lvA"
CANAL_URL = "https://www.youtube.com/@aiDotEngineer/videos"

TEMAS = {
    "agentes": "Agentes",
    "evals": "Evals",
    "infraestrutura": "Infraestrutura",
    "produto": "Produto",
    "modelos": "Modelos",
    "engenharia-de-software": "Engenharia de software",
    "dados-e-rag": "Dados e RAG",
    "pesquisa": "Pesquisa",
    "carreira-e-equipes": "Carreira e equipes",
}
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def ler_json(caminho, padrao=None):
    p = Path(caminho)
    if not p.exists():
        return padrao
    return json.loads(p.read_text(encoding="utf-8"))


def gravar_json(caminho, dados) -> None:
    p = Path(caminho)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def data_local(ts: float) -> date:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(TZ).date()


def hoje_local(agora: datetime | None = None) -> date:
    return (agora or datetime.now(tz=timezone.utc)).astimezone(TZ).date()


def inicio_do_dia_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=TZ).astimezone(timezone.utc)


def fmt_tempo(segundos) -> str:
    s = int(segundos or 0)
    h, resto = divmod(s, 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def fmt_data(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{SEMANA[d.weekday()]}, {d.day} {MESES[d.month - 1]} {d.year}"


def fmt_datahora(iso: str) -> str:
    d = datetime.fromisoformat(iso).astimezone(TZ)
    return f"{d.day} {MESES[d.month - 1]} {d.year}, {d:%H:%M}"


def titulo_e_palestrante(titulo: str) -> tuple[str, str | None]:
    base, sep, autor = titulo.rpartition(" — ")
    if not sep or not base.strip():
        return titulo.strip(), None
    return base.strip(), autor.strip()


def chave(nome: str) -> str:
    return " ".join(nome.lower().split())


def slug(texto: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


def ytdlp_base() -> list[str]:
    cmd = [sys.executable, "-m", "yt_dlp", "--no-warnings"]
    if shutil.which("deno") is None and shutil.which("node"):
        cmd += ["--js-runtimes", "node"]
    return cmd
```

- [ ] **Step 6: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_comum.py -v`
Expected: 7 passed

- [ ] **Step 7: Commit**

```bash
git add requirements.txt pytest.ini .gitignore scripts/comum.py tests/test_comum.py data/.gitkeep site/.gitkeep
git commit -m "feat: base do projeto e utilidades comuns"
```

---

### Task 2: Estado (processados, pendentes, config, execução)

**Files:**
- Create: `scripts/estado.py`, `tests/test_estado.py`

**Interfaces:**
- Consumes: `comum.DATA, ler_json, gravar_json, hoje_local`.
- Produces: `MAX_TENTATIVAS = 3`; classe `Estado(pasta: Path = DATA)` com atributos `processados: dict`, `pendentes: dict`, `config: dict`, `execucao: dict` e métodos `salvar()`, propriedade `inicio -> date|None`, `definir_inicio(d: date)`, propriedade `backfill_concluido -> bool`, `concluir_backfill()`, `elegivel(vid) -> bool`, `marcar_processado(vid, edicao: str, ignorado: str|None=None)`, `registrar_falha(vid, titulo, publicado_ts, etapa, erro)`, `pendentes_ativos() -> list[str]`, `abandonados() -> dict`, `registrar_execucao(videos: int)`. CLI: `estado.py [--data PASTA] {processado --arquivo JSON | falha --id --titulo --publicado-ts --etapa --erro | execucao --videos N | modo | hoje | backfill-concluido}`.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_estado.py`:
```python
from datetime import date

from comum import gravar_json
import estado as mod
from estado import MAX_TENTATIVAS, Estado


def test_estado_vazio(tmp_path):
    e = Estado(tmp_path)
    assert e.elegivel("abcdefghijk")
    assert e.inicio is None
    assert e.backfill_concluido is False


def test_marcar_processado_remove_de_pendentes(tmp_path):
    e = Estado(tmp_path)
    e.registrar_falha("abcdefghijk", "Título", 1790000000, "extracao", "sem legenda")
    e.marcar_processado("abcdefghijk", "2026-09-28")
    e.salvar()
    e2 = Estado(tmp_path)
    assert not e2.elegivel("abcdefghijk")
    assert "abcdefghijk" not in e2.pendentes
    assert e2.processados["abcdefghijk"]["edicao"] == "2026-09-28"


def test_tres_falhas_abandonam(tmp_path):
    e = Estado(tmp_path)
    for _ in range(MAX_TENTATIVAS):
        assert e.elegivel("abcdefghijk")
        e.registrar_falha("abcdefghijk", "T", 1790000000, "analise", "json inválido")
    assert not e.elegivel("abcdefghijk")
    assert list(e.abandonados()) == ["abcdefghijk"]
    assert e.pendentes_ativos() == []


def test_erro_longo_truncado(tmp_path):
    e = Estado(tmp_path)
    e.registrar_falha("abcdefghijk", "T", 0, "extracao", "e" * 1000)
    assert len(e.pendentes["abcdefghijk"]["ultimo_erro"]) == 300


def test_inicio_backfill_e_execucao(tmp_path):
    e = Estado(tmp_path)
    e.definir_inicio(date(2026, 9, 25))
    e.definir_inicio(date(2026, 9, 22))
    e.definir_inicio(date(2026, 9, 27))
    e.concluir_backfill()
    e.registrar_execucao(5)
    e.salvar()
    e2 = Estado(tmp_path)
    assert e2.inicio == date(2026, 9, 22)
    assert e2.backfill_concluido is True
    assert e2.execucao["videos"] == 5


def test_cli_processado_via_arquivo(tmp_path):
    arquivo = tmp_path / "publicados.json"
    gravar_json(arquivo, {"abcdefghijk": "2026-09-28", "bbbbbbbbbbb": "2026-09-27"})
    assert mod.main(["--data", str(tmp_path), "processado", "--arquivo", str(arquivo)]) == 0
    e = Estado(tmp_path)
    assert e.processados["bbbbbbbbbbb"]["edicao"] == "2026-09-27"


def test_cli_modo(tmp_path, capsys):
    mod.main(["--data", str(tmp_path), "modo"])
    assert capsys.readouterr().out.strip() == "backfill"
    mod.main(["--data", str(tmp_path), "backfill-concluido"])
    mod.main(["--data", str(tmp_path), "modo"])
    assert capsys.readouterr().out.strip() == "diario"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_estado.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'estado'`

- [ ] **Step 3: Implementar `scripts/estado.py`**

```python
"""Registro de vídeos processados e pendentes, configuração e última execução."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from pathlib import Path

from comum import DATA, gravar_json, hoje_local, ler_json

MAX_TENTATIVAS = 3


def _agora() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


class Estado:
    def __init__(self, pasta: Path = DATA):
        self.pasta = Path(pasta)
        self.processados: dict = ler_json(self.pasta / "processados.json", {})
        self.pendentes: dict = ler_json(self.pasta / "pendentes.json", {})
        self.config: dict = ler_json(self.pasta / "config.json", {})
        self.execucao: dict = ler_json(self.pasta / "execucao.json", {})

    def salvar(self) -> None:
        gravar_json(self.pasta / "processados.json", self.processados)
        gravar_json(self.pasta / "pendentes.json", self.pendentes)
        gravar_json(self.pasta / "config.json", self.config)
        gravar_json(self.pasta / "execucao.json", self.execucao)

    @property
    def inicio(self) -> date | None:
        valor = self.config.get("inicio")
        return date.fromisoformat(valor) if valor else None

    def definir_inicio(self, d: date) -> None:
        if self.inicio is None or d < self.inicio:
            self.config["inicio"] = d.isoformat()

    @property
    def backfill_concluido(self) -> bool:
        return bool(self.config.get("backfill_concluido"))

    def concluir_backfill(self) -> None:
        self.config["backfill_concluido"] = True

    def elegivel(self, vid: str) -> bool:
        return vid not in self.processados and vid not in self.abandonados()

    def marcar_processado(self, vid: str, edicao: str, ignorado: str | None = None) -> None:
        registro = {"edicao": edicao, "em": _agora()}
        if ignorado:
            registro["ignorado"] = ignorado
        self.processados[vid] = registro
        self.pendentes.pop(vid, None)

    def registrar_falha(self, vid: str, titulo: str, publicado_ts: float, etapa: str, erro: str) -> None:
        p = self.pendentes.setdefault(vid, {"titulo": titulo, "publicado_ts": publicado_ts, "tentativas": 0})
        p["tentativas"] += 1
        p.update(ultima_etapa=etapa, ultimo_erro=str(erro)[:300], em=_agora())

    def pendentes_ativos(self) -> list[str]:
        return [v for v, p in self.pendentes.items() if p["tentativas"] < MAX_TENTATIVAS]

    def abandonados(self) -> dict:
        return {v: p for v, p in self.pendentes.items() if p["tentativas"] >= MAX_TENTATIVAS}

    def registrar_execucao(self, videos: int) -> None:
        self.execucao = {"em": _agora(), "videos": videos}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=DATA)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("processado", help="marca como publicados os vídeos de publicados.json")
    p.add_argument("--arquivo", type=Path, required=True)
    f = sub.add_parser("falha", help="registra uma tentativa que falhou")
    f.add_argument("--id", required=True)
    f.add_argument("--titulo", required=True)
    f.add_argument("--publicado-ts", type=float, required=True)
    f.add_argument("--etapa", required=True)
    f.add_argument("--erro", required=True)
    x = sub.add_parser("execucao", help="registra a execução para o rodapé")
    x.add_argument("--videos", type=int, required=True)
    sub.add_parser("modo", help="imprime backfill ou diario")
    sub.add_parser("hoje", help="imprime a data de hoje em Brasília")
    sub.add_parser("backfill-concluido", help="liga a flag de backfill concluído")
    a = ap.parse_args(argv)

    if a.cmd == "hoje":
        print(hoje_local().isoformat())
        return 0
    e = Estado(a.data)
    if a.cmd == "modo":
        print("diario" if e.backfill_concluido else "backfill")
        return 0
    if a.cmd == "processado":
        for vid, edicao in ler_json(a.arquivo, {}).items():
            e.marcar_processado(vid, edicao)
    elif a.cmd == "falha":
        e.registrar_falha(a.id, a.titulo, a.publicado_ts, a.etapa, a.erro)
    elif a.cmd == "execucao":
        e.registrar_execucao(a.videos)
    elif a.cmd == "backfill-concluido":
        e.concluir_backfill()
    e.salvar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_estado.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/estado.py tests/test_estado.py
git commit -m "feat: registro de processados, pendentes e execução"
```

---

### Task 3: Detecção de vídeos novos

**Files:**
- Create: `scripts/detectar.py`, `tests/test_detectar.py`, `tests/fixtures/rss.xml`

**Interfaces:**
- Consumes: `comum.*`, `estado.Estado`.
- Produces: `parse_rss(xml: str) -> list[dict]` (itens `{"id","titulo","publicado_ts","short"}`), `parse_listagem(saida: str) -> list[dict]` (mesmo formato), `baixar_rss() -> str`, `listar_canal(desde_ts: float, maximo=150) -> list[dict]`, `selecionar(candidatos, estado, hoje: date, backfill: bool) -> tuple[list[dict], list[dict]]` (itens da fila `{"id","titulo","publicado_ts","edicao"}`), `main(argv)`. Arquivo `trabalho/<hoje>/fila.json` = `{"hoje": "AAAA-MM-DD", "modo": "diario"|"backfill", "videos": [...]}`.

- [ ] **Step 1: Criar a fixture do RSS**

`tests/fixtures/rss.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
 <title>AI Engineer</title>
 <entry>
  <id>yt:video:hoje0000001</id>
  <yt:videoId>hoje0000001</yt:videoId>
  <title>Publicado hoje de madrugada — Bia, Acme</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=hoje0000001"/>
  <published>2026-09-29T04:00:00+00:00</published>
 </entry>
 <entry>
  <id>yt:video:ontem000001</id>
  <yt:videoId>ontem000001</yt:videoId>
  <title>Evals &amp; Agents — Ana, Weights &amp; Biases</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=ontem000001"/>
  <published>2026-09-29T02:30:00+00:00</published>
 </entry>
 <entry>
  <id>yt:video:short000001</id>
  <yt:videoId>short000001</yt:videoId>
  <title>Um short</title>
  <link rel="alternate" href="https://www.youtube.com/shorts/short000001"/>
  <published>2026-09-28T15:00:00+00:00</published>
 </entry>
 <entry>
  <id>yt:video:antigo00001</id>
  <yt:videoId>antigo00001</yt:videoId>
  <title>Talk antigo — Caio, Beta</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=antigo00001"/>
  <published>2026-09-10T15:00:00+00:00</published>
 </entry>
</feed>
```

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_detectar.py`:
```python
from datetime import date, datetime, timezone
from pathlib import Path

import detectar
from comum import ler_json
from estado import MAX_TENTATIVAS, Estado

FIXTURE = Path(__file__).parent / "fixtures" / "rss.xml"
HOJE = date(2026, 9, 29)


def candidatos():
    return detectar.parse_rss(FIXTURE.read_text(encoding="utf-8"))


def test_parse_rss_decodifica_e_marca_shorts():
    vs = candidatos()
    assert [v["id"] for v in vs] == ["hoje0000001", "ontem000001", "short000001", "antigo00001"]
    assert vs[1]["titulo"] == "Evals & Agents — Ana, Weights & Biases"
    assert vs[2]["short"] is True
    assert vs[1]["short"] is False
    assert vs[1]["publicado_ts"] == datetime(2026, 9, 29, 2, 30, tzinfo=timezone.utc).timestamp()


def test_selecionar_diario_pega_ontem_mesmo_depois_da_meia_noite_utc(tmp_path):
    e = Estado(tmp_path)
    e.definir_inicio(date(2026, 9, 22))
    fila, ignorados = detectar.selecionar(candidatos(), e, HOJE, backfill=False)
    assert [v["id"] for v in fila] == ["ontem000001"]
    assert fila[0]["edicao"] == "2026-09-28"
    assert [v["id"] for v in ignorados] == ["short000001"]


def test_selecionar_pula_processados_e_abandonados(tmp_path):
    e = Estado(tmp_path)
    e.marcar_processado("ontem000001", "2026-09-28")
    fila, _ = detectar.selecionar(candidatos(), e, HOJE, backfill=False)
    assert "ontem000001" not in [v["id"] for v in fila]
    e2 = Estado(tmp_path / "b")
    for _ in range(MAX_TENTATIVAS):
        e2.registrar_falha("ontem000001", "T", 0, "extracao", "x")
    fila2, _ = detectar.selecionar(candidatos(), e2, HOJE, backfill=False)
    assert "ontem000001" not in [v["id"] for v in fila2]


def test_selecionar_inclui_pendente_fora_do_rss(tmp_path):
    e = Estado(tmp_path)
    ts = datetime(2026, 9, 26, 15, 0, tzinfo=timezone.utc).timestamp()
    e.registrar_falha("pendente001", "Pendente — X, Y", ts, "extracao", "bloqueio")
    fila, _ = detectar.selecionar(candidatos(), e, HOJE, backfill=False)
    pend = [v for v in fila if v["id"] == "pendente001"][0]
    assert pend["edicao"] == "2026-09-28"
    assert pend["titulo"] == "Pendente — X, Y"


def test_selecionar_backfill_agrupa_pela_data_de_publicacao(tmp_path):
    e = Estado(tmp_path)
    e.definir_inicio(date(2026, 9, 22))
    fila, _ = detectar.selecionar(candidatos(), e, HOJE, backfill=True)
    assert [(v["id"], v["edicao"]) for v in fila] == [("ontem000001", "2026-09-28")]


def test_parse_listagem():
    saida = ("aaaaaaaaaaa\t1790533807\thttps://www.youtube.com/watch?v=aaaaaaaaaaa\tTítulo A — P, E\n"
             "bbbbbbbbbbb\tNA\thttps://www.youtube.com/shorts/bbbbbbbbbbb\tShort\n"
             "linha quebrada\n")
    vs = detectar.parse_listagem(saida)
    assert vs == [{"id": "aaaaaaaaaaa", "titulo": "Título A — P, E", "publicado_ts": 1790533807.0, "short": False}]


def test_main_diario_grava_fila_e_ignora_short(tmp_path, monkeypatch):
    monkeypatch.setattr(detectar, "baixar_rss", lambda: FIXTURE.read_text(encoding="utf-8"))
    rc = detectar.main(["--hoje", "2026-09-29", "--data", str(tmp_path / "data"),
                        "--trabalho", str(tmp_path / "trab")])
    assert rc == 0
    fila = ler_json(tmp_path / "trab" / "2026-09-29" / "fila.json")
    assert fila["modo"] == "diario"
    assert [v["id"] for v in fila["videos"]] == ["ontem000001"]
    e = Estado(tmp_path / "data")
    assert e.processados["short000001"]["ignorado"] == "short"
    assert e.inicio == date(2026, 9, 28)
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_detectar.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'detectar'`

- [ ] **Step 4: Implementar `scripts/detectar.py`**

```python
"""Detecta vídeos novos do canal AI Engineer e grava trabalho/<hoje>/fila.json."""
from __future__ import annotations

import argparse
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path

from comum import (CANAL_ID, CANAL_URL, DATA, TRABALHO, data_local, gravar_json, hoje_local,
                   inicio_do_dia_utc, ytdlp_base)
from estado import Estado

RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CANAL_ID}"
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def baixar_rss() -> str:
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0 aprendendo-ai"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def parse_rss(xml: str) -> list[dict]:
    raiz = ET.fromstring(xml)
    videos = []
    for entrada in raiz.findall("atom:entry", NS):
        link = entrada.find("atom:link", NS)
        videos.append({
            "id": entrada.findtext("yt:videoId", namespaces=NS),
            "titulo": entrada.findtext("atom:title", namespaces=NS),
            "publicado_ts": datetime.fromisoformat(entrada.findtext("atom:published", namespaces=NS)).timestamp(),
            "short": link is not None and "/shorts/" in link.get("href", ""),
        })
    return videos


def parse_listagem(saida: str) -> list[dict]:
    videos = []
    for linha in saida.splitlines():
        partes = linha.split("\t", 3)
        if len(partes) != 4 or not partes[1].isdigit():
            continue
        vid, ts, url, titulo = partes
        videos.append({"id": vid, "titulo": titulo, "publicado_ts": float(ts), "short": "/shorts/" in url})
    return videos


def listar_canal(desde_ts: float, maximo: int = 150) -> list[dict]:
    cmd = [*ytdlp_base(), "--skip-download", "--playlist-end", str(maximo),
           "--break-match-filters", f"timestamp>={int(desde_ts)}",
           "--print", "%(id)s\t%(timestamp)s\t%(webpage_url)s\t%(title)s", CANAL_URL]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    # 101 = yt-dlp parou ao encontrar o primeiro vídeo mais antigo que o corte (esperado)
    if r.returncode not in (0, 101):
        raise RuntimeError(f"yt-dlp falhou ({r.returncode}): {r.stderr.strip()[-300:]}")
    return parse_listagem(r.stdout)


def selecionar(candidatos: list[dict], estado: Estado, hoje: date, backfill: bool) -> tuple[list[dict], list[dict]]:
    limite = inicio_do_dia_utc(hoje).timestamp()
    ontem = (hoje - timedelta(days=1)).isoformat()

    def edicao_de(ts: float) -> str:
        return data_local(ts).isoformat() if backfill else ontem

    fila, ignorados, vistos = [], [], set()
    for v in candidatos:
        vistos.add(v["id"])
        if v["publicado_ts"] >= limite or not estado.elegivel(v["id"]):
            continue
        if estado.inicio and data_local(v["publicado_ts"]) < estado.inicio:
            continue
        item = {"id": v["id"], "titulo": v["titulo"], "publicado_ts": v["publicado_ts"],
                "edicao": edicao_de(v["publicado_ts"])}
        (ignorados if v.get("short") else fila).append(item)
    for vid in estado.pendentes_ativos():
        if vid in vistos:
            continue
        p = estado.pendentes[vid]
        fila.append({"id": vid, "titulo": p["titulo"], "publicado_ts": p["publicado_ts"],
                     "edicao": edicao_de(p["publicado_ts"])})
    return fila, ignorados


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hoje", type=date.fromisoformat, default=None)
    ap.add_argument("--backfill", type=int, default=0, help="quantos dias para trás (primeira execução)")
    ap.add_argument("--limite", type=int, default=0, help="fica só com os N mais recentes (teste)")
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--trabalho", type=Path, default=TRABALHO)
    a = ap.parse_args(argv)

    hoje = a.hoje or hoje_local()
    estado = Estado(a.data)
    if a.backfill:
        inicio = hoje - timedelta(days=a.backfill)
        estado.definir_inicio(inicio)
        candidatos = listar_canal(inicio_do_dia_utc(inicio).timestamp())
    else:
        if estado.inicio is None:
            estado.definir_inicio(hoje - timedelta(days=1))
        candidatos = parse_rss(baixar_rss())

    fila, ignorados = selecionar(candidatos, estado, hoje, backfill=bool(a.backfill))
    fila.sort(key=lambda v: v["publicado_ts"], reverse=True)
    if a.limite:
        fila = fila[: a.limite]
    for v in ignorados:
        estado.marcar_processado(v["id"], v["edicao"], ignorado="short")
    estado.salvar()

    saida = a.trabalho / hoje.isoformat() / "fila.json"
    gravar_json(saida, {"hoje": hoje.isoformat(), "modo": "backfill" if a.backfill else "diario", "videos": fila})
    print(f"{len(fila)} vídeo(s) na fila, {len(ignorados)} short(s) ignorado(s) -> {saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_detectar.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/detectar.py tests/test_detectar.py tests/fixtures/rss.xml
git commit -m "feat: detecção de vídeos novos por RSS e backfill"
```

---

### Task 4: Extração de metadados e transcrição

**Files:**
- Create: `scripts/extrair.py`, `tests/test_extrair.py`

**Interfaces:**
- Consumes: `comum.*`, `estado.Estado`, `fila.json` da Task 3.
- Produces: `DURACAO_MINIMA = 180`; `obter_info(vid) -> dict`, `meta_de_info(info) -> dict`, `meta_de_apify(item) -> dict`, `escolher_legenda(info) -> str|None`, `baixar_json3(url) -> dict`, `segmentos_json3(dados) -> list[tuple[float,str]]`, `segmentos_apify(item) -> list[tuple[float,str]]`, `formatar_transcricao(segs, janela=30) -> str`, `transcricao_apify(vid, token) -> dict`, `extrair_video(vid, pasta: Path, token: str|None) -> dict` (`{"id","status": "ok"|"falha"|"ignorado"|"adiado", "etapa"?, "erro"?, "motivo"?}`), `main(argv)`.
- Arquivos: `trabalho/<hoje>/<id>/meta.json` com as chaves `id, titulo, titulo_curto, palestrante, descricao, duracao, publicado_ts, live_status, capitulos[{t,titulo}], thumbnail, storyboard{largura,altura,linhas,colunas,fps,fragmentos[{url,duracao}]}|null`; `trabalho/<hoje>/<id>/transcricao.txt` com linhas `[t=SEGUNDOS] texto`; `trabalho/<hoje>/extracao.json` = `{"ok": [ids], "resultados": [...]}`.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_extrair.py`:
```python
import extrair
from comum import ler_json, gravar_json
from estado import Estado

VID = "abcdefghijk"
INFO = {
    "id": VID,
    "title": "Scale the Judgment, Not the Model — Andrew Orobator, Reddit",
    "description": "Descrição do talk",
    "duration": 900,
    "timestamp": 1790524817,
    "live_status": "not_live",
    "chapters": [{"start_time": 0.0, "title": "Intro", "end_time": 25.0}],
    "formats": [
        {"format_id": "sb0", "width": 320, "height": 180, "rows": 3, "columns": 3, "fps": 0.2,
         "fragments": [{"url": "https://i.ytimg.com/sb/x/M0.jpg", "duration": 45.0}]},
        {"format_id": "137"},
    ],
    "automatic_captions": {
        "en-orig": [{"ext": "vtt", "url": "u-vtt"}, {"ext": "json3", "url": "u-orig"}],
        "en": [{"ext": "json3", "url": "u-en"}],
    },
    "subtitles": {},
}
JSON3 = {"events": [
    {"tStartMs": 0, "dDurationMs": 900000, "id": 1},
    {"tStartMs": 1000, "segs": [{"utf8": "Hello"}, {"utf8": " everyone"}]},
    {"tStartMs": 3000, "aAppend": 1, "segs": [{"utf8": "\n"}]},
    {"tStartMs": 40000, "segs": [{"utf8": "Evals matter."}]},
]}
APIFY = {"status": "success", "video_id": VID, "title": INFO["title"], "description": "d",
         "duration_seconds": 900, "published_at": "2026-09-27T16:00:17Z",
         "transcript": [{"start": 1.0, "end": 3.0, "duration": 2.0, "text": "Hello everyone"},
                        {"start": 40.0, "end": 42.0, "duration": 2.0, "text": " "}]}


def test_meta_de_info():
    m = extrair.meta_de_info(INFO)
    assert m["titulo_curto"] == "Scale the Judgment, Not the Model"
    assert m["palestrante"] == "Andrew Orobator, Reddit"
    assert m["capitulos"] == [{"t": 0, "titulo": "Intro"}]
    assert m["storyboard"]["colunas"] == 3
    assert m["storyboard"]["fragmentos"][0]["duracao"] == 45.0
    assert m["duracao"] == 900


def test_meta_de_apify():
    m = extrair.meta_de_apify(APIFY)
    assert m["id"] == VID and m["storyboard"] is None and m["capitulos"] == []
    assert m["publicado_ts"] == 1790524817.0


def test_escolher_legenda_prefere_manual_depois_en_orig():
    assert extrair.escolher_legenda(INFO) == "u-orig"
    com_manual = {**INFO, "subtitles": {"en": [{"ext": "json3", "url": "u-manual"}]}}
    assert extrair.escolher_legenda(com_manual) == "u-manual"
    so_en = {**INFO, "automatic_captions": {"en": [{"ext": "json3", "url": "u-en"}]}}
    assert extrair.escolher_legenda(so_en) == "u-en"
    assert extrair.escolher_legenda({**INFO, "automatic_captions": {}}) is None


def test_segmentos_e_formatacao():
    segs = extrair.segmentos_json3(JSON3)
    assert segs == [(1.0, "Hello everyone"), (40.0, "Evals matter.")]
    assert extrair.segmentos_apify(APIFY) == [(1.0, "Hello everyone")]
    texto = extrair.formatar_transcricao([(0, "a"), (10, "b"), (31, "c"), (65, "d")])
    assert texto == "[t=0] a b\n[t=31] c\n[t=65] d\n"


def _falha(*_a, **_k):
    raise RuntimeError("bloqueado")


def test_extrair_ok_via_json3(tmp_path, monkeypatch):
    monkeypatch.setattr(extrair, "obter_info", lambda vid: INFO)
    monkeypatch.setattr(extrair, "baixar_json3", lambda url: JSON3)
    r = extrair.extrair_video(VID, tmp_path / VID, token=None)
    assert r == {"id": VID, "status": "ok"}
    assert ler_json(tmp_path / VID / "meta.json")["titulo_curto"] == "Scale the Judgment, Not the Model"
    assert (tmp_path / VID / "transcricao.txt").read_text().startswith("[t=1] Hello everyone")


def test_extrair_cai_para_apify_quando_json3_falha(tmp_path, monkeypatch):
    monkeypatch.setattr(extrair, "obter_info", lambda vid: INFO)
    monkeypatch.setattr(extrair, "baixar_json3", _falha)
    monkeypatch.setattr(extrair, "transcricao_apify", lambda vid, token: APIFY)
    assert extrair.extrair_video(VID, tmp_path / VID, token="t")["status"] == "ok"


def test_extrair_sem_ytdlp_usa_meta_da_apify(tmp_path, monkeypatch):
    monkeypatch.setattr(extrair, "obter_info", _falha)
    monkeypatch.setattr(extrair, "transcricao_apify", lambda vid, token: APIFY)
    assert extrair.extrair_video(VID, tmp_path / VID, token="t")["status"] == "ok"
    assert ler_json(tmp_path / VID / "meta.json")["storyboard"] is None


def test_extrair_falha_quando_tudo_falha(tmp_path, monkeypatch):
    monkeypatch.setattr(extrair, "obter_info", lambda vid: INFO)
    monkeypatch.setattr(extrair, "baixar_json3", _falha)
    monkeypatch.setattr(extrair, "transcricao_apify", _falha)
    r = extrair.extrair_video(VID, tmp_path / VID, token="t")
    assert r["status"] == "falha" and "json3" in r["erro"] and "apify" in r["erro"]


def test_premiere_adiada_e_curto_ignorado(tmp_path, monkeypatch):
    monkeypatch.setattr(extrair, "obter_info", lambda vid: {**INFO, "live_status": "is_upcoming"})
    assert extrair.extrair_video(VID, tmp_path / VID, None)["status"] == "adiado"
    monkeypatch.setattr(extrair, "obter_info", lambda vid: {**INFO, "duration": 50})
    assert extrair.extrair_video(VID, tmp_path / VID, None) == {"id": VID, "status": "ignorado", "motivo": "curto"}


def test_main_registra_estado(tmp_path, monkeypatch):
    dia = tmp_path / "trab" / "2026-09-29"
    gravar_json(dia / "fila.json", {"hoje": "2026-09-29", "modo": "diario", "videos": [
        {"id": VID, "titulo": "A", "publicado_ts": 1.0, "edicao": "2026-09-28"},
        {"id": "curto000001", "titulo": "B", "publicado_ts": 1.0, "edicao": "2026-09-28"},
        {"id": "quebrado001", "titulo": "C", "publicado_ts": 1.0, "edicao": "2026-09-28"},
    ]})

    def falso(vid, pasta, token):
        if vid == VID:
            return {"id": vid, "status": "ok"}
        if vid == "curto000001":
            return {"id": vid, "status": "ignorado", "motivo": "curto"}
        raise ValueError("inesperado")

    monkeypatch.setattr(extrair, "extrair_video", falso)
    assert extrair.main(["--fila", str(dia / "fila.json"), "--data", str(tmp_path / "data")]) == 0
    assert ler_json(dia / "extracao.json")["ok"] == [VID]
    e = Estado(tmp_path / "data")
    assert e.processados["curto000001"]["ignorado"] == "curto"
    assert e.pendentes["quebrado001"]["tentativas"] == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_extrair.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'extrair'`

- [ ] **Step 3: Implementar `scripts/extrair.py`**

```python
"""Extrai metadados e transcrição de cada vídeo da fila (yt-dlp primeiro, Apify como plano B)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from comum import DATA, gravar_json, ler_json, titulo_e_palestrante, ytdlp_base
from estado import Estado

DURACAO_MINIMA = 180
APIFY_ACTOR = "starvibe~youtube-video-transcript"


def obter_info(vid: str) -> dict:
    cmd = [*ytdlp_base(), "-J", "--skip-download", f"https://www.youtube.com/watch?v={vid}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[-300:] or f"código {r.returncode}")
    return json.loads(r.stdout)


def meta_de_info(info: dict) -> dict:
    curto, palestrante = titulo_e_palestrante(info["title"])
    sb = next((f for f in info.get("formats", []) if f.get("format_id") == "sb0" and f.get("fragments")), None)
    return {
        "id": info["id"],
        "titulo": info["title"],
        "titulo_curto": curto,
        "palestrante": palestrante,
        "descricao": (info.get("description") or "")[:3000],
        "duracao": info.get("duration") or 0,
        "publicado_ts": info.get("timestamp") or info.get("release_timestamp"),
        "live_status": info.get("live_status"),
        "capitulos": [{"t": int(c["start_time"]), "titulo": c["title"]} for c in info.get("chapters") or []],
        "thumbnail": f"https://i.ytimg.com/vi/{info['id']}/maxresdefault.jpg",
        "storyboard": None if sb is None else {
            "largura": sb["width"], "altura": sb["height"], "linhas": sb["rows"], "colunas": sb["columns"],
            "fps": sb["fps"], "fragmentos": [{"url": f["url"], "duracao": f["duration"]} for f in sb["fragments"]],
        },
    }


def meta_de_apify(item: dict) -> dict:
    curto, palestrante = titulo_e_palestrante(item["title"])
    publicado = item.get("published_at")
    return {
        "id": item["video_id"],
        "titulo": item["title"],
        "titulo_curto": curto,
        "palestrante": palestrante,
        "descricao": (item.get("description") or "")[:3000],
        "duracao": item.get("duration_seconds") or 0,
        "publicado_ts": datetime.fromisoformat(publicado.replace("Z", "+00:00")).timestamp() if publicado else None,
        "live_status": None,
        "capitulos": [],
        "thumbnail": f"https://i.ytimg.com/vi/{item['video_id']}/maxresdefault.jpg",
        "storyboard": None,
    }


def escolher_legenda(info: dict) -> str | None:
    ordem = [("subtitles", "en"), ("subtitles", "en-US"), ("automatic_captions", "en-orig"),
             ("automatic_captions", "en")]
    for fonte, lingua in ordem:
        for f in (info.get(fonte) or {}).get(lingua, []):
            if f.get("ext") == "json3":
                return f["url"]
    return None


def baixar_json3(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def segmentos_json3(dados: dict) -> list[tuple[float, str]]:
    segs = []
    for ev in dados.get("events", []):
        partes = ev.get("segs")
        if not partes:
            continue
        texto = "".join(p.get("utf8", "") for p in partes).replace("\n", " ").strip()
        if texto:
            segs.append((ev["tStartMs"] / 1000, texto))
    return segs


def segmentos_apify(item: dict) -> list[tuple[float, str]]:
    return [(float(s["start"]), s["text"].strip()) for s in item.get("transcript") or [] if s.get("text", "").strip()]


def formatar_transcricao(segs: list[tuple[float, str]], janela: int = 30) -> str:
    linhas, inicio, partes = [], None, []
    for t, texto in segs:
        if inicio is None:
            inicio = t
        elif t - inicio >= janela:
            linhas.append(f"[t={int(inicio)}] {' '.join(partes)}")
            inicio, partes = t, []
        partes.append(texto)
    if partes:
        linhas.append(f"[t={int(inicio)}] {' '.join(partes)}")
    return "\n".join(linhas) + "\n"


def transcricao_apify(vid: str, token: str) -> dict:
    url = f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"
    corpo = json.dumps({"youtube_url": f"https://www.youtube.com/watch?v={vid}", "language": "en"}).encode()
    req = urllib.request.Request(url, data=corpo, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        itens = json.load(r)
    if not itens or itens[0].get("status") != "success":
        motivo = itens[0].get("message") if itens else "resposta vazia"
        raise RuntimeError(f"sem transcrição ({motivo})")
    return itens[0]


def extrair_video(vid: str, pasta: Path, token: str | None) -> dict:
    pasta = Path(pasta)
    item_apify, info = None, None
    try:
        info = obter_info(vid)
        meta = meta_de_info(info)
    except Exception as erro_info:
        if not token:
            return {"id": vid, "status": "falha", "etapa": "extracao", "erro": f"yt-dlp: {erro_info}"}
        try:
            item_apify = transcricao_apify(vid, token)
        except Exception as erro_apify:
            return {"id": vid, "status": "falha", "etapa": "extracao",
                    "erro": f"yt-dlp: {erro_info}; apify: {erro_apify}"}
        meta = meta_de_apify(item_apify)

    if meta["live_status"] in ("is_upcoming", "is_live"):
        return {"id": vid, "status": "adiado", "motivo": meta["live_status"]}
    if meta["duracao"] and meta["duracao"] < DURACAO_MINIMA:
        return {"id": vid, "status": "ignorado", "motivo": "curto"}

    segs, erros = [], []
    if info is not None:
        url = escolher_legenda(info)
        if url:
            try:
                segs = segmentos_json3(baixar_json3(url))
            except Exception as e:
                erros.append(f"json3: {e}")
        else:
            erros.append("json3: vídeo sem legenda em inglês")
    if not segs and token:
        try:
            item_apify = item_apify or transcricao_apify(vid, token)
            segs = segmentos_apify(item_apify)
        except Exception as e:
            erros.append(f"apify: {e}")
    if not segs:
        return {"id": vid, "status": "falha", "etapa": "extracao", "erro": "; ".join(erros) or "transcrição vazia"}

    gravar_json(pasta / "meta.json", meta)
    (pasta / "transcricao.txt").write_text(formatar_transcricao(segs), encoding="utf-8")
    return {"id": vid, "status": "ok"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fila", type=Path, required=True)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)

    fila = ler_json(a.fila)
    pasta_dia = a.fila.parent
    token = os.environ.get("APIFY_TOKEN")

    def seguro(v: dict) -> dict:
        try:
            return extrair_video(v["id"], pasta_dia / v["id"], token)
        except Exception as e:
            return {"id": v["id"], "status": "falha", "etapa": "extracao", "erro": f"erro inesperado: {e}"}

    with ThreadPoolExecutor(a.workers) as ex:
        resultados = list(ex.map(seguro, fila["videos"]))

    estado = Estado(a.data)
    por_id = {v["id"]: v for v in fila["videos"]}
    for r in resultados:
        v = por_id[r["id"]]
        if r["status"] == "falha":
            estado.registrar_falha(v["id"], v["titulo"], v["publicado_ts"], r["etapa"], r["erro"])
        elif r["status"] == "ignorado":
            estado.marcar_processado(v["id"], v["edicao"], ignorado=r["motivo"])
    estado.salvar()

    ok = [r["id"] for r in resultados if r["status"] == "ok"]
    gravar_json(pasta_dia / "extracao.json", {"ok": ok, "resultados": resultados})
    contagem = {s: sum(r["status"] == s for r in resultados) for s in ("ok", "falha", "ignorado", "adiado")}
    print(" ".join(f"{k}={n}" for k, n in contagem.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_extrair.py -v`
Expected: 10 passed

- [ ] **Step 5: Teste de fumaça com um vídeo real (rede)**

Run:
```bash
.venv/bin/python -c "
import sys; sys.path.insert(0, 'scripts')
import extrair, tempfile, pathlib
d = pathlib.Path(tempfile.mkdtemp())
print(extrair.extrair_video('474j-n1Ltxc', d / 'v', None))
print((d / 'v' / 'transcricao.txt').read_text()[:300])
"
```
Expected: `{'id': '474j-n1Ltxc', 'status': 'ok'}` e as primeiras linhas começando com `[t=12] How's everyone doing?`

- [ ] **Step 6: Commit**

```bash
git add scripts/extrair.py tests/test_extrair.py
git commit -m "feat: extração de metadados e transcrição com fallback Apify"
```

---

### Task 5: Schemas e validação

**Files:**
- Create: `schemas/analise.schema.json`, `schemas/explicacao.schema.json`, `schemas/curadoria.schema.json`, `schemas/dia.schema.json`, `scripts/validar.py`, `tests/test_validar.py`, `tests/fixtures/video/meta.json`, `tests/fixtures/video/analise.json`, `tests/fixtures/video/explicacao.json`, `tests/fixtures/video/curadoria.json`

**Interfaces:**
- Consumes: `comum.SCHEMAS, ler_json`.
- Produces: `validar(dados, nome: str) -> list[str]` (nome ∈ `analise|explicacao|curadoria|dia`), `checar_analise(analise, meta) -> list[str]`, `erros_de(tipo, arquivo: Path, meta: Path|None) -> list[str]`, CLI `validar.py TIPO ARQUIVO [--meta META]` (imprime `ok` e sai 0, ou lista erros e sai 1). Fixtures `tests/fixtures/video/*` usadas nas Tasks 7 e 8.

- [ ] **Step 1: Criar os schemas**

`schemas/analise.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Saída do analista-video",
  "type": "object",
  "additionalProperties": false,
  "required": ["id", "tese", "tldr", "tema", "complexidade", "ideias", "conceitos", "leitura_critica", "acoes", "numeros"],
  "properties": {
    "id": {"type": "string", "minLength": 11, "maxLength": 11},
    "tese": {"type": "string", "minLength": 10, "maxLength": 160},
    "tldr": {"type": "array", "minItems": 3, "maxItems": 3, "items": {"type": "string", "minLength": 10, "maxLength": 280}},
    "tema": {"enum": ["agentes", "evals", "infraestrutura", "produto", "modelos", "engenharia-de-software", "dados-e-rag", "pesquisa", "carreira-e-equipes"]},
    "complexidade": {"type": "integer", "minimum": 1, "maximum": 5},
    "ideias": {
      "type": "array", "minItems": 3, "maxItems": 5,
      "items": {
        "type": "object", "additionalProperties": false, "required": ["titulo", "texto", "momento"],
        "properties": {
          "titulo": {"type": "string", "minLength": 3, "maxLength": 80},
          "texto": {"type": "string", "minLength": 20, "maxLength": 600},
          "momento": {
            "type": "object", "additionalProperties": false, "required": ["t", "descricao", "legenda"],
            "properties": {
              "t": {"type": "integer", "minimum": 0},
              "descricao": {"type": "string", "minLength": 3, "maxLength": 200},
              "legenda": {"type": "string", "minLength": 3, "maxLength": 120}
            }
          }
        }
      }
    },
    "conceitos": {
      "type": "array", "maxItems": 8,
      "items": {
        "type": "object", "additionalProperties": false, "required": ["nome", "traducao", "nivel", "trecho_t"],
        "properties": {
          "nome": {"type": "string", "minLength": 2, "maxLength": 60},
          "traducao": {"type": "string", "maxLength": 80},
          "nivel": {"enum": ["basico", "intermediario", "avancado"]},
          "trecho_t": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "integer", "minimum": 0}}
        }
      }
    },
    "leitura_critica": {"type": "string", "minLength": 20, "maxLength": 600},
    "acoes": {"type": "array", "minItems": 1, "maxItems": 4, "items": {"type": "string", "minLength": 10, "maxLength": 240}},
    "numeros": {
      "type": "array", "maxItems": 4,
      "items": {
        "type": "object", "additionalProperties": false, "required": ["valor", "contexto", "t"],
        "properties": {
          "valor": {"type": "string", "minLength": 1, "maxLength": 16},
          "contexto": {"type": "string", "minLength": 3, "maxLength": 80},
          "t": {"type": "integer", "minimum": 0}
        }
      }
    }
  }
}
```

`schemas/explicacao.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Saída do explicador",
  "type": "object",
  "additionalProperties": false,
  "required": ["id", "conceitos"],
  "properties": {
    "id": {"type": "string", "minLength": 11, "maxLength": 11},
    "conceitos": {
      "type": "array", "minItems": 1, "maxItems": 5,
      "items": {
        "type": "object", "additionalProperties": false,
        "required": ["nome", "analogia", "explicacao", "pre_requisitos", "desenho"],
        "properties": {
          "nome": {"type": "string", "minLength": 2, "maxLength": 60},
          "analogia": {"type": "string", "minLength": 20, "maxLength": 300},
          "explicacao": {"type": "array", "minItems": 3, "maxItems": 5, "items": {"type": "string", "minLength": 10, "maxLength": 300}},
          "pre_requisitos": {"type": "array", "maxItems": 4, "items": {"type": "string", "minLength": 2, "maxLength": 60}},
          "desenho": {
            "type": ["object", "null"], "additionalProperties": false, "required": ["nos"],
            "properties": {
              "nos": {
                "type": "array", "minItems": 2, "maxItems": 5,
                "items": {
                  "type": "object", "additionalProperties": false, "required": ["rotulo", "nota"],
                  "properties": {
                    "rotulo": {"type": "string", "minLength": 2, "maxLength": 24},
                    "nota": {"type": "string", "minLength": 2, "maxLength": 40}
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

`schemas/curadoria.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Saída do curador-prints",
  "type": "object",
  "additionalProperties": false,
  "required": ["id", "momentos"],
  "properties": {
    "id": {"type": "string", "minLength": 11, "maxLength": 11},
    "momentos": {
      "type": "array",
      "items": {
        "type": "object", "additionalProperties": false, "required": ["i", "frame", "nota"],
        "properties": {
          "i": {"type": "integer", "minimum": 0},
          "frame": {"type": ["string", "null"]},
          "nota": {"type": "string", "maxLength": 160}
        }
      }
    }
  }
}
```

`schemas/dia.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Abertura de uma edição, escrita pelo orquestrador",
  "type": "object",
  "additionalProperties": false,
  "required": ["edicao", "titulo", "abertura", "ordem", "conceitos_novos"],
  "properties": {
    "edicao": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
    "titulo": {"type": "string", "minLength": 5, "maxLength": 70},
    "abertura": {"type": "string", "minLength": 40, "maxLength": 900},
    "ordem": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 11, "maxLength": 11}},
    "conceitos_novos": {"type": "array", "items": {"type": "string"}}
  }
}
```

- [ ] **Step 2: Criar as fixtures de um vídeo**

`tests/fixtures/video/meta.json`:
```json
{
  "id": "abcdefghijk",
  "titulo": "Scale the Judgment, Not the Model — Andrew Orobator, Reddit",
  "titulo_curto": "Scale the Judgment, Not the Model",
  "palestrante": "Andrew Orobator, Reddit",
  "descricao": "Como o Reddit escala avaliação com modelos pequenos.",
  "duracao": 900,
  "publicado_ts": 1790524817,
  "live_status": "not_live",
  "capitulos": [{"t": 0, "titulo": "Intro"}],
  "thumbnail": "https://i.ytimg.com/vi/abcdefghijk/maxresdefault.jpg",
  "storyboard": null
}
```

`tests/fixtures/video/analise.json`:
```json
{
  "id": "abcdefghijk",
  "tese": "Escale o julgamento humano, não o tamanho do modelo",
  "tldr": [
    "O Reddit usa modelos pequenos guiados por critérios escritos por pessoas.",
    "O ganho veio de melhorar as instruções de avaliação, sem trocar de modelo.",
    "Evals feitos com exemplos reais evitaram regressões em produção."
  ],
  "tema": "evals",
  "complexidade": 4,
  "ideias": [
    {"titulo": "Critério antes de modelo", "texto": "A equipe escreveu critérios claros do que é uma boa resposta antes de testar qualquer modelo novo.", "momento": {"t": 30, "descricao": "slide com a lista de critérios", "legenda": "Os critérios que guiam o avaliador"}},
    {"titulo": "Um juiz automático", "texto": "Um modelo lê cada resposta e dá nota seguindo os critérios, como um corretor de prova com gabarito.", "momento": {"t": 300, "descricao": "diagrama do fluxo do juiz", "legenda": "O fluxo do avaliador automático"}},
    {"titulo": "Medir antes de trocar", "texto": "Toda troca de modelo passa pela mesma bateria de testes antes de ir para produção.", "momento": {"t": 600, "descricao": "gráfico de acurácia por versão", "legenda": "A acurácia subiu sem trocar o modelo"}}
  ],
  "conceitos": [
    {"nome": "eval", "traducao": "avaliação", "nivel": "basico", "trecho_t": [20, 90]},
    {"nome": "LLM-as-judge", "traducao": "modelo como juiz", "nivel": "avancado", "trecho_t": [280, 420]}
  ],
  "leitura_critica": "Os números vêm de um único produto do Reddit e não há comparação com outras equipes.",
  "acoes": ["Escreva três critérios do que é uma boa resposta antes de trocar de modelo."],
  "numeros": [{"valor": "3x", "contexto": "menos regressões após os evals", "t": 610}]
}
```

`tests/fixtures/video/explicacao.json`:
```json
{
  "id": "abcdefghijk",
  "conceitos": [
    {
      "nome": "LLM-as-judge",
      "analogia": "Um LLM como juiz é como um corretor de redação que recebe o gabarito antes de ler as provas.",
      "explicacao": [
        "Você escreve os critérios de uma boa resposta.",
        "Um modelo lê cada resposta junto com os critérios.",
        "Ele devolve uma nota e o motivo da nota."
      ],
      "pre_requisitos": ["eval"],
      "desenho": {"nos": [
        {"rotulo": "CRITÉRIOS", "nota": "escritos por pessoas"},
        {"rotulo": "JUIZ", "nota": "modelo lê e avalia"},
        {"rotulo": "NOTA", "nota": "com justificativa"}
      ]}
    }
  ]
}
```

`tests/fixtures/video/curadoria.json`:
```json
{
  "id": "abcdefghijk",
  "momentos": [
    {"i": 0, "frame": "frames/m0_1.jpg", "nota": "slide com a lista de critérios"},
    {"i": 1, "frame": null, "nota": "só o rosto do palestrante"},
    {"i": 2, "frame": "frames/m2_0.jpg", "nota": "gráfico de acurácia"}
  ]
}
```

- [ ] **Step 3: Escrever o teste que falha**

`tests/test_validar.py`:
```python
import copy
from pathlib import Path

import validar
from comum import gravar_json, ler_json

FIX = Path(__file__).parent / "fixtures" / "video"
ANALISE = ler_json(FIX / "analise.json")
META = ler_json(FIX / "meta.json")


def test_fixtures_validas():
    assert validar.validar(ANALISE, "analise") == []
    assert validar.validar(ler_json(FIX / "explicacao.json"), "explicacao") == []
    assert validar.validar(ler_json(FIX / "curadoria.json"), "curadoria") == []
    assert validar.checar_analise(ANALISE, META) == []


def test_campo_faltando_e_tema_invalido():
    ruim = copy.deepcopy(ANALISE)
    del ruim["leitura_critica"]
    ruim["tema"] = "marketing"
    erros = validar.validar(ruim, "analise")
    assert any("leitura_critica" in e for e in erros)
    assert any(e.startswith("tema:") for e in erros)


def test_minuto_alem_da_duracao_e_id_trocado():
    ruim = copy.deepcopy(ANALISE)
    ruim["ideias"][1]["momento"]["t"] = 1200
    ruim["numeros"][0]["t"] = 999
    ruim["id"] = "zzzzzzzzzzz"
    erros = validar.checar_analise(ruim, META)
    assert "ideias/1/momento/t: 1200s passa da duração 900s" in erros
    assert "numeros/0/t: 999s passa da duração 900s" in erros
    assert any(e.startswith("id:") for e in erros)


def test_dia():
    ok = {"edicao": "2026-09-28", "titulo": "O dia dos juízes", "abertura": "a" * 50,
          "ordem": ["abcdefghijk"], "conceitos_novos": ["LLM-as-judge"]}
    assert validar.validar(ok, "dia") == []
    assert validar.validar({**ok, "edicao": "28/09/2026"}, "dia") != []


def test_cli(tmp_path, capsys):
    arq = tmp_path / "analise.json"
    gravar_json(arq, ANALISE)
    assert validar.main(["analise", str(arq), "--meta", str(FIX / "meta.json")]) == 0
    assert capsys.readouterr().out.strip() == "ok"
    gravar_json(arq, {**ANALISE, "tldr": ["curta"]})
    assert validar.main(["analise", str(arq)]) == 1
    assert validar.main(["analise", str(tmp_path / "nao-existe.json")]) == 1
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_validar.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'validar'`

- [ ] **Step 5: Implementar `scripts/validar.py`**

```python
"""Valida as saídas dos agentes contra os schemas e contra os metadados do vídeo."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from comum import SCHEMAS, ler_json

_validadores: dict[str, Draft202012Validator] = {}


def _validador(nome: str) -> Draft202012Validator:
    if nome not in _validadores:
        _validadores[nome] = Draft202012Validator(ler_json(SCHEMAS / f"{nome}.schema.json"))
    return _validadores[nome]


def validar(dados, nome: str) -> list[str]:
    erros = sorted(_validador(nome).iter_errors(dados), key=lambda e: [str(p) for p in e.absolute_path])
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '(raiz)'}: {e.message}" for e in erros]


def checar_analise(analise: dict, meta: dict) -> list[str]:
    erros = []
    if analise.get("id") != meta["id"]:
        erros.append(f"id: esperado {meta['id']}, veio {analise.get('id')}")
    duracao = meta.get("duracao") or 0
    if not duracao:
        return erros
    for i, ideia in enumerate(analise.get("ideias", [])):
        t = ideia.get("momento", {}).get("t", 0)
        if t > duracao:
            erros.append(f"ideias/{i}/momento/t: {t}s passa da duração {duracao}s")
    for i, numero in enumerate(analise.get("numeros", [])):
        if numero.get("t", 0) > duracao:
            erros.append(f"numeros/{i}/t: {numero['t']}s passa da duração {duracao}s")
    return erros


def erros_de(tipo: str, arquivo: Path, meta: Path | None = None) -> list[str]:
    try:
        dados = ler_json(arquivo)
    except json.JSONDecodeError as e:
        return [f"(raiz): JSON inválido: {e}"]
    if dados is None:
        return [f"(raiz): arquivo não encontrado: {arquivo}"]
    erros = validar(dados, tipo)
    if tipo == "analise" and meta is not None and not erros:
        erros += checar_analise(dados, ler_json(meta))
    return erros


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tipo", choices=["analise", "explicacao", "curadoria", "dia"])
    ap.add_argument("arquivo", type=Path)
    ap.add_argument("--meta", type=Path, default=None)
    a = ap.parse_args(argv)
    erros = erros_de(a.tipo, a.arquivo, a.meta)
    if erros:
        print("\n".join(erros))
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_validar.py -v`
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
git add schemas scripts/validar.py tests/test_validar.py tests/fixtures/video
git commit -m "feat: schemas das saídas dos agentes e validação"
```

---

### Task 6: Captura de frames

**Files:**
- Create: `scripts/capturar_frames.py`, `tests/test_capturar_frames.py`

**Interfaces:**
- Consumes: `comum.*`; `meta.json` (Task 4) e `analise.json` (formato da Task 5) em cada pasta de vídeo.
- Produces: `posicao_storyboard(sb: dict, t: float) -> tuple[str, tuple[int,int,int,int]]`, `frames_do_video(vid, t, prefixo: Path) -> list[Path]`, `frames_do_storyboard(sb, t, prefixo: Path) -> list[Path]`, `frame_thumbnail(url, prefixo: Path) -> list[Path]`, `capturar_momentos(pasta: Path, video_fn=..., storyboard_fn=..., thumb_fn=...) -> dict`, `main(argv)`. Arquivo `frames/manifesto.json` = `{"id", "momentos": [{"i", "t", "fonte": "video"|"storyboard"|"thumbnail"|null, "frames": ["frames/m0_0.jpg", ...], "erros": [...]}]}` com caminhos relativos à pasta do vídeo.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_capturar_frames.py`:
```python
import shutil
from pathlib import Path

from PIL import Image

import capturar_frames as cf
from comum import gravar_json, ler_json

FIX = Path(__file__).parent / "fixtures" / "video"
SB = {"largura": 320, "altura": 180, "linhas": 3, "colunas": 3, "fps": 0.2026,
      "fragmentos": [{"url": f"https://sb/M{i}.jpg", "duracao": 44.4} for i in range(18)]}


def test_posicao_storyboard():
    assert cf.posicao_storyboard(SB, 0) == ("https://sb/M0.jpg", (0, 0, 320, 180))
    # t=50 -> quadro 10 -> folha 1, posição 1
    assert cf.posicao_storyboard(SB, 50) == ("https://sb/M1.jpg", (320, 0, 640, 180))
    # além do fim: último quadro da última folha
    assert cf.posicao_storyboard(SB, 10000) == ("https://sb/M17.jpg", (640, 360, 960, 540))


def _pasta(tmp_path, storyboard=None):
    pasta = tmp_path / "abcdefghijk"
    pasta.mkdir()
    shutil.copy(FIX / "analise.json", pasta / "analise.json")
    meta = ler_json(FIX / "meta.json")
    meta["storyboard"] = storyboard
    gravar_json(pasta / "meta.json", meta)
    return pasta


def _gera(n):
    def fn(*args):
        prefixo = args[-1]
        saida = []
        for k in range(n):
            p = prefixo.with_name(f"{prefixo.name}_{k}.jpg")
            Image.new("RGB", (64, 36)).save(p)
            saida.append(p)
        return saida
    return fn


def _falha(*_a):
    raise RuntimeError("bloqueado")


def test_video_ok(tmp_path):
    pasta = _pasta(tmp_path)
    m = cf.capturar_momentos(pasta, video_fn=_gera(3), storyboard_fn=_falha, thumb_fn=_falha)
    assert [x["fonte"] for x in m["momentos"]] == ["video"] * 3
    assert m["momentos"][0]["frames"] == ["frames/m0_0.jpg", "frames/m0_1.jpg", "frames/m0_2.jpg"]
    assert ler_json(pasta / "frames" / "manifesto.json") == m


def test_cai_para_storyboard(tmp_path):
    pasta = _pasta(tmp_path, storyboard=SB)
    m = cf.capturar_momentos(pasta, video_fn=_falha, storyboard_fn=_gera(3), thumb_fn=_falha)
    assert m["momentos"][1]["fonte"] == "storyboard"
    assert "video: bloqueado" in m["momentos"][1]["erros"]


def test_thumbnail_so_uma_vez_e_bloco_sem_imagem(tmp_path):
    pasta = _pasta(tmp_path, storyboard=None)
    m = cf.capturar_momentos(pasta, video_fn=_falha, storyboard_fn=_falha, thumb_fn=_gera(1))
    assert [x["fonte"] for x in m["momentos"]] == ["thumbnail", None, None]
    assert m["momentos"][1]["frames"] == []


def test_nada_funciona(tmp_path):
    pasta = _pasta(tmp_path, storyboard=SB)
    m = cf.capturar_momentos(pasta, video_fn=_falha, storyboard_fn=_falha, thumb_fn=_falha)
    assert all(x["fonte"] is None and x["frames"] == [] for x in m["momentos"])
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_capturar_frames.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'capturar_frames'`

- [ ] **Step 3: Implementar `scripts/capturar_frames.py`**

```python
"""Captura frames candidatos para o momento de cada ideia (vídeo, storyboard ou thumbnail)."""
from __future__ import annotations

import argparse
import subprocess
import tempfile
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

from PIL import Image

from comum import gravar_json, ler_json, ytdlp_base

_cache_sprites: dict[str, bytes] = {}


def baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 aprendendo-ai"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def posicao_storyboard(sb: dict, t: float) -> tuple[str, tuple[int, int, int, int]]:
    por_folha = sb["linhas"] * sb["colunas"]
    idx = max(0, int(t * sb["fps"]))
    folha = idx // por_folha
    if folha >= len(sb["fragmentos"]):
        folha, pos = len(sb["fragmentos"]) - 1, por_folha - 1
    else:
        pos = idx % por_folha
    x = (pos % sb["colunas"]) * sb["largura"]
    y = (pos // sb["colunas"]) * sb["altura"]
    return sb["fragmentos"][folha]["url"], (x, y, x + sb["largura"], y + sb["altura"])


def frames_do_video(vid: str, t: float, prefixo: Path) -> list[Path]:
    inicio = max(0, int(t) - 1)
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [*ytdlp_base(), "-f", "bv*[height<=720][ext=mp4]/bv*[height<=720]",
               "--download-sections", f"*{inicio}-{inicio + 3}", "-o", str(Path(tmp) / "clip.%(ext)s"),
               f"https://www.youtube.com/watch?v={vid}"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        clipes = sorted(Path(tmp).glob("clip.*"))
        if r.returncode != 0 or not clipes:
            raise RuntimeError(r.stderr.strip()[-200:] or "download do trecho falhou")
        for k, deslocamento in enumerate((0.3, 1.3, 2.3)):
            destino = prefixo.with_name(f"{prefixo.name}_{k}.jpg")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(deslocamento), "-i", str(clipes[0]),
                            "-frames:v", "1", "-q:v", "3", str(destino)], timeout=60, check=False)
            if destino.exists():
                frames.append(destino)
    if not frames:
        raise RuntimeError("ffmpeg não gerou frames")
    return frames


def frames_do_storyboard(sb: dict, t: float, prefixo: Path) -> list[Path]:
    frames = []
    for k, deslocamento in enumerate((-5, 0, 5)):
        url, caixa = posicao_storyboard(sb, max(0, t + deslocamento))
        if url not in _cache_sprites:
            _cache_sprites[url] = baixar(url)
        destino = prefixo.with_name(f"{prefixo.name}_{k}.jpg")
        with Image.open(BytesIO(_cache_sprites[url])) as sprite:
            sprite.convert("RGB").crop(caixa).save(destino, "JPEG", quality=90)
        frames.append(destino)
    return frames


def frame_thumbnail(url: str, prefixo: Path) -> list[Path]:
    destino = prefixo.with_name(f"{prefixo.name}_0.jpg")
    for tentativa in (url, url.replace("maxresdefault", "hqdefault")):
        try:
            destino.write_bytes(baixar(tentativa))
            return [destino]
        except Exception:
            continue
    raise RuntimeError("thumbnail indisponível")


def capturar_momentos(pasta: Path, video_fn=frames_do_video, storyboard_fn=frames_do_storyboard,
                      thumb_fn=frame_thumbnail) -> dict:
    pasta = Path(pasta)
    meta = ler_json(pasta / "meta.json")
    analise = ler_json(pasta / "analise.json")
    dir_frames = pasta / "frames"
    dir_frames.mkdir(exist_ok=True)
    thumbnail_usada = False
    momentos = []
    for i, ideia in enumerate(analise["ideias"]):
        t = ideia["momento"]["t"]
        prefixo = dir_frames / f"m{i}"
        tentativas = [("video", lambda: video_fn(meta["id"], t, prefixo))]
        if meta.get("storyboard"):
            tentativas.append(("storyboard", lambda: storyboard_fn(meta["storyboard"], t, prefixo)))
        if not thumbnail_usada:
            tentativas.append(("thumbnail", lambda: thumb_fn(meta["thumbnail"], prefixo)))
        fonte, frames, erros = None, [], []
        for nome, fn in tentativas:
            try:
                frames, fonte = fn(), nome
                break
            except Exception as e:
                erros.append(f"{nome}: {e}")
        thumbnail_usada = thumbnail_usada or fonte == "thumbnail"
        momentos.append({"i": i, "t": t, "fonte": fonte,
                         "frames": [f.relative_to(pasta).as_posix() for f in frames], "erros": erros})
    manifesto = {"id": meta["id"], "momentos": momentos}
    gravar_json(dir_frames / "manifesto.json", manifesto)
    return manifesto


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dia", type=Path, required=True, help="pasta trabalho/<hoje>")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    ids = [vid for vid in ler_json(a.dia / "extracao.json")["ok"] if (a.dia / vid / "analise.json").exists()]
    with ThreadPoolExecutor(a.workers) as ex:
        manifestos = list(ex.map(lambda vid: capturar_momentos(a.dia / vid), ids))
    fontes = Counter(m["fonte"] for man in manifestos for m in man["momentos"])
    print(f"{len(ids)} vídeo(s): " + " ".join(f"{k or 'sem_imagem'}={n}" for k, n in fontes.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_capturar_frames.py -v`
Expected: 5 passed

- [ ] **Step 5: Teste de fumaça do storyboard e do trecho de vídeo (rede)**

Run:
```bash
.venv/bin/python -c "
import sys; sys.path.insert(0, 'scripts')
import extrair, capturar_frames as cf, tempfile, pathlib
d = pathlib.Path(tempfile.mkdtemp())
meta = extrair.meta_de_info(extrair.obter_info('474j-n1Ltxc'))
print(cf.frames_do_storyboard(meta['storyboard'], 300, d / 'sb'))
print(cf.frames_do_video('474j-n1Ltxc', 300, d / 'vd'))
"
```
Expected: duas listas com 3 caminhos `.jpg` cada. Abra um de cada com o Read para confirmar que são imagens do talk.

- [ ] **Step 6: Commit**

```bash
git add scripts/capturar_frames.py tests/test_capturar_frames.py
git commit -m "feat: captura de frames com fallback de storyboard e thumbnail"
```

---

### Task 7: Consolidação por vídeo e glossário

**Files:**
- Create: `scripts/consolidar.py`, `tests/test_consolidar.py`

**Interfaces:**
- Consumes: `comum.*`, `estado.Estado`, `validar.erros_de`; na pasta de cada vídeo: `meta.json`, `analise.json`, `explicacao.json` (opcional), `curadoria.json` (opcional), `frames/manifesto.json` (opcional); `trabalho/<hoje>/fila.json` e `extracao.json`.
- Produces: `escolher_frame(pasta, i, manifesto, curadoria) -> Path|None`, `salvar_imagem(origem, destino)`, `consolidar_video(pasta, edicao, pasta_data, pasta_site, glossario: dict) -> dict`, `main(argv)`. Arquivos: `data/videos/<id>.json` (chaves: `id, titulo, titulo_curto, palestrante, url, duracao, publicado_ts, edicao, tese, tldr, tema, complexidade, ideias[{titulo,texto,t,legenda,print}], conceitos[{nome,traducao,nivel,chave,analogia,explicacao,pre_requisitos,desenho,no_glossario}], leitura_critica, acoes, numeros`), `data/glossario.json` (dict `chave -> {chave,nome,traducao,analogia,explicacao,video_id,video_titulo,edicao}`), `site/img/<id>/<i>.jpg`, `trabalho/<hoje>/publicados.json` (`{id: edicao}`).

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_consolidar.py`:
```python
import shutil
from pathlib import Path

from PIL import Image

import consolidar
from comum import gravar_json, ler_json
from estado import Estado

FIX = Path(__file__).parent / "fixtures" / "video"
VID = "abcdefghijk"


def _pasta(tmp_path, com_curadoria=True):
    pasta = tmp_path / "trab" / VID
    (pasta / "frames").mkdir(parents=True)
    for nome in ("meta.json", "analise.json", "explicacao.json"):
        shutil.copy(FIX / nome, pasta / nome)
    if com_curadoria:
        shutil.copy(FIX / "curadoria.json", pasta / "curadoria.json")
    momentos = []
    for i in range(3):
        frames = []
        for k in range(3):
            Image.new("RGB", (1280, 720), (i * 60, k * 60, 90)).save(pasta / "frames" / f"m{i}_{k}.jpg")
            frames.append(f"frames/m{i}_{k}.jpg")
        momentos.append({"i": i, "t": 0, "fonte": "video", "frames": frames, "erros": []})
    gravar_json(pasta / "frames" / "manifesto.json", {"id": VID, "momentos": momentos})
    return pasta


def test_consolidar_video(tmp_path):
    pasta = _pasta(tmp_path)
    glossario = {}
    v = consolidar.consolidar_video(pasta, "2026-09-28", tmp_path / "data", tmp_path / "site", glossario)
    assert v["url"] == f"https://www.youtube.com/watch?v={VID}"
    assert [i["print"] for i in v["ideias"]] == [f"img/{VID}/0.jpg", None, f"img/{VID}/2.jpg"]
    with Image.open(tmp_path / "site" / "img" / VID / "0.jpg") as im:
        assert im.width <= 960
    eval_, judge = v["conceitos"]
    assert eval_["analogia"] is None and eval_["no_glossario"] is False
    assert judge["analogia"].startswith("Um LLM como juiz")
    assert judge["desenho"]["nos"][0]["rotulo"] == "CRITÉRIOS"
    assert glossario["llm-as-judge"]["video_id"] == VID
    assert glossario["llm-as-judge"]["chave"] == "llm-as-judge"
    assert ler_json(tmp_path / "data" / "videos" / f"{VID}.json") == v


def test_conceito_ja_no_glossario_nao_e_sobrescrito(tmp_path):
    pasta = _pasta(tmp_path)
    glossario = {"eval": {"chave": "eval", "nome": "eval", "video_id": "outro000001"},
                 "llm-as-judge": {"chave": "llm-as-judge", "nome": "LLM-as-judge", "video_id": "outro000001"}}
    v = consolidar.consolidar_video(pasta, "2026-09-28", tmp_path / "data", tmp_path / "site", glossario)
    assert v["conceitos"][0]["no_glossario"] is True
    assert glossario["llm-as-judge"]["video_id"] == "outro000001"


def test_sem_curadoria_usa_frame_do_meio(tmp_path):
    pasta = _pasta(tmp_path, com_curadoria=False)
    assert consolidar.escolher_frame(pasta, 1, ler_json(pasta / "frames" / "manifesto.json"), None) == \
        pasta / "frames" / "m1_1.jpg"


def test_main_valida_e_grava_publicados(tmp_path):
    dia = tmp_path / "trab"
    _pasta(tmp_path)
    ruim = dia / "ruim0000001"
    ruim.mkdir()
    shutil.copy(FIX / "meta.json", ruim / "meta.json")
    gravar_json(ruim / "analise.json", {"id": "ruim0000001"})
    gravar_json(dia / "fila.json", {"hoje": "2026-09-29", "modo": "diario", "videos": [
        {"id": VID, "titulo": "A", "publicado_ts": 1.0, "edicao": "2026-09-28"},
        {"id": "ruim0000001", "titulo": "Ruim", "publicado_ts": 1.0, "edicao": "2026-09-28"},
    ]})
    gravar_json(dia / "extracao.json", {"ok": [VID, "ruim0000001"], "resultados": []})
    rc = consolidar.main(["--dia", str(dia), "--data", str(tmp_path / "data"), "--site", str(tmp_path / "site")])
    assert rc == 0
    assert ler_json(dia / "publicados.json") == {VID: "2026-09-28"}
    assert "llm-as-judge" in ler_json(tmp_path / "data" / "glossario.json")
    assert Estado(tmp_path / "data").pendentes["ruim0000001"]["ultima_etapa"] == "consolidacao"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_consolidar.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'consolidar'`

- [ ] **Step 3: Implementar `scripts/consolidar.py`**

```python
"""Junta análise, explicação e prints de cada vídeo em data/videos/<id>.json e atualiza o glossário."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from comum import DATA, SITE, chave, gravar_json, ler_json
from estado import Estado
from validar import erros_de


def escolher_frame(pasta: Path, i: int, manifesto: dict | None, curadoria: dict | None) -> Path | None:
    if curadoria:
        for m in curadoria["momentos"]:
            if m["i"] == i:
                if m["frame"] is None:
                    return None
                if (pasta / m["frame"]).exists():
                    return pasta / m["frame"]
    for m in (manifesto or {}).get("momentos", []):
        if m["i"] == i and m["frames"]:
            return pasta / m["frames"][len(m["frames"]) // 2]
    return None


def salvar_imagem(origem: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(origem) as im:
        im = im.convert("RGB")
        im.thumbnail((960, 540))
        im.save(destino, "JPEG", quality=80, optimize=True)


def consolidar_video(pasta: Path, edicao: str, pasta_data: Path, pasta_site: Path, glossario: dict) -> dict:
    pasta = Path(pasta)
    meta = ler_json(pasta / "meta.json")
    analise = ler_json(pasta / "analise.json")
    explicacao = ler_json(pasta / "explicacao.json")
    curadoria = ler_json(pasta / "curadoria.json")
    manifesto = ler_json(pasta / "frames" / "manifesto.json")
    vid = meta["id"]

    ideias = []
    for i, ideia in enumerate(analise["ideias"]):
        frame = escolher_frame(pasta, i, manifesto, curadoria)
        caminho_print = None
        if frame is not None and frame.exists():
            caminho_print = f"img/{vid}/{i}.jpg"
            salvar_imagem(frame, Path(pasta_site) / caminho_print)
        ideias.append({"titulo": ideia["titulo"], "texto": ideia["texto"], "t": ideia["momento"]["t"],
                       "legenda": ideia["momento"]["legenda"], "print": caminho_print})

    explicados = {chave(c["nome"]): c for c in (explicacao or {}).get("conceitos", [])}
    conceitos = []
    for c in analise["conceitos"]:
        k = chave(c["nome"])
        e = explicados.get(k)
        item = {"nome": c["nome"], "traducao": c["traducao"], "nivel": c["nivel"], "chave": k,
                "analogia": None, "explicacao": [], "pre_requisitos": [], "desenho": None}
        if e:
            item.update(analogia=e["analogia"], explicacao=e["explicacao"], pre_requisitos=e["pre_requisitos"],
                        desenho=e.get("desenho"))
            glossario.setdefault(k, {"chave": k, "nome": c["nome"], "traducao": c["traducao"],
                                     "analogia": e["analogia"], "explicacao": e["explicacao"], "video_id": vid,
                                     "video_titulo": meta["titulo_curto"], "edicao": edicao})
        item["no_glossario"] = k in glossario and glossario[k]["video_id"] != vid
        conceitos.append(item)

    video = {
        "id": vid, "titulo": meta["titulo"], "titulo_curto": meta["titulo_curto"],
        "palestrante": meta["palestrante"], "url": f"https://www.youtube.com/watch?v={vid}",
        "duracao": meta["duracao"], "publicado_ts": meta["publicado_ts"], "edicao": edicao,
        "tese": analise["tese"], "tldr": analise["tldr"], "tema": analise["tema"],
        "complexidade": analise["complexidade"], "ideias": ideias, "conceitos": conceitos,
        "leitura_critica": analise["leitura_critica"], "acoes": analise["acoes"], "numeros": analise["numeros"],
    }
    gravar_json(Path(pasta_data) / "videos" / f"{vid}.json", video)
    return video


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dia", type=Path, required=True, help="pasta trabalho/<hoje>")
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--site", type=Path, default=SITE)
    a = ap.parse_args(argv)

    fila = {v["id"]: v for v in ler_json(a.dia / "fila.json")["videos"]}
    ok = ler_json(a.dia / "extracao.json")["ok"]
    glossario = ler_json(a.data / "glossario.json", {})
    estado = Estado(a.data)
    publicados = {}
    for vid in ok:
        pasta = a.dia / vid
        if not (pasta / "analise.json").exists():
            continue
        erros = erros_de("analise", pasta / "analise.json", pasta / "meta.json")
        if erros:
            v = fila[vid]
            estado.registrar_falha(vid, v["titulo"], v["publicado_ts"], "consolidacao", "; ".join(erros))
            print(f"{vid}: análise inválida, vai para pendentes")
            continue
        for opcional in ("explicacao", "curadoria"):
            arq = pasta / f"{opcional}.json"
            if arq.exists() and erros_de(opcional, arq):
                arq.rename(arq.with_suffix(".invalido.json"))
                print(f"{vid}: {opcional}.json inválido, ignorado")
        consolidar_video(pasta, fila[vid]["edicao"], a.data, a.site, glossario)
        publicados[vid] = fila[vid]["edicao"]
    gravar_json(a.data / "glossario.json", glossario)
    estado.salvar()
    gravar_json(a.dia / "publicados.json", publicados)
    print(f"{len(publicados)} vídeo(s) consolidado(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Note: `no_glossario` só é verdadeiro quando o conceito foi explicado em **outro** vídeo; o próprio vídeo que originou a entrada mostra a explicação completa.

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_consolidar.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/consolidar.py tests/test_consolidar.py
git commit -m "feat: consolidação por vídeo, imagens e glossário"
```

---

### Task 8: Template Quadro Anotado e montagem do site

**Files:**
- Create: `templates/estilo.css`, `templates/app.js`, `templates/_video.html.j2`, `templates/edicao.html.j2`, `templates/index.html.j2`, `scripts/montar_site.py`, `tests/test_montar_site.py`

**Interfaces:**
- Consumes: `comum.*`, `estado.Estado`; `data/videos/*.json` (formato da Task 7), `data/dias/*.json` (schema `dia`), `data/glossario.json`.
- Produces: `montar(pasta_data: Path, pasta_site: Path) -> list[str]` (edições geradas, mais recente primeiro), `main(argv)`. Arquivos: `site/index.html`, `site/dias/<edicao>.html` (fragmento sem `<html>`), `site/estilo.css`, `site/app.js`, `site/.nojekyll`.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_montar_site.py`:
```python
from pathlib import Path

import montar_site
from comum import gravar_json
from estado import Estado


def video(vid, edicao, **extra):
    base = {
        "id": vid, "titulo": f"Talk {vid} — Ana, Weights & Biases", "titulo_curto": f"Talk {vid}",
        "palestrante": "Ana, Weights & Biases", "url": f"https://www.youtube.com/watch?v={vid}",
        "duracao": 900, "publicado_ts": 1790524817, "edicao": edicao,
        "tese": "Escale o julgamento, não o modelo", "tldr": ["Frase um aqui.", "Frase dois aqui.", "Frase três aqui."],
        "tema": "evals", "complexidade": 4,
        "ideias": [
            {"titulo": "Critério", "texto": "Texto da ideia um.", "t": 312, "legenda": "O slide", "print": f"img/{vid}/0.jpg"},
            {"titulo": "Sem imagem", "texto": "Texto da ideia dois.", "t": 400, "legenda": "Sem print", "print": None},
        ],
        "conceitos": [
            {"nome": "LLM-as-judge", "traducao": "modelo como juiz", "nivel": "avancado", "chave": "llm-as-judge",
             "analogia": "É como um corretor com gabarito.", "explicacao": ["Passo um.", "Passo dois.", "Passo três."],
             "pre_requisitos": ["eval"], "desenho": {"nos": [{"rotulo": "A", "nota": "n1"}, {"rotulo": "B", "nota": "n2"}]},
             "no_glossario": False},
            {"nome": "eval", "traducao": "avaliação", "nivel": "basico", "chave": "eval", "analogia": None,
             "explicacao": [], "pre_requisitos": [], "desenho": None, "no_glossario": True},
            {"nome": "token", "traducao": "pedaço de texto", "nivel": "basico", "chave": "token", "analogia": None,
             "explicacao": [], "pre_requisitos": [], "desenho": None, "no_glossario": False},
        ],
        "leitura_critica": "Amostra de um único produto.", "acoes": ["Escreva três critérios."],
        "numeros": [{"valor": "3x", "contexto": "menos regressões", "t": 610}],
    }
    base.update(extra)
    return base


def preparar(tmp_path):
    data = tmp_path / "data"
    gravar_json(data / "videos" / "aaaaaaaaaaa.json", video("aaaaaaaaaaa", "2026-09-28"))
    gravar_json(data / "videos" / "bbbbbbbbbbb.json", video("bbbbbbbbbbb", "2026-09-28",
                titulo_curto='Agents <script>alert("x")</script> & Co'))
    gravar_json(data / "videos" / "ccccccccccc.json", video("ccccccccccc", "2026-09-27"))
    gravar_json(data / "dias" / "2026-09-28.json", {"edicao": "2026-09-28", "titulo": "O dia dos juízes",
                "abertura": "Hoje dois talks falam de avaliação.", "ordem": ["bbbbbbbbbbb", "aaaaaaaaaaa"],
                "conceitos_novos": []})
    gravar_json(data / "glossario.json", {"eval": {"chave": "eval", "nome": "eval", "traducao": "avaliação",
                "analogia": "Uma prova com gabarito.", "explicacao": ["a", "b", "c"], "video_id": "ccccccccccc",
                "video_titulo": "Talk ccccccccccc", "edicao": "2026-09-27"}})
    e = Estado(data)
    e.registrar_falha("ddddddddddd", "Pendente & cia", 1.0, "extracao", "x")
    for _ in range(3):
        e.registrar_falha("eeeeeeeeeee", "Desistido", 1.0, "extracao", "x")
    e.registrar_execucao(3)
    e.salvar()
    return data


def test_monta_index_e_fragmentos(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    assert montar_site.montar(data, site) == ["2026-09-28", "2026-09-27"]
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "O dia dos juízes" in html
    assert 'data-src="dias/2026-09-27.html"' in html
    assert (site / "dias" / "2026-09-27.html").exists()
    assert "<html" not in (site / "dias" / "2026-09-27.html").read_text(encoding="utf-8")
    for arq in ("estilo.css", "app.js", ".nojekyll"):
        assert (site / arq).exists()


def test_ordem_de_leitura_e_escape(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert html.index('id="v-bbbbbbbbbbb"') < html.index('id="v-aaaaaaaaaaa"')
    assert "<script>alert" not in html
    assert "Agents &lt;script&gt;alert(&#34;x&#34;)&lt;/script&gt; &amp; Co" in html
    assert "Weights &amp; Biases" in html


def test_links_de_minuto_prints_e_conceitos(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert 'href="https://www.youtube.com/watch?v=aaaaaaaaaaa&amp;t=312s"' in html
    assert 'src="img/aaaaaaaaaaa/0.jpg"' in html
    assert "▶ 06:40" in html  # ideia sem print mostra o link do minuto em texto
    assert "É como um corretor com gabarito." in html
    assert 'href="#g-eval"' in html  # conceito já no glossário vira link
    assert "token (pedaço de texto)" in html  # termo básico aparece com tradução
    assert 'id="g-eval"' in html
    assert "●●●●○" in html


def test_rodape(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "Pendente &amp; cia" in html and "(1/3)" in html
    assert "Desistido" in html


def test_site_vazio(tmp_path):
    site = tmp_path / "site"
    assert montar_site.montar(tmp_path / "data", site) == []
    assert "Nenhuma edição publicada ainda." in (site / "index.html").read_text(encoding="utf-8")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_montar_site.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'montar_site'`

- [ ] **Step 3: Criar `templates/estilo.css`**

```css
:root{
  --paper:#F1F1EF;--dot:#CFD1D6;--card:#FFFFFF;--line:#DADCE0;
  --ink:#0B0E14;--ink-2:#434343;--muted:#5D6576;
  --orange:#ED9556;--orange-ink:#B4581A;--navy:#152137;
  --shadow:0 1px 2px rgba(11,14,20,.06),0 10px 24px -12px rgba(11,14,20,.18);
  --display:"Barlow Condensed","Arial Narrow",sans-serif;
  --body:"Barlow","Helvetica Neue",Arial,sans-serif;
  --hand:"Covered By Your Grace",cursive;
  color-scheme:light;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#0D1422;--dot:#1F2B40;--card:#152137;--line:#25334B;
    --ink:#F1F1EF;--ink-2:#CDD1D8;--muted:#9AA3B5;--orange-ink:#F2A66E;--navy:#0A1020;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 24px -12px rgba(0,0,0,.6);
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --paper:#0D1422;--dot:#1F2B40;--card:#152137;--line:#25334B;
  --ink:#F1F1EF;--ink-2:#CDD1D8;--muted:#9AA3B5;--orange-ink:#F2A66E;--navy:#0A1020;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 24px -12px rgba(0,0,0,.6);
  color-scheme:dark;
}
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background-color:var(--paper);background-image:radial-gradient(var(--dot) 1.1px,transparent 1.3px);background-size:22px 22px;color:var(--ink);font:400 17px/1.62 var(--body);padding-inline:16px}
.wrap{max-width:1080px;margin:0 auto;padding:48px 0 80px}
a{color:var(--orange-ink)}
a:focus-visible,button:focus-visible,summary:focus-visible,input:focus-visible{outline:2px solid var(--orange-ink);outline-offset:3px;border-radius:4px}
.label{display:block;font:300 .82rem/1.3 var(--display);letter-spacing:.22em;text-transform:uppercase;color:var(--muted)}
.hand{font:400 1.35rem/1.25 var(--hand);color:var(--orange-ink);margin:.25rem 0 0}
.muted{color:var(--muted)}
h1,h2,h3{font-family:var(--display);font-weight:900;text-transform:uppercase;letter-spacing:-.03em;line-height:.95;margin:0}
h1{font-size:clamp(3rem,11vw,7.4rem);line-height:.88}
h1 .risco{position:relative;display:inline-block}
h1 .risco::after{content:"";position:absolute;left:-2%;right:-2%;bottom:.02em;height:.09em;background:var(--orange);border-radius:99px;transform:rotate(-1deg)}
h2{font-size:clamp(2.1rem,5.4vw,3.4rem)}
h3{font-size:clamp(1.7rem,4vw,2.4rem);overflow-wrap:anywhere}
h4{font:700 1.45rem/1.2 var(--display);margin:0 0 .4rem}
.hero{padding:24px 0 32px}
.abas{display:flex;flex-wrap:wrap;gap:8px 20px;margin:0 0 20px;font:500 1rem var(--display);text-transform:uppercase;letter-spacing:.08em}
.abas a{color:var(--ink);text-decoration:none;border-bottom:2px solid transparent}
.abas a:hover{border-color:var(--orange)}
.filtro{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}
.filtro button,.chip{font:500 .95rem/1 var(--display);border:1.5px solid var(--ink);border-radius:99px;padding:.45em .9em;background:var(--card);color:var(--ink)}
.filtro button{cursor:pointer}
.filtro button[aria-pressed="true"]{background:var(--ink);color:var(--paper)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px 20px;box-shadow:var(--shadow)}
.card p{margin:.3rem 0}
.edicao{margin-top:48px}
.edicao-head{max-width:680px;margin-bottom:24px}
.edicao-head h2{margin:.3rem 0 .6rem}
.abertura{font-size:1.08rem;color:var(--ink-2);margin:0}
.ordem ol{margin:.5rem 0 0;padding-left:1.6rem}
.ordem li::marker{font-family:var(--display);font-weight:900;color:var(--orange-ink)}
.video{margin-top:64px;display:grid;gap:18px}
.video[hidden]{display:none}
.video.feito .sec-titulo h3{text-decoration:line-through;text-decoration-color:var(--orange);text-decoration-thickness:3px}
.sec-head{display:flex;gap:18px;align-items:flex-start}
.step{font:900 clamp(3.4rem,8vw,5.4rem)/.8 var(--display);color:transparent;-webkit-text-stroke:1.6px var(--orange-ink);flex:none}
.sec-titulo{min-width:0}
.chips{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.chip-link{text-decoration:none;border-color:var(--orange-ink);color:var(--orange-ink)}
.estudei{display:inline-flex;gap:6px;align-items:center;font:500 .95rem var(--display);text-transform:uppercase;letter-spacing:.08em;margin-left:auto;cursor:pointer}
.estudei input{accent-color:var(--orange);width:18px;height:18px}
.grid-2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:18px 28px;align-items:start}
.shot{margin:0;background:var(--card);padding:10px 10px 12px;border-radius:6px;box-shadow:var(--shadow);transform:rotate(var(--tilt,0deg))}
.shot img{display:block;width:100%;height:auto;border-radius:3px;background:var(--line)}
.shot figcaption{display:flex;justify-content:space-between;gap:12px;font-size:.88rem;color:var(--muted);margin-top:8px}
.shot figcaption a,.minuto{font:700 .95rem var(--display);white-space:nowrap;text-decoration:none}
.sem-print{margin:0;align-self:center;color:var(--muted);font-size:.95rem}
.casper{position:relative;background:var(--card);border:1.5px dashed var(--orange);border-radius:10px;padding:22px 20px 16px;margin-top:12px}
.casper .tag{position:absolute;top:-15px;left:14px;background:var(--paper);padding:0 8px;font:400 1.2rem/1.3 var(--hand);color:var(--orange-ink)}
.casper p{margin:.2rem 0}
.passos{margin:.6rem 0 0;padding-left:1.4rem}
.passos li::marker{font-family:var(--display);font-weight:700;color:var(--orange-ink)}
.pre{font-size:.92rem;color:var(--muted)}
.fluxo{display:flex;flex-wrap:wrap;align-items:stretch;gap:10px;margin-top:14px}
.no{border:1.5px solid var(--ink);border-radius:8px;padding:10px 14px;background:var(--card);min-width:110px}
.no strong{display:block;font:700 1.05rem/1.1 var(--display);text-transform:uppercase}
.no span{font-size:.85rem;color:var(--muted)}
.no.fim{background:var(--ink);color:var(--paper)}
.no.fim span{color:var(--line)}
.seta{align-self:center;font:700 1.6rem var(--display);color:var(--orange)}
.nums{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.num{background:var(--navy);color:#F1F1EF;border-radius:10px;padding:14px 16px;text-decoration:none}
.num strong{display:block;font:900 2rem/1 var(--display);color:var(--orange)}
.num span{font-size:.85rem;color:#C9CDD4}
.termos{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0}
.termos .label{width:100%}
.acoes{list-style:none;margin:0;padding:0}
.acoes li{display:grid;grid-template-columns:26px 1fr;padding:.25rem 0}
.acoes li::before{content:"→";font:700 1.1rem var(--display);color:var(--orange-ink)}
#arquivo,#glossario{margin-top:88px}
.arquivo{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-top:12px;box-shadow:var(--shadow)}
.arquivo summary{cursor:pointer;padding:14px 18px}
.arquivo .label{display:inline}
.arquivo .conteudo{padding:0 18px 18px}
.arquivo .casper .tag{background:var(--card)}
.glossario{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:26px 18px;margin-top:28px}
.rodape{margin-top:88px;padding-top:18px;border-top:1px solid var(--line);font-size:.9rem;color:var(--muted)}
@media (max-width:560px){.estudei{margin-left:0}.sec-head{gap:12px}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.shot{transform:none}}
```

- [ ] **Step 4: Criar `templates/app.js`**

```javascript
(() => {
  const ler = (k) => { try { return localStorage.getItem(k) === "1"; } catch (e) { return false; } };
  const guardar = (k, v) => { try { v ? localStorage.setItem(k, "1") : localStorage.removeItem(k); } catch (e) {} };
  let temaAtivo = "";

  function aplicarFiltro(raiz = document) {
    raiz.querySelectorAll(".video").forEach((v) => { v.hidden = temaAtivo !== "" && v.dataset.tema !== temaAtivo; });
  }

  function preparar(raiz) {
    raiz.querySelectorAll("input[data-id]").forEach((caixa) => {
      const bloco = caixa.closest(".video");
      caixa.checked = ler("estudei:" + caixa.dataset.id);
      bloco?.classList.toggle("feito", caixa.checked);
      caixa.addEventListener("change", () => {
        guardar("estudei:" + caixa.dataset.id, caixa.checked);
        bloco?.classList.toggle("feito", caixa.checked);
      });
    });
    aplicarFiltro(raiz);
  }

  const carregamentos = new WeakMap();
  function carregar(det) {
    if (!carregamentos.has(det)) {
      const alvo = det.querySelector(".conteudo");
      alvo.textContent = "Carregando…";
      const p = fetch(det.dataset.src)
        .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.text(); })
        .then((html) => { alvo.innerHTML = html; preparar(alvo); })
        .catch(() => {
          carregamentos.delete(det);
          alvo.textContent = "Não consegui carregar esta edição. Feche e abra de novo.";
        });
      carregamentos.set(det, p);
    }
    return carregamentos.get(det);
  }

  document.querySelectorAll("details.arquivo").forEach((d) => d.addEventListener("toggle", () => { if (d.open) carregar(d); }));

  document.querySelectorAll(".filtro button").forEach((b) => b.addEventListener("click", () => {
    temaAtivo = b.dataset.tema;
    document.querySelectorAll(".filtro button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    aplicarFiltro();
  }));

  document.addEventListener("click", async (ev) => {
    const link = ev.target.closest("a[data-edicao]");
    if (!link || document.querySelector(link.getAttribute("href"))) return;
    const det = document.querySelector(`details.arquivo[data-src="dias/${link.dataset.edicao}.html"]`);
    if (!det) return;
    ev.preventDefault();
    det.open = true;
    await carregar(det);
    const suave = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.querySelector(link.getAttribute("href"))?.scrollIntoView({ behavior: suave ? "smooth" : "auto" });
  });

  preparar(document);
})();
```

- [ ] **Step 5: Criar `templates/_video.html.j2`**

```jinja
{% macro minuto(v, t) -%}
<a class="minuto" href="{{ v.url }}&amp;t={{ t }}s" target="_blank" rel="noopener">▶ {{ t|tempo }}</a>
{%- endmacro %}

{% macro bloco(v, n) -%}
<article class="video" id="v-{{ v.id }}" data-tema="{{ v.tema }}">
  <header class="sec-head">
    <span class="step" aria-hidden="true">{{ "%02d"|format(n) }}</span>
    <div class="sec-titulo">
      <h3>{{ v.titulo_curto }}</h3>
      <p class="hand">{{ v.tese }}</p>
    </div>
  </header>

  <div class="chips">
    <span class="chip">{{ TEMAS.get(v.tema, v.tema) }}</span>
    <span class="chip">{{ v.duracao|tempo }}</span>
    <span class="chip" title="Complexidade {{ v.complexidade }} de 5">{{ "●" * v.complexidade }}{{ "○" * (5 - v.complexidade) }}</span>
    {% if v.palestrante %}<span class="chip">{{ v.palestrante }}</span>{% endif %}
    <a class="chip chip-link" href="{{ v.url }}" target="_blank" rel="noopener">Assistir no YouTube</a>
    <label class="estudei"><input type="checkbox" data-id="{{ v.id }}"> estudei</label>
  </div>

  <div class="card">
    <span class="label">Em 3 frases</span>
    {% for frase in v.tldr %}<p>{{ frase }}</p>{% endfor %}
  </div>

  {% for ideia in v.ideias %}
  <div class="grid-2">
    <div class="card">
      <h4>{{ ideia.titulo }}</h4>
      <p>{{ ideia.texto }}</p>
    </div>
    {% if ideia.print %}
    <figure class="shot" style="--tilt: {{ '-0.6deg' if loop.index is odd else '0.6deg' }}">
      <img src="{{ ideia.print }}" alt="{{ ideia.legenda }}" loading="lazy" width="960" height="540">
      <figcaption><span>{{ ideia.legenda }}</span>{{ minuto(v, ideia.t) }}</figcaption>
    </figure>
    {% else %}
    <p class="sem-print">{{ minuto(v, ideia.t) }} {{ ideia.legenda }}</p>
    {% endif %}
  </div>
  {% endfor %}

  {% if v.numeros %}
  <div class="nums">
    {% for num in v.numeros %}
    <a class="num" href="{{ v.url }}&amp;t={{ num.t }}s" target="_blank" rel="noopener"><strong>{{ num.valor }}</strong><span>{{ num.contexto }} · {{ num.t|tempo }}</span></a>
    {% endfor %}
  </div>
  {% endif %}

  {% for c in v.conceitos if c.analogia %}
  <div class="casper">
    <span class="tag">analogia</span>
    <p><strong>{{ c.nome }}{% if c.traducao and c.traducao|lower != c.nome|lower %} ({{ c.traducao }}){% endif %}.</strong> {{ c.analogia }}</p>
    <ol class="passos">{% for passo in c.explicacao %}<li>{{ passo }}</li>{% endfor %}</ol>
    {% if c.desenho %}
    <div class="fluxo">
      {% for no in c.desenho.nos %}
      <div class="no{% if loop.last %} fim{% endif %}"><strong>{{ no.rotulo }}</strong><span>{{ no.nota }}</span></div>
      {% if not loop.last %}<span class="seta" aria-hidden="true">→</span>{% endif %}
      {% endfor %}
    </div>
    {% endif %}
    {% if c.pre_requisitos %}<p class="pre">Ajuda saber antes: {{ c.pre_requisitos|join(", ") }}</p>{% endif %}
  </div>
  {% endfor %}

  {% set no_glossario = v.conceitos|rejectattr("analogia")|selectattr("no_glossario")|list %}
  {% set termos = v.conceitos|rejectattr("analogia")|rejectattr("no_glossario")|list %}
  {% if no_glossario or termos %}
  <p class="termos">
    <span class="label">Termos do talk</span>
    {% for c in no_glossario %}<a class="chip" href="#g-{{ c.chave|slug }}">{{ c.nome }} · no glossário</a>{% endfor %}
    {% for c in termos %}<span class="chip">{{ c.nome }}{% if c.traducao and c.traducao|lower != c.nome|lower %} ({{ c.traducao }}){% endif %}</span>{% endfor %}
  </p>
  {% endif %}

  <div class="casper">
    <span class="tag">leitura crítica</span>
    <p>{{ v.leitura_critica }}</p>
  </div>

  <div class="card">
    <h4>O que fazer com isso</h4>
    <ul class="acoes">{% for a in v.acoes %}<li>{{ a }}</li>{% endfor %}</ul>
  </div>
</article>
{%- endmacro %}
```

- [ ] **Step 6: Criar `templates/edicao.html.j2`**

```jinja
{% from "_video.html.j2" import bloco with context %}
<section class="edicao" id="e-{{ edicao }}">
  <div class="edicao-head">
    <span class="label">Edição · {{ data_fmt }} · {{ videos|length }} {{ "vídeo" if videos|length == 1 else "vídeos" }}</span>
    <h2>{{ dia.titulo if dia else "Talks do dia" }}</h2>
    {% if dia %}<p class="abertura">{{ dia.abertura }}</p>{% endif %}
  </div>
  <nav class="card ordem" aria-label="Ordem de leitura">
    <span class="label">Ordem de leitura</span>
    <ol>{% for v in videos %}<li><a href="#v-{{ v.id }}">{{ v.titulo_curto }}</a> <span class="muted">· {{ v.duracao|tempo }}</span></li>{% endfor %}</ol>
  </nav>
  {% for v in videos %}{{ bloco(v, loop.index) }}{% endfor %}
</section>
```

- [ ] **Step 7: Criar `templates/index.html.j2`**

```jinja
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aprendendo AI</title>
<meta name="description" content="Resumos diários dos talks do canal AI Engineer, explicados no estilo Quadro Anotado.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@300;500;700;900&family=Barlow:ital,wght@0,400;0,600;1,400&family=Covered+By+Your+Grace&display=swap">
<link rel="stylesheet" href="estilo.css">
</head>
<body>
<main class="wrap">
  <header class="hero">
    <span class="label">Estudo diário · canal AI Engineer{% if atual %} · {{ atual.data_fmt }}{% endif %}</span>
    <h1>Aprendendo <span class="risco">AI</span></h1>
    <p class="hand">um talk por bloco, explicado como numa aula particular</p>
  </header>

  <nav class="abas" aria-label="Seções">
    <a href="#hoje">Última edição</a>
    <a href="#arquivo">Edições anteriores</a>
    <a href="#glossario">Glossário</a>
  </nav>

  {% if temas_presentes %}
  <div class="filtro" role="group" aria-label="Filtrar por tema">
    <button type="button" data-tema="" aria-pressed="true">Todos</button>
    {% for t in temas_presentes %}<button type="button" data-tema="{{ t }}" aria-pressed="false">{{ TEMAS.get(t, t) }}</button>{% endfor %}
  </div>
  {% endif %}

  <div id="hoje">
    {% if atual %}
      {% with edicao=atual.edicao, data_fmt=atual.data_fmt, dia=atual.dia, videos=atual.videos %}{% include "edicao.html.j2" %}{% endwith %}
    {% else %}
      <p class="card">Nenhuma edição publicada ainda.</p>
    {% endif %}
  </div>

  <section id="arquivo">
    <h2>Edições anteriores</h2>
    {% for e in anteriores %}
    <details class="arquivo" data-src="dias/{{ e.edicao }}.html">
      <summary><span class="label">{{ e.data_fmt }}</span> <strong>{{ e.titulo or "Talks do dia" }}</strong> <span class="muted">· {{ e.n }} {{ "vídeo" if e.n == 1 else "vídeos" }}</span></summary>
      <div class="conteudo" aria-live="polite"></div>
    </details>
    {% else %}
    <p class="muted">Ainda não há edições anteriores.</p>
    {% endfor %}
  </section>

  <section id="glossario">
    <h2>Glossário</h2>
    <p class="hand">tudo que você já estudou</p>
    <div class="glossario">
      {% for g in glossario %}
      <div class="casper" id="g-{{ g.chave|slug }}">
        <span class="tag">{{ g.nome }}</span>
        <p>{% if g.traducao %}<em>{{ g.traducao }}.</em> {% endif %}{{ g.analogia }}</p>
        <ol class="passos">{% for p in g.explicacao %}<li>{{ p }}</li>{% endfor %}</ol>
        <p class="pre">Apareceu em <a href="#v-{{ g.video_id }}" data-edicao="{{ g.edicao }}">{{ g.video_titulo }}</a></p>
      </div>
      {% else %}
      <p class="muted">Os conceitos explicados vão aparecer aqui.</p>
      {% endfor %}
    </div>
  </section>

  <footer class="rodape">
    {% if execucao %}<p>Última execução: {{ execucao.em_fmt }} · {{ execucao.videos }} {{ "vídeo" if execucao.videos == 1 else "vídeos" }}</p>{% endif %}
    {% if pendentes %}<p>Tentando de novo: {% for p in pendentes %}<a href="https://www.youtube.com/watch?v={{ p.id }}" target="_blank" rel="noopener">{{ p.titulo }}</a> ({{ p.tentativas }}/3){% if not loop.last %}; {% endif %}{% endfor %}</p>{% endif %}
    {% if abandonados %}<p>Não processados: {% for p in abandonados %}<a href="https://www.youtube.com/watch?v={{ p.id }}" target="_blank" rel="noopener">{{ p.titulo }}</a>{% if not loop.last %}; {% endif %}{% endfor %}</p>{% endif %}
  </footer>
</main>
<script src="app.js" defer></script>
</body>
</html>
```

- [ ] **Step 8: Implementar `scripts/montar_site.py`**

```python
"""Monta o site estático (site/) a partir de data/, no template Quadro Anotado."""
from __future__ import annotations

import argparse
import shutil
from collections import defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from comum import DATA, SITE, TEMAS, TEMPLATES, chave, fmt_data, fmt_datahora, fmt_tempo, ler_json, slug
from estado import Estado


def _ambiente() -> Environment:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["tempo"] = fmt_tempo
    env.filters["slug"] = slug
    env.globals["TEMAS"] = TEMAS
    return env


def _ordenar(videos: list[dict], dia: dict | None) -> list[dict]:
    posicao = {vid: i for i, vid in enumerate((dia or {}).get("ordem", []))}
    return sorted(videos, key=lambda v: (posicao.get(v["id"], len(posicao)), v.get("publicado_ts") or 0))


def montar(pasta_data: Path, pasta_site: Path) -> list[str]:
    pasta_data, pasta_site = Path(pasta_data), Path(pasta_site)
    env = _ambiente()
    por_edicao: dict[str, list] = defaultdict(list)
    for arq in sorted((pasta_data / "videos").glob("*.json")):
        v = ler_json(arq)
        por_edicao[v["edicao"]].append(v)
    dias = {arq.stem: ler_json(arq) for arq in (pasta_data / "dias").glob("*.json")}
    edicoes = sorted(por_edicao, reverse=True)

    def contexto(e: str) -> dict:
        return {"edicao": e, "data_fmt": fmt_data(e), "dia": dias.get(e), "videos": _ordenar(por_edicao[e], dias.get(e))}

    (pasta_site / "dias").mkdir(parents=True, exist_ok=True)
    fragmento = env.get_template("edicao.html.j2")
    for e in edicoes:
        (pasta_site / "dias" / f"{e}.html").write_text(fragmento.render(**contexto(e)), encoding="utf-8")

    estado = Estado(pasta_data)
    execucao = dict(estado.execucao)
    if execucao.get("em"):
        execucao["em_fmt"] = fmt_datahora(execucao["em"])
    glossario = sorted(ler_json(pasta_data / "glossario.json", {}).values(), key=lambda g: chave(g["nome"]))
    index = env.get_template("index.html.j2").render(
        atual=contexto(edicoes[0]) if edicoes else None,
        anteriores=[{"edicao": e, "data_fmt": fmt_data(e), "titulo": (dias.get(e) or {}).get("titulo"),
                     "n": len(por_edicao[e])} for e in edicoes[1:]],
        glossario=glossario,
        execucao=execucao or None,
        pendentes=[{"id": vid, **estado.pendentes[vid]} for vid in estado.pendentes_ativos()],
        abandonados=[{"id": vid, **p} for vid, p in estado.abandonados().items()],
        temas_presentes=sorted({v["tema"] for vs in por_edicao.values() for v in vs}),
    )
    (pasta_site / "index.html").write_text(index, encoding="utf-8")
    for estatico in ("estilo.css", "app.js"):
        shutil.copy(TEMPLATES / estatico, pasta_site / estatico)
    (pasta_site / ".nojekyll").touch()
    return edicoes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--site", type=Path, default=SITE)
    a = ap.parse_args(argv)
    edicoes = montar(a.data, a.site)
    print(f"site montado com {len(edicoes)} edição(ões) em {a.site}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 9: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_montar_site.py -v`
Expected: 5 passed. Se `test_ordem_de_leitura_e_escape` falhar só pela forma das aspas escapadas, confira a saída real com `grep -o "Agents[^<]*" site/index.html` e ajuste o teste para a forma que o Jinja gera (`&#34;` é o padrão do MarkupSafe).

- [ ] **Step 10: Conferir o visual com dados de exemplo**

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0, 'tests'); sys.path.insert(0, 'scripts')
import pathlib, test_montar_site as t, montar_site
base = pathlib.Path('trabalho/amostra'); base.mkdir(parents=True, exist_ok=True)
data = t.preparar(base); montar_site.montar(data, base / 'site')
"
```
Crie `.claude/launch.json` (se não existir) com uma configuração `amostra` que rode `python3 -m http.server 8765 -d trabalho/amostra/site` na porta 8765, abra com `preview_start` e confira: papel pontilhado, título condensado, número vazado laranja, polaroide inclinada, caixas tracejadas com etiqueta, abertura de edição anterior carregando ao clicar, filtro de tema, checkbox "estudei" riscando o título, e largura de 400px sem rolagem lateral (`resize_window` com 400x800). Volte o tamanho com o preset `desktop`.

- [ ] **Step 11: Commit**

```bash
git add templates scripts/montar_site.py tests/test_montar_site.py
git commit -m "feat: template Quadro Anotado e montagem do site"
```

---

### Task 9: Agentes, receita da rotina e CLAUDE.md

**Files:**
- Create: `.claude/agents/analista-video.md`, `.claude/agents/explicador.md`, `.claude/agents/curador-prints.md`, `ROTINA.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: CLIs das Tasks 2 a 8 (`detectar.py`, `extrair.py`, `validar.py`, `capturar_frames.py`, `consolidar.py`, `montar_site.py`, `estado.py`), schemas da Task 5.
- Produces: subagentes `analista-video` (model `sonnet`), `explicador` (model `opus`), `curador-prints` (model `haiku`); receita `ROTINA.md` que a rotina da nuvem executa.

- [ ] **Step 1: Criar `.claude/agents/analista-video.md`**

```markdown
---
name: analista-video
description: Lê a transcrição de um talk do canal AI Engineer e grava a síntese estruturada em analise.json. Use um por vídeo.
model: sonnet
tools: Read, Write, Bash
---

Você transforma um talk técnico em material de estudo para um leitor brasileiro que usa IA no trabalho, mas ainda não tem base técnica profunda.

## Entrada

O orquestrador informa a pasta do vídeo (ex.: `trabalho/2026-09-29/474j-n1Ltxc`) e a lista de conceitos que já estão no glossário. Leia:

- `meta.json`: título, palestrante, descrição, duração, capítulos.
- `transcricao.txt`: parágrafos no formato `[t=SEGUNDOS] texto`. É legenda automática em inglês: nomes de empresas e produtos costumam sair errados. Corrija pelo contexto e pela descrição.

## Saída

Grave `<pasta>/analise.json` seguindo exatamente `schemas/analise.schema.json`. Depois rode:

    python3 scripts/validar.py analise <pasta>/analise.json --meta <pasta>/meta.json

Se aparecer qualquer erro, corrija o arquivo e rode de novo até imprimir `ok`. Responda ao orquestrador apenas com `ok <id>` ou `erro <id>: <motivo>`.

## Campos

- `id`: o id do vídeo (11 caracteres, igual ao de `meta.json`).
- `tese`: a ideia central em uma linha, no tom de anotação de professor. Até 160 caracteres.
- `tldr`: exatamente 3 frases.
- `tema`: um de `agentes`, `evals`, `infraestrutura`, `produto`, `modelos`, `engenharia-de-software`, `dados-e-rag`, `pesquisa`, `carreira-e-equipes`.
- `complexidade` (1 a 5): 1 = qualquer pessoa que usa ChatGPT entende; 3 = precisa conhecer agentes, RAG ou evals; 5 = pesquisa, treino de modelos ou matemática.
- `ideias`: de 3 a 5. Cada uma tem `momento.t` em segundos inteiros, escolhido onde a tela provavelmente mostra algo útil (slide, gráfico, demo, código). Use os `[t=...]` da transcrição e pistas como "as you can see", "this chart", "let me show you". `momento.descricao` diz o que deve estar na tela; `momento.legenda` diz o que o print prova, em uma linha.
- `conceitos`: até 8 termos técnicos que o leitor precisa entender para acompanhar o talk. `nivel`: `basico`, `intermediario` ou `avancado`. `trecho_t` = `[início, fim]` em segundos onde o conceito é discutido. Use o mesmo `nome` que já está no glossário quando for o mesmo conceito.
- `leitura_critica`: onde o talk é pitch de produto, onde falta evidência, amostra pequena ou conflito de interesse.
- `acoes`: de 1 a 4 ações concretas para quem usa IA no trabalho.
- `numeros`: até 4 números ditos no vídeo, cada um com o segundo (`t`) em que aparece. Nunca invente número.

## Regras de escrita

- Português do Brasil. Termo técnico em inglês na primeira vez com tradução: "eval (avaliação)".
- Frases curtas e diretas, na voz ativa.
- Número só com a fonte (o minuto do vídeo).
- Proibido: o molde "não é X, é Y"; travessão para apartes; frase de efeito com dois-pontos; superlativos vazios ("revolucionário", "incrível"); jargão sem explicação; emoji.
```

- [ ] **Step 2: Criar `.claude/agents/explicador.md`**

```markdown
---
name: explicador
description: Explica conceitos técnicos difíceis de um talk com analogia do dia a dia e passos simples, gravando explicacao.json. Use só quando o orquestrador indicar.
model: opus
tools: Read, Write, Bash
---

Você é o professor que explica no quadro. O leitor usa IA no trabalho, mas não tem base técnica profunda. Ele precisa sair entendendo o mecanismo, não só o nome.

## Entrada

O orquestrador informa a pasta do vídeo e a lista de conceitos a explicar (nomes exatamente como em `analise.json`). Leia `analise.json` e, em `transcricao.txt`, só os parágrafos dentro do `trecho_t` de cada conceito. Não leia a transcrição inteira.

## Saída

Grave `<pasta>/explicacao.json` seguindo `schemas/explicacao.schema.json`, com um item por conceito pedido e o mesmo `nome`. Depois rode:

    python3 scripts/validar.py explicacao <pasta>/explicacao.json

Corrija até imprimir `ok`. Responda apenas `ok <id>` ou `erro <id>: <motivo>`.

## Para cada conceito

- `analogia`: uma frase no formato "X é como Y", com algo do dia a dia (cozinha, trânsito, escritório, escola, esporte). Sem jargão dentro da analogia.
- `explicacao`: de 3 a 5 passos curtos, do mais simples ao mais técnico. O primeiro passo precisa ser entendível por alguém que nunca ouviu o termo.
- `pre_requisitos`: até 4 conceitos que ajudam a entender este (pode ser lista vazia).
- `desenho`: só quando o conceito é um fluxo ou mecanismo com etapas. De 2 a 5 nós, cada um com `rotulo` curto em maiúsculas (até 24 caracteres) e `nota` curta (até 40). O último nó é o resultado. Nos outros casos, `null`.

## Regras de escrita

- Português do Brasil. Termo técnico em inglês na primeira vez com tradução.
- Frases curtas e diretas, na voz ativa.
- Proibido: o molde "não é X, é Y"; travessão para apartes; frase de efeito com dois-pontos; superlativos vazios; emoji.
```

- [ ] **Step 3: Criar `.claude/agents/curador-prints.md`**

```markdown
---
name: curador-prints
description: Olha os frames capturados de um vídeo e escolhe o melhor para cada momento, gravando curadoria.json.
model: haiku
tools: Read, Write, Bash
---

Você escolhe a imagem que prova cada ideia do talk.

## Entrada

O orquestrador informa a pasta do vídeo. Leia `frames/manifesto.json` e `analise.json`. Para o momento `i`, `analise.json` → `ideias[i].momento.descricao` diz o que deveria aparecer na tela.

## Como escolher

Para cada momento do manifesto, abra cada imagem listada em `frames` (use Read no caminho `<pasta>/<frame>`; o Read mostra a imagem) e escolha uma:

- Prefira slide, gráfico, código, diagrama ou demo legível e ligado à descrição.
- Evite rosto do palestrante em close, tela preta, transição borrada, plateia ou logo do evento.
- Se nenhuma servir, use `null`.
- Momentos com `frames` vazio recebem `null`.

## Saída

Grave `<pasta>/curadoria.json`:

    {"id": "<id>", "momentos": [{"i": 0, "frame": "frames/m0_1.jpg", "nota": "slide com a lista de critérios"}]}

`frame` é o caminho exatamente como está no manifesto, ou `null`. `nota` descreve o que a imagem mostra, em até 160 caracteres, em português. Depois rode:

    python3 scripts/validar.py curadoria <pasta>/curadoria.json

Corrija até imprimir `ok`. Responda apenas `ok <id>` ou `erro <id>: <motivo>`.
```

- [ ] **Step 4: Criar `ROTINA.md`**

````markdown
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
pip install -q -r requirements.txt
python3 scripts/estado.py hoje
python3 scripts/estado.py modo
```

Anote `HOJE` (primeira saída) e `MODO` (`backfill` ou `diario`).

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
````

- [ ] **Step 5: Criar `CLAUDE.md`**

```markdown
# Aprendendo AI

Rotina que transforma os talks do canal AI Engineer em blocos de estudo em português, publicados em GitHub Pages no estilo Quadro Anotado (`docs/guia-quadro-anotado.pdf`).

- Spec: `docs/superpowers/specs/2026-09-29-rotina-aprendizado-ai-design.md`
- Receita da rotina diária: `ROTINA.md`. Só execute quando pedirem explicitamente.
- Branch única: `claude/biblioteca`.
- Testes: `.venv/bin/pytest` (local) ou `python3 -m pytest` (nuvem).
- Nenhum modelo escreve HTML: o site sai de `scripts/montar_site.py` + `templates/`.
- `data/` é estado de produção (processados, glossário, vídeos). Não edite à mão sem necessidade.
```

- [ ] **Step 6: Conferir que os agentes estão bem formados**

Run: `head -5 .claude/agents/*.md && .venv/bin/pytest -q`
Expected: cada arquivo começa com `---`, `name`, `description`, `model`, `tools`; todos os testes passam.

- [ ] **Step 7: Commit**

```bash
git add .claude/agents ROTINA.md CLAUDE.md
git commit -m "feat: subagentes, receita da rotina e CLAUDE.md"
```

---

### Task 10: Teste local ponta a ponta com 2 vídeos

**Files:**
- Modify: `data/*` e `site/*` (gerados pela execução real; entram no git)

**Interfaces:**
- Consumes: tudo das Tasks 1 a 9.
- Produces: primeira edição real publicada localmente, aprovada pelo usuário.

- [ ] **Step 1: Detectar e extrair 2 vídeos reais**

```bash
.venv/bin/python scripts/detectar.py --backfill 2 --limite 2
.venv/bin/python scripts/extrair.py --fila trabalho/$(.venv/bin/python scripts/estado.py hoje)/fila.json
```
Expected: `2 vídeo(s) na fila` e `ok=2 falha=0 ...`.

- [ ] **Step 2: Rodar os passos 3 a 9 do `ROTINA.md` nesta sessão**

Siga `ROTINA.md` a partir do passo 3, com esta sessão como orquestradora. Para os subagentes, use a ferramenta Agent com `subagent_type` `analista-video`, `explicador` e `curador-prints` se estiverem disponíveis; se não, use `general-purpose` com `model` `sonnet`, `opus` e `haiku`, respectivamente, e a instrução "Siga `.claude/agents/<agente>.md` para a pasta X". Dispare os 2 analistas na mesma mensagem.

- [ ] **Step 3: Montar o site e revisar o visual**

```bash
.venv/bin/python scripts/estado.py execucao --videos 2
.venv/bin/python scripts/montar_site.py
```
Adicione a `.claude/launch.json` uma configuração `site` com `python3 -m http.server 8766 -d site` na porta 8766 e abra com `preview_start`. Confira os mesmos pontos do Step 10 da Task 8, agora com conteúdo real, e leia os dois blocos em busca de violações das regras de escrita.

- [ ] **Step 4: Aprovação do usuário**

Mostre o site ao usuário e pergunte se o visual e o tom estão aprovados. Ajustes de visual voltam para `templates/` (e o teste da Task 8 roda de novo); ajustes de tom voltam para `.claude/agents/*.md`. Repita os Steps 2 e 3 só nos vídeos afetados até a aprovação.

- [ ] **Step 5: Marcar como processados e commitar**

```bash
.venv/bin/python scripts/estado.py processado --arquivo trabalho/$(.venv/bin/python scripts/estado.py hoje)/publicados.json
.venv/bin/python scripts/montar_site.py
git add data site .claude/launch.json
git commit -m "edição local de teste: 2 vídeos"
```

---

### Task 11: Repositório no GitHub e publicação no Pages

**Files:**
- Create: `.github/workflows/pages.yml`, `.github/workflows/testes.yml`

**Interfaces:**
- Consumes: branch `claude/biblioteca` com o site da Task 10.
- Produces: repositório público `aprendendo-ai` com `claude/biblioteca` como branch padrão e o site no ar em `https://<usuario>.github.io/aprendendo-ai/`.

- [ ] **Step 1: Criar os workflows**

`.github/workflows/pages.yml`:
```yaml
name: Publicar site
on:
  push:
    branches: [claude/biblioteca]
    paths: ["site/**"]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
      - id: deploy
        uses: actions/deploy-pages@v4
```

`.github/workflows/testes.yml`:
```yaml
name: Testes
on:
  push:
    branches: [claude/biblioteca]
    paths: ["scripts/**", "tests/**", "templates/**", "schemas/**", "requirements.txt"]
  workflow_dispatch:
jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python -m pytest -q
```

```bash
git add .github
git commit -m "ci: deploy do Pages e testes"
```

- [ ] **Step 2: Instalar e autenticar o `gh`**

```bash
brew install gh
```
O login é interativo e fica com o usuário. Peça para ele rodar `gh auth login` no terminal (GitHub.com, HTTPS, login pelo navegador) e avisar quando terminar. Confira com `gh auth status`.

- [ ] **Step 3: Criar o repositório público e enviar**

Confirme com o usuário antes de rodar (cria um repositório público):
```bash
gh repo create aprendendo-ai --public --source . --remote origin --push
gh repo view --json defaultBranchRef -q .defaultBranchRef.name
```
Expected: `claude/biblioteca` (a primeira branch enviada vira a padrão). Se não for, rode `gh repo edit --default-branch claude/biblioteca`.

- [ ] **Step 4: Ativar o Pages via Actions e publicar**

```bash
gh api -X POST "repos/{owner}/aprendendo-ai/pages" -f build_type=workflow
gh workflow run pages.yml
gh run watch "$(gh run list --workflow pages.yml --limit 1 --json databaseId -q '.[0].databaseId')"
gh api "repos/{owner}/aprendendo-ai/pages" -q .html_url
```
Expected: o run termina com sucesso e a URL do site aparece. Abra a URL com `preview_start` e confira que o site é o mesmo da Task 10.

---

### Task 12: Ambiente e rotina na nuvem, primeira execução

**Files:** nenhum no repositório (configuração em claude.ai/code).

**Interfaces:**
- Consumes: repositório da Task 11, `ROTINA.md`.
- Produces: ambiente `aprendendo-ai` e rotina diária; primeira execução real (backfill de 7 dias) publicada.

- [ ] **Step 1: Usuário cria o ambiente em claude.ai/code**

Passe ao usuário este roteiro (ele faz na interface; nenhuma credencial passa por esta conversa):

1. Conectar o GitHub e dar acesso ao repositório `aprendendo-ai`.
2. Criar o ambiente `aprendendo-ai`:
   - **Rede:** nível *Custom*, mantendo a lista padrão e adicionando `youtube.com`, `www.youtube.com`, `*.googlevideo.com`, `i.ytimg.com`, `api.apify.com`, `fonts.googleapis.com`.
   - **Setup script:**
     ```bash
     #!/bin/bash
     set -e
     apt-get update -qq && apt-get install -y -qq ffmpeg
     pip install -q yt-dlp "jsonschema>=4.21" "jinja2>=3.1" "pillow>=10" "pytest>=8"
     ```
   - **Variáveis:** `BASH_MAX_TIMEOUT_MS=600000` e `BASH_DEFAULT_TIMEOUT_MS=300000`.
   - **Credencial:** `APIFY_TOKEN` com o token do console da Apify (Settings → API & Integrations), colado pelo próprio usuário.

- [ ] **Step 2: Usuário cria a rotina**

- Repositório: `aprendendo-ai`; ambiente: `aprendendo-ai`; modelo: Opus.
- Prompt: `Execute a rotina conforme o ROTINA.md.`
- Agendamento: diário às 07:00 (horário local de Brasília). Se a interface permitir, deixe a rotina pausada até a Task 13.

- [ ] **Step 3: Primeira execução com "Run now"**

O usuário clica em **Run now**. Como `data/config.json` ainda não tem `backfill_concluido`, a rotina roda o backfill de 7 dias (cerca de 35 vídeos; os 2 da Task 10 são pulados).

- [ ] **Step 4: Medir e revisar**

Com o usuário, leia o relatório final da execução (passo 11 do `ROTINA.md`) e confira:

- os subagentes rodaram em paralelo ou houve plano B;
- houve bloqueio do YouTube (muitos `storyboard`/`thumbnail`, ou extrações via Apify);
- tempo total e consumo informado na sessão;
- pendentes e motivos.

Abra o site publicado e revise junto com o usuário. Problemas de código viram correção local (com teste), commit e push em `claude/biblioteca`; depois, nova execução com "Run now".

---

### Task 13: Ativar o agendamento diário

**Files:** nenhum.

- [ ] **Step 1: Ativar**

Com a aprovação do usuário na Task 12, ele ativa (ou confirma) o agendamento diário às 07:00 da rotina.

- [ ] **Step 2: Conferir a primeira execução agendada**

No dia seguinte, confira em claude.ai/code/routines que a execução das 07:00 terminou, que `data/config.json` tem `backfill_concluido: true` e que o site ganhou a edição de ontem.
