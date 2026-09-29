"""Valida as saídas dos agentes contra os schemas e contra os metadados do vídeo."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from comum import SCHEMAS, ler_json

_validadores: dict[str, Draft202012Validator] = {}


def _validador(nome: str) -> Draft202012Validator:
    if nome not in _validadores:
        _validadores[nome] = Draft202012Validator(ler_json(SCHEMAS / f"{nome}.schema.json"))
    return _validadores[nome]


def validar(dados, nome: str) -> list[str]:
    erros = sorted(_validador(nome).iter_errors(dados), key=lambda e: [str(p) for p in e.absolute_path])
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '(raiz)'}: {e.message}" for e in erros]


def checar_analise(analise: dict, meta: dict) -> list[str]:
    erros = []
    if analise.get("id") != meta["id"]:
        erros.append(f"id: esperado {meta['id']}, veio {analise.get('id')}")
    duracao = meta.get("duracao") or 0
    if not duracao:
        return erros
    for i, ideia in enumerate(analise.get("ideias", [])):
        t = ideia.get("momento", {}).get("t", 0)
        if t > duracao:
            erros.append(f"ideias/{i}/momento/t: {t}s passa da duração {duracao}s")
    for i, numero in enumerate(analise.get("numeros", [])):
        if numero.get("t", 0) > duracao:
            erros.append(f"numeros/{i}/t: {numero['t']}s passa da duração {duracao}s")
    return erros


def erros_de(tipo: str, arquivo: Path, meta: Path | None = None) -> list[str]:
    try:
        dados = ler_json(arquivo)
    except json.JSONDecodeError as e:
        return [f"(raiz): JSON inválido: {e}"]
    if dados is None:
        return [f"(raiz): arquivo não encontrado: {arquivo}"]
    erros = validar(dados, tipo)
    if tipo == "analise" and meta is not None and not erros:
        erros += checar_analise(dados, ler_json(meta))
    return erros


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tipo", choices=["analise", "explicacao", "curadoria", "dia"])
    ap.add_argument("arquivo", type=Path)
    ap.add_argument("--meta", type=Path, default=None)
    a = ap.parse_args(argv)
    erros = erros_de(a.tipo, a.arquivo, a.meta)
    if erros:
        print("\n".join(erros))
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
