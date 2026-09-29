from datetime import date, datetime, timezone
from pathlib import Path

import detectar
from comum import ler_json
from estado import MAX_TENTATIVAS, Estado

FIXTURE = Path(__file__).parent / "fixtures" / "rss.xml"
HOJE = date(2026, 9, 29)


def candidatos():
    return detectar.parse_rss(FIXTURE.read_text(encoding="utf-8"))


def test_parse_rss_decodifica_e_marca_shorts():
    vs = candidatos()
    assert [v["id"] for v in vs] == ["hoje0000001", "ontem000001", "short000001", "antigo00001"]
    assert vs[1]["titulo"] == "Evals & Agents — Ana, Weights & Biases"
    assert vs[2]["short"] is True
    assert vs[1]["short"] is False
    assert vs[1]["publicado_ts"] == datetime(2026, 9, 29, 2, 30, tzinfo=timezone.utc).timestamp()


def test_selecionar_diario_pega_ontem_mesmo_depois_da_meia_noite_utc(tmp_path):
    e = Estado(tmp_path)
    e.definir_inicio(date(2026, 9, 22))
    fila, ignorados = detectar.selecionar(candidatos(), e, HOJE, backfill=False)
    assert [v["id"] for v in fila] == ["ontem000001"]
    assert fila[0]["edicao"] == "2026-09-28"
    assert [v["id"] for v in ignorados] == ["short000001"]


def test_selecionar_pula_processados_e_abandonados(tmp_path):
    e = Estado(tmp_path)
    e.marcar_processado("ontem000001", "2026-09-28")
    fila, _ = detectar.selecionar(candidatos(), e, HOJE, backfill=False)
    assert "ontem000001" not in [v["id"] for v in fila]
    e2 = Estado(tmp_path / "b")
    for _ in range(MAX_TENTATIVAS):
        e2.registrar_falha("ontem000001", "T", 0, "extracao", "x")
    fila2, _ = detectar.selecionar(candidatos(), e2, HOJE, backfill=False)
    assert "ontem000001" not in [v["id"] for v in fila2]


def test_selecionar_inclui_pendente_fora_do_rss(tmp_path):
    e = Estado(tmp_path)
    ts = datetime(2026, 9, 26, 15, 0, tzinfo=timezone.utc).timestamp()
    e.registrar_falha("pendente001", "Pendente — X, Y", ts, "extracao", "bloqueio")
    fila, _ = detectar.selecionar(candidatos(), e, HOJE, backfill=False)
    pend = [v for v in fila if v["id"] == "pendente001"][0]
    assert pend["edicao"] == "2026-09-28"
    assert pend["titulo"] == "Pendente — X, Y"


def test_selecionar_backfill_agrupa_pela_data_de_publicacao(tmp_path):
    e = Estado(tmp_path)
    e.definir_inicio(date(2026, 9, 22))
    fila, _ = detectar.selecionar(candidatos(), e, HOJE, backfill=True)
    assert [(v["id"], v["edicao"]) for v in fila] == [("ontem000001", "2026-09-28")]


def test_parse_listagem():
    saida = ("aaaaaaaaaaa\t1790533807\thttps://www.youtube.com/watch?v=aaaaaaaaaaa\tTítulo A — P, E\n"
             "bbbbbbbbbbb\tNA\thttps://www.youtube.com/shorts/bbbbbbbbbbb\tShort\n"
             "linha quebrada\n")
    vs = detectar.parse_listagem(saida)
    assert vs == [{"id": "aaaaaaaaaaa", "titulo": "Título A — P, E", "publicado_ts": 1790533807.0, "short": False}]


def test_main_diario_grava_fila_e_ignora_short(tmp_path, monkeypatch):
    monkeypatch.setattr(detectar, "baixar_rss", lambda: FIXTURE.read_text(encoding="utf-8"))
    rc = detectar.main(["--hoje", "2026-09-29", "--data", str(tmp_path / "data"),
                        "--trabalho", str(tmp_path / "trab")])
    assert rc == 0
    fila = ler_json(tmp_path / "trab" / "2026-09-29" / "fila.json")
    assert fila["modo"] == "diario"
    assert [v["id"] for v in fila["videos"]] == ["ontem000001"]
    e = Estado(tmp_path / "data")
    assert e.processados["short000001"]["ignorado"] == "short"
    assert e.inicio == date(2026, 9, 28)
