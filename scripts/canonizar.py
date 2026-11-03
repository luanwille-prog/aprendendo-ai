"""Junta termos duplicados do glossário (Skill/Skills, LLM judge/LLM-as-a-judge…) usando data/aliases.json.

Funde as aparições na entrada canônica, apaga a duplicata e troca a chave nos conceitos de data/videos.
É idempotente: rodar de novo não muda nada.
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

from comum import DATA, chave, gravar_json, ler_json, listar_json


def ler_aliases(pasta_data: Path) -> dict[str, str]:
    return {chave(a): chave(c) for a, c in (ler_json(Path(pasta_data) / "aliases.json", {}) or {}).items()}


def _solta(k: str) -> str:
    """Forma frouxa de uma chave: sem acento, pontuação, artigos e plural simples."""
    k = unicodedata.normalize("NFKD", k).encode("ascii", "ignore").decode().lower()
    k = re.sub(r"\(.*?\)", "", k)
    palavras = [p for p in re.sub(r"[^a-z0-9]+", " ", k).split() if p not in {"a", "as", "an", "the", "de", "do", "da"}]
    return " ".join(p[:-1] if len(p) > 3 and p.endswith("s") and not p.endswith("ss") else p for p in palavras)


class Resolvedor:
    """Acha a entrada do glossário para um nome escrito livremente (pré-requisito, conceito novo)."""

    def __init__(self, glossario: dict, aliases: dict[str, str]):
        self.glossario, self.aliases = glossario, aliases
        self.soltas = {}
        for k in glossario:
            self.soltas.setdefault(_solta(k), k)

    def __call__(self, nome: str) -> str | None:
        k = chave(nome)
        k = self.aliases.get(k, k)
        if k in self.glossario:
            return k
        return self.soltas.get(_solta(k))


def canonizar(pasta_data: Path) -> dict:
    pasta_data = Path(pasta_data)
    aliases = ler_aliases(pasta_data)
    glossario = ler_json(pasta_data / "glossario.json", {})
    fundidos = {}
    for alias, canon in aliases.items():
        if alias not in glossario or alias == canon:
            continue
        velho = glossario.pop(alias)
        if canon not in glossario:
            glossario[canon] = {**velho, "chave": canon}
            fundidos[alias] = canon
            continue
        novo = glossario[canon]
        vistos = {a["video_id"] for a in novo.get("aparicoes", [])}
        novo.setdefault("aparicoes", []).extend(a for a in velho.get("aparicoes", []) if a["video_id"] not in vistos)
        if not novo.get("analogia") and velho.get("analogia"):
            novo.update(analogia=velho["analogia"], explicacao=velho.get("explicacao", []))
        fundidos[alias] = canon
    gravar_json(pasta_data / "glossario.json", glossario)

    videos_mudados = 0
    for arq in listar_json(pasta_data / "videos"):
        v = ler_json(arq)
        mudou, vistos, conceitos = False, set(), []
        for c in v["conceitos"]:
            k = aliases.get(c["chave"], c["chave"])
            if k != c["chave"]:
                c["chave"], mudou = k, True
            if k in vistos:  # o mesmo conceito com dois nomes no mesmo talk
                mudou = True
                continue
            vistos.add(k)
            conceitos.append(c)
        if mudou:
            v["conceitos"] = conceitos
            gravar_json(arq, v)
            videos_mudados += 1
    return {"fundidos": fundidos, "videos": videos_mudados}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--listar", action="store_true", help="só imprime 'nome | tradução' de cada termo, para o analista")
    a = ap.parse_args(argv)
    if a.listar:
        for g in sorted(ler_json(a.data / "glossario.json", {}).values(), key=lambda g: g["chave"]):
            print(f"{g['nome']} | {g.get('traducao') or ''}")
        return 0
    r = canonizar(a.data)
    print(f"{len(r['fundidos'])} termo(s) fundido(s), {r['videos']} vídeo(s) atualizado(s)")
    for alias, canon in r["fundidos"].items():
        print(f"  {alias} -> {canon}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
