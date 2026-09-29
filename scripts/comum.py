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


def listar_json(pasta) -> list[Path]:
    """Arquivos .json de uma pasta, em ordem, sem os ocultos (o macOS cria "._x.json" em discos ExFAT)."""
    p = Path(pasta)
    if not p.is_dir():
        return []
    return sorted(a for a in p.glob("*.json") if not a.name.startswith("."))


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


def ffmpeg_bin() -> str:
    """ffmpeg do sistema; sem ele, o binário estático do pacote imageio-ffmpeg (instalável via pip)."""
    sistema = shutil.which("ffmpeg")
    if sistema:
        return sistema
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def ytdlp_base() -> list[str]:
    cmd = [sys.executable, "-m", "yt_dlp", "--no-warnings"]
    if shutil.which("deno") is None and shutil.which("node"):
        cmd += ["--js-runtimes", "node"]
    if shutil.which("ffmpeg") is None:
        cmd += ["--ffmpeg-location", ffmpeg_bin()]
    return cmd
