"""Enriquecimento retroativo: aplica em data/ o que foi gerado depois da publicação.

Fontes (todas em trabalho/backfill/, validadas antes de gravar):
- didatica/lote-*.json: rotulo, objetivo, perguntas e experimento de cada vídeo (schemas/didatica.schema.json);
- essenciais.json: os 2 ou 3 talks essenciais de cada edição (vai para data/dias/<edicao>.json);
- glossario/saida-*.json: analogias para os termos mais citados e termos de base que faltavam.

Com --prints, também copia a nota do curador (descrição do que o print mostra) para o alt das imagens
e regrava os prints a 1280 px a partir dos frames originais em trabalho/<dia>/<id>/frames.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from comum import DATA, SITE, TRABALHO, chave, gravar_json, ler_json, listar_json
from consolidar import escolher_frame, salvar_imagem
from validar import validar

CAMPOS_DIDATICOS = ("rotulo", "objetivo", "perguntas", "experimento")


def aplicar_didatica(pasta_backfill: Path, pasta_data: Path) -> tuple[int, list[str]]:
    aplicados, erros = 0, []
    for arq in sorted((pasta_backfill / "didatica").glob("lote-*.json")):
        for item in ler_json(arq)["videos"]:
            e = validar(item, "didatica")
            destino = pasta_data / "videos" / f"{item.get('id')}.json"
            if e or not destino.exists():
                erros.append(f"{arq.name} {item.get('id')}: {e or 'vídeo inexistente'}")
                continue
            v = ler_json(destino)
            v.update({k: item[k] for k in CAMPOS_DIDATICOS})
            gravar_json(destino, v)
            aplicados += 1
    return aplicados, erros


def aplicar_essenciais(pasta_backfill: Path, pasta_data: Path) -> tuple[int, list[str]]:
    escolhas = ler_json(pasta_backfill / "essenciais.json", {})
    aplicados, erros = 0, []
    for edicao, itens in escolhas.items():
        arq = pasta_data / "dias" / f"{edicao}.json"
        if not arq.exists():
            erros.append(f"{edicao}: sem data/dias")
            continue
        dia = ler_json(arq)
        novo = {**dia, "essenciais": [{"id": i["id"], "por_que": i["por_que"]} for i in itens if i["id"] in dia["ordem"]]}
        e = validar(novo, "dia")
        if e:
            erros.append(f"{edicao}: {e}")
            continue
        gravar_json(arq, novo)
        aplicados += 1
    return aplicados, erros


def aplicar_glossario(pasta_backfill: Path, pasta_data: Path) -> tuple[int, list[str]]:
    glossario = ler_json(pasta_data / "glossario.json", {})
    aplicados, erros = 0, []
    for arq in sorted((pasta_backfill / "glossario").glob("saida-*.json")):
        for t in ler_json(arq)["termos"]:
            item = {k: t.get(k) for k in ("nome", "analogia", "explicacao", "pre_requisitos", "desenho")}
            e = validar({"id": "x" * 11, "conceitos": [item]}, "explicacao")
            if e or len(t.get("traducao") or "") > 80:
                erros.append(f"{arq.name} {t.get('chave')}: {e or 'tradução longa'}")
                continue
            k = chave(t["chave"])
            entrada = glossario.get(k)
            if entrada is None:  # termo de base: entra sem aparição própria
                entrada = glossario[k] = {"chave": k, "nome": t["nome"], "traducao": t.get("traducao"), "base": True,
                                          "video_id": None, "video_titulo": None, "edicao": None, "aparicoes": []}
            if entrada.get("analogia"):
                continue  # nunca sobrescreve uma analogia que já veio de um talk
            entrada.update(analogia=t["analogia"], explicacao=t["explicacao"], pre_requisitos=t["pre_requisitos"],
                           desenho=t.get("desenho"))
            if t.get("traducao") and not entrada.get("traducao"):
                entrada["traducao"] = t["traducao"]
            aplicados += 1
    gravar_json(pasta_data / "glossario.json", glossario)
    return aplicados, erros


def _pasta_trabalho(vid: str, pasta_trabalho: Path) -> Path | None:
    """A pasta mais recente em trabalho/<dia>/<id> que chegou a ter análise (a que foi publicada)."""
    candidatas = sorted(p for p in pasta_trabalho.glob(f"*/{vid}") if (p / "analise.json").exists())
    return candidatas[-1] if candidatas else None


def aplicar_prints(pasta_data: Path, pasta_site: Path, pasta_trabalho: Path) -> tuple[int, int, list[str]]:
    descricoes = regravados = 0
    erros = []
    for arq in listar_json(pasta_data / "videos"):
        v = ler_json(arq)
        pasta = _pasta_trabalho(v["id"], pasta_trabalho)
        if pasta is None:
            continue
        curadoria = ler_json(pasta / "curadoria.json")
        manifesto = ler_json(pasta / "frames" / "manifesto.json")
        notas = {m["i"]: m.get("nota") for m in (curadoria or {}).get("momentos", [])}
        mudou = False
        for i, ideia in enumerate(v["ideias"]):
            if not ideia.get("print"):
                continue
            if notas.get(i) and ideia.get("descricao") != notas[i]:
                ideia["descricao"] = notas[i]
                descricoes += 1
                mudou = True
            frame = escolher_frame(pasta, i, manifesto, curadoria)
            if frame is not None and frame.exists():
                try:
                    salvar_imagem(frame, pasta_site / ideia["print"])
                    regravados += 1
                except Exception as e:  # frame ilegível: mantém o print antigo
                    erros.append(f"{v['id']} ideia {i}: {e}")
        if mudou:
            gravar_json(arq, v)
    return descricoes, regravados, erros


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backfill", type=Path, default=TRABALHO / "backfill")
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--site", type=Path, default=SITE)
    ap.add_argument("--prints", action="store_true", help="também descreve e regrava os prints a partir de trabalho/")
    a = ap.parse_args(argv)
    falhas = []
    n, e = aplicar_didatica(a.backfill, a.data); falhas += e
    print(f"didática: {n} vídeo(s)")
    n, e = aplicar_essenciais(a.backfill, a.data); falhas += e
    print(f"essenciais: {n} edição(ões)")
    n, e = aplicar_glossario(a.backfill, a.data); falhas += e
    print(f"glossário: {n} termo(s) explicado(s)")
    if a.prints:
        d, r, e = aplicar_prints(a.data, a.site, TRABALHO); falhas += e
        print(f"prints: {d} descrição(ões), {r} imagem(ns) regravada(s)")
    for f in falhas:
        print("  erro:", f)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
