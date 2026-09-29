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
