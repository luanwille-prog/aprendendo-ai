"""Extrai metadados e transcrição de cada vídeo da fila (yt-dlp primeiro, Apify como plano B)."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from comum import DATA, gravar_json, ler_json, titulo_e_palestrante, ytdlp_base
from estado import Estado

DURACAO_MINIMA = 180
APIFY_ACTOR = "starvibe~youtube-video-transcript"
# mensagens do yt-dlp para premieres e lives que ainda não começaram
AINDA_NAO_COMECOU = re.compile(r"premieres? in|live event will begin|will begin in|scheduled to start", re.I)


def obter_info(vid: str) -> dict:
    cmd = [*ytdlp_base(), "-J", "--skip-download", "--ignore-no-formats-error", f"https://www.youtube.com/watch?v={vid}"]
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
    headers = {"Content-Type": "application/json"}
    if token:  # sem token na sessão, o proxy da nuvem injeta a credencial do ambiente
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=corpo, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=180) as r:
        itens = json.load(r)
    if not itens or itens[0].get("status") != "success":
        motivo = itens[0].get("message") if itens else "resposta vazia"
        raise RuntimeError(f"sem transcrição ({motivo})")
    return itens[0]


def extrair_video(vid: str, pasta: Path, token: str | None) -> dict:
    """token None desliga a Apify; "" tenta a Apify sem header (a credencial vem do proxy da nuvem)."""
    pasta = Path(pasta)
    item_apify, info = None, None
    try:
        info = obter_info(vid)
        meta = meta_de_info(info)
    except Exception as erro_info:
        if AINDA_NAO_COMECOU.search(str(erro_info)):
            return {"id": vid, "status": "adiado", "motivo": "is_upcoming"}
        if token is None:
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
    if not segs and token is not None:
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
    # "" = tenta a Apify sem header (credencial do ambiente injetada pelo proxy); None desliga a Apify
    token = os.environ.get("APIFY_TOKEN", "")

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
