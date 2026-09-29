"""Junta análise, explicação e prints de cada vídeo em data/videos/<id>.json e atualiza o glossário."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from comum import DATA, SITE, chave, gravar_json, ler_json
from estado import Estado
from validar import erros_de


def escolher_frame(pasta: Path, i: int, manifesto: dict | None, curadoria: dict | None) -> Path | None:
    candidatos = next((m["frames"] for m in (manifesto or {}).get("momentos", []) if m["i"] == i), [])
    if curadoria:
        for m in curadoria["momentos"]:
            if m["i"] == i:
                if m["frame"] is None:
                    return None
                # só vale um frame que o próprio manifesto listou para este momento
                if m["frame"] in candidatos and (pasta / m["frame"]).exists():
                    return pasta / m["frame"]
    if candidatos:
        return pasta / candidatos[len(candidatos) // 2]
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
            try:
                salvar_imagem(frame, Path(pasta_site) / f"img/{vid}/{i}.jpg")
                caminho_print = f"img/{vid}/{i}.jpg"
            except Exception as e:
                print(f"{vid}: frame {frame.name} ilegível ({e}), ideia {i} sai sem print")
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
