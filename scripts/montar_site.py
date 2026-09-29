"""Monta o site estático (site/) a partir de data/, no template Quadro Anotado.

Saída: index.html (home com a última edição em destaque e as anteriores agrupadas por semana),
edicoes/<data>.html (uma página por edição), glossario.html e status.html.
"""
from __future__ import annotations

import argparse
import shutil
import unicodedata
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from comum import (DATA, MESES, SITE, TEMAS, TEMPLATES, chave, fmt_data, fmt_datahora, fmt_tempo, ler_json,
                   listar_json, slug)
from estado import MAX_TENTATIVAS, Estado


def _ambiente() -> Environment:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["tempo"] = fmt_tempo
    env.filters["slug"] = slug
    env.globals["TEMAS"] = TEMAS
    env.globals["MAX_TENTATIVAS"] = MAX_TENTATIVAS
    return env


def _ordenar(videos: list[dict], dia: dict | None) -> list[dict]:
    posicao = {vid: i for i, vid in enumerate((dia or {}).get("ordem", []))}
    return sorted(videos, key=lambda v: (posicao.get(v["id"], len(posicao)), v.get("publicado_ts") or 0))


def _duracao_fmt(segundos: int) -> str:
    minutos = round(segundos / 60)
    h, m = divmod(minutos, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def _semanas(edicoes: list[dict]) -> list[dict]:
    """Agrupa edições (já em ordem decrescente) pela semana que começa na segunda-feira."""
    grupos: dict[date, list] = {}
    for ed in edicoes:
        d = date.fromisoformat(ed["edicao"])
        grupos.setdefault(d - timedelta(days=d.weekday()), []).append(ed)
    return [{"rotulo": f"Semana de {seg.day} {MESES[seg.month - 1]}", "edicoes": eds} for seg, eds in grupos.items()]


def _letra(nome: str) -> str:
    inicial = unicodedata.normalize("NFKD", nome.strip()[:1]).encode("ascii", "ignore").decode().upper()
    return inicial if inicial.isalpha() else "#"


def _glossario(entradas: list[dict]) -> list[dict]:
    grupos: dict[str, list] = defaultdict(list)
    for g in sorted(entradas, key=lambda g: chave(g["nome"])):
        g = dict(g)
        g.setdefault("chave", chave(g["nome"]))
        if not g.get("aparicoes"):
            g["aparicoes"] = [{"video_id": g["video_id"], "video_titulo": g["video_titulo"], "edicao": g["edicao"]}]
        grupos[_letra(g["nome"])].append(g)
    return [{"letra": letra, "termos": grupos[letra]} for letra in sorted(grupos, key=lambda x: (x == "#", x))]


def montar(pasta_data: Path, pasta_site: Path) -> list[str]:
    pasta_data, pasta_site = Path(pasta_data), Path(pasta_site)
    env = _ambiente()
    por_edicao: dict[str, list] = defaultdict(list)
    for arq in listar_json(pasta_data / "videos"):
        v = ler_json(arq)
        por_edicao[v["edicao"]].append(v)
    dias = {arq.stem: ler_json(arq) for arq in listar_json(pasta_data / "dias")}

    edicoes = []
    for e in sorted(por_edicao, reverse=True):
        dia = dias.get(e)
        videos = _ordenar(por_edicao[e], dia)
        temas_ids = list(dict.fromkeys(v["tema"] for v in videos))
        edicoes.append({
            "edicao": e, "data_fmt": fmt_data(e), "dia": dia, "videos": videos,
            "titulo": (dia or {}).get("titulo") or "Talks do dia",
            "temas": [TEMAS.get(t, t) for t in temas_ids], "temas_ids": temas_ids,
            "duracao_fmt": _duracao_fmt(sum(v.get("duracao") or 0 for v in videos)),
        })

    estado = Estado(pasta_data)
    execucao = dict(estado.execucao)
    if execucao.get("em"):
        execucao["em_fmt"] = fmt_datahora(execucao["em"])
    comum = {"execucao": execucao or None}

    for antigo in ("dias",):  # fragmentos da versão com edições recolhidas
        if (pasta_site / antigo).exists():
            shutil.rmtree(pasta_site / antigo)
    (pasta_site / "edicoes").mkdir(parents=True, exist_ok=True)
    pagina_edicao = env.get_template("edicao.html.j2")
    for i, ed in enumerate(edicoes):
        html = pagina_edicao.render(
            raiz="../", pagina="edicao", edicao=ed["edicao"], data_fmt=ed["data_fmt"], dia=ed["dia"],
            videos=ed["videos"], titulo=ed["titulo"], duracao_fmt=ed["duracao_fmt"],
            anterior=edicoes[i + 1] if i + 1 < len(edicoes) else None,
            proxima=edicoes[i - 1] if i > 0 else None, **comum)
        (pasta_site / "edicoes" / f"{ed['edicao']}.html").write_text(html, encoding="utf-8")

    # "continuar de onde parei": talks da mais nova para a mais antiga, na ordem de leitura
    talks = [{"id": v["id"], "href": f"edicoes/{ed['edicao']}.html#v-{v['id']}", "titulo": v["titulo_curto"]}
             for ed in edicoes for v in ed["videos"]]
    anteriores = edicoes[1:]
    index = env.get_template("index.html.j2").render(
        raiz="", pagina="home", atual=edicoes[0] if edicoes else None, semanas=_semanas(anteriores),
        temas_todos=sorted({t for ed in anteriores for t in ed["temas_ids"]}), talks=talks, **comum)
    (pasta_site / "index.html").write_text(index, encoding="utf-8")

    entradas = list(ler_json(pasta_data / "glossario.json", {}).values())
    html = env.get_template("glossario.html.j2").render(
        raiz="", pagina="glossario", grupos=_glossario(entradas), total=len(entradas),
        com_analogia=sum(1 for g in entradas if g.get("analogia")), **comum)
    (pasta_site / "glossario.html").write_text(html, encoding="utf-8")

    html = env.get_template("status.html.j2").render(
        raiz="", pagina="status",
        pendentes=[{"id": vid, **estado.pendentes[vid]} for vid in estado.pendentes_ativos()],
        abandonados=[{"id": vid, **p} for vid, p in estado.abandonados().items()],
        total_videos=sum(len(ed["videos"]) for ed in edicoes), total_edicoes=len(edicoes), **comum)
    (pasta_site / "status.html").write_text(html, encoding="utf-8")

    for estatico in ("estilo.css", "app.js", "favicon.svg"):
        shutil.copy(TEMPLATES / estatico, pasta_site / estatico)
    (pasta_site / ".nojekyll").touch()
    return [ed["edicao"] for ed in edicoes]


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
