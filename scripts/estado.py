"""Registro de vídeos processados e pendentes, configuração e última execução."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from pathlib import Path

from comum import DATA, gravar_json, hoje_local, ler_json

MAX_TENTATIVAS = 3


def _agora() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


class Estado:
    def __init__(self, pasta: Path = DATA):
        self.pasta = Path(pasta)
        self.processados: dict = ler_json(self.pasta / "processados.json", {})
        self.pendentes: dict = ler_json(self.pasta / "pendentes.json", {})
        self.config: dict = ler_json(self.pasta / "config.json", {})
        self.execucao: dict = ler_json(self.pasta / "execucao.json", {})

    def salvar(self) -> None:
        gravar_json(self.pasta / "processados.json", self.processados)
        gravar_json(self.pasta / "pendentes.json", self.pendentes)
        gravar_json(self.pasta / "config.json", self.config)
        gravar_json(self.pasta / "execucao.json", self.execucao)

    @property
    def inicio(self) -> date | None:
        valor = self.config.get("inicio")
        return date.fromisoformat(valor) if valor else None

    def definir_inicio(self, d: date) -> None:
        if self.inicio is None or d < self.inicio:
            self.config["inicio"] = d.isoformat()

    @property
    def backfill_concluido(self) -> bool:
        return bool(self.config.get("backfill_concluido"))

    def concluir_backfill(self) -> None:
        self.config["backfill_concluido"] = True

    def elegivel(self, vid: str) -> bool:
        return vid not in self.processados and vid not in self.abandonados()

    def marcar_processado(self, vid: str, edicao: str, ignorado: str | None = None) -> None:
        registro = {"edicao": edicao, "em": _agora()}
        if ignorado:
            registro["ignorado"] = ignorado
        self.processados[vid] = registro
        self.pendentes.pop(vid, None)

    def registrar_falha(self, vid: str, titulo: str, publicado_ts: float, etapa: str, erro: str) -> None:
        p = self.pendentes.setdefault(vid, {"titulo": titulo, "publicado_ts": publicado_ts, "tentativas": 0})
        p["tentativas"] += 1
        p.update(ultima_etapa=etapa, ultimo_erro=str(erro)[:300], em=_agora())

    def pendentes_ativos(self) -> list[str]:
        return [v for v, p in self.pendentes.items() if p["tentativas"] < MAX_TENTATIVAS]

    def abandonados(self) -> dict:
        return {v: p for v, p in self.pendentes.items() if p["tentativas"] >= MAX_TENTATIVAS}

    def registrar_execucao(self, videos: int) -> None:
        self.execucao = {"em": _agora(), "videos": videos}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=DATA)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("processado", help="marca como publicados os vídeos de publicados.json")
    p.add_argument("--arquivo", type=Path, required=True)
    f = sub.add_parser("falha", help="registra uma tentativa que falhou")
    f.add_argument("--pasta", type=Path, help="pasta do vídeo: lê meta.json e erros.txt e tira a análise das próximas etapas")
    f.add_argument("--id")
    f.add_argument("--titulo")
    f.add_argument("--publicado-ts", type=float)
    f.add_argument("--etapa", required=True)
    f.add_argument("--erro", default="")
    x = sub.add_parser("execucao", help="registra a execução para o rodapé")
    x.add_argument("--videos", type=int, required=True)
    sub.add_parser("modo", help="imprime backfill ou diario")
    sub.add_parser("hoje", help="imprime a data de hoje em Brasília")
    sub.add_parser("backfill-concluido", help="liga a flag de backfill concluído")
    a = ap.parse_args(argv)

    if a.cmd == "hoje":
        print(hoje_local().isoformat())
        return 0
    e = Estado(a.data)
    if a.cmd == "modo":
        print("diario" if e.backfill_concluido else "backfill")
        return 0
    if a.cmd == "processado":
        for vid, edicao in ler_json(a.arquivo, {}).items():
            e.marcar_processado(vid, edicao)
    elif a.cmd == "falha":
        if a.pasta:
            meta = ler_json(a.pasta / "meta.json")
            erros = a.pasta / "erros.txt"
            erro = a.erro or (erros.read_text(encoding="utf-8") if erros.exists() else "sem detalhe")
            e.registrar_falha(meta["id"], meta["titulo"], meta["publicado_ts"], a.etapa, erro)
            analise = a.pasta / "analise.json"
            if analise.exists():
                analise.rename(a.pasta / "analise.invalido.json")
        elif a.id and a.titulo and a.publicado_ts is not None:
            e.registrar_falha(a.id, a.titulo, a.publicado_ts, a.etapa, a.erro or "sem detalhe")
        else:
            ap.error("falha: use --pasta, ou --id, --titulo e --publicado-ts")
    elif a.cmd == "execucao":
        e.registrar_execucao(a.videos)
    elif a.cmd == "backfill-concluido":
        e.concluir_backfill()
    e.salvar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
