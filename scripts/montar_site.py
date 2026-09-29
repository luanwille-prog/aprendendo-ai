"""Monta o site estático (site/) a partir de data/, no template Quadro Anotado.

Saída: index.html (home com a última edição em destaque e cartões de todas as edições),
edicoes/<data>.html (uma página por edição) e glossario.html.
"""
from __future__ import annotations

import argparse
import shutil
from collections import defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from comum import (DATA, SITE, TEMAS, TEMPLATES, chave, fmt_data, fmt_datahora, fmt_tempo, ler_json,
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
        edicoes.append({
            "edicao": e, "data_fmt": fmt_data(e), "dia": dia, "videos": videos,
            "titulo": (dia or {}).get("titulo") or "Talks do dia",
            "temas": [TEMAS.get(t, t) for t in dict.fromkeys(v["tema"] for v in videos)],
            "temas_ids": list(dict.fromkeys(v["tema"] for v in videos)),
        })

    estado = Estado(pasta_data)
    execucao = dict(estado.execucao)
    if execucao.get("em"):
        execucao["em_fmt"] = fmt_datahora(execucao["em"])
    comum = {
        "execucao": execucao or None,
        "pendentes": [{"id": vid, **estado.pendentes[vid]} for vid in estado.pendentes_ativos()],
        "abandonados": [{"id": vid, **p} for vid, p in estado.abandonados().items()],
    }

    if (pasta_site / "dias").exists():  # fragmentos da versão com edições recolhidas
        shutil.rmtree(pasta_site / "dias")
    (pasta_site / "edicoes").mkdir(parents=True, exist_ok=True)
    pagina_edicao = env.get_template("edicao.html.j2")
    for i, ed in enumerate(edicoes):
        proxima = edicoes[i - 1] if i > 0 else None
        anterior = edicoes[i + 1] if i + 1 < len(edicoes) else None
        html = pagina_edicao.render(raiz="../", pagina="edicao", edicao=ed["edicao"], data_fmt=ed["data_fmt"],
                                    dia=ed["dia"], videos=ed["videos"], titulo=ed["titulo"], temas=ed["temas_ids"],
                                    anterior=anterior, proxima=proxima, **comum)
        (pasta_site / "edicoes" / f"{ed['edicao']}.html").write_text(html, encoding="utf-8")

    index = env.get_template("index.html.j2").render(
        raiz="", pagina="home", atual=edicoes[0] if edicoes else None, edicoes=edicoes, **comum)
    (pasta_site / "index.html").write_text(index, encoding="utf-8")

    glossario = sorted(ler_json(pasta_data / "glossario.json", {}).values(), key=lambda g: chave(g["nome"]))
    html = env.get_template("glossario.html.j2").render(raiz="", pagina="glossario", glossario=glossario, **comum)
    (pasta_site / "glossario.html").write_text(html, encoding="utf-8")

    for estatico in ("estilo.css", "app.js"):
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
