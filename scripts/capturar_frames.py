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
