"""Monta o site estático (site/) a partir de data/, no template Quadro Anotado."""
from __future__ import annotations

import argparse
import shutil
from collections import defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from comum import (DATA, SITE, TEMAS, TEMPLATES, chave, fmt_data, fmt_datahora, fmt_tempo, ler_json,
                   listar_json, slug)
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
    for arq in listar_json(pasta_data / "videos"):
        v = ler_json(arq)
        por_edicao[v["edicao"]].append(v)
    dias = {arq.stem: ler_json(arq) for arq in listar_json(pasta_data / "dias")}
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
