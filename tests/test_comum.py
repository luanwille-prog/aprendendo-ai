from datetime import date, datetime, timezone

from comum import (chave, data_local, fmt_data, fmt_datahora, fmt_tempo, gravar_json,
                   inicio_do_dia_utc, ler_json, listar_json, slug, titulo_e_palestrante)


def test_data_local_vira_o_dia_em_brasilia():
    # 2026-09-29 02:30 UTC = 2026-09-28 23:30 em Brasília
    ts = datetime(2026, 9, 29, 2, 30, tzinfo=timezone.utc).timestamp()
    assert data_local(ts) == date(2026, 9, 28)


def test_inicio_do_dia_utc():
    assert inicio_do_dia_utc(date(2026, 9, 29)) == datetime(2026, 9, 29, 3, 0, tzinfo=timezone.utc)


def test_fmt_tempo():
    assert fmt_tempo(312) == "05:12"
    assert fmt_tempo(3725) == "1:02:05"
    assert fmt_tempo(None) == "00:00"


def test_fmt_data_e_datahora():
    assert fmt_data("2026-09-28") == "segunda, 28 set 2026"
    assert fmt_datahora("2026-09-29T10:12:00+00:00") == "29 set 2026, 07:12"


def test_json_ida_e_volta(tmp_path):
    p = tmp_path / "a" / "b.json"
    gravar_json(p, {"título": "ação"})
    assert ler_json(p) == {"título": "ação"}
    assert ler_json(tmp_path / "nao.json", {}) == {}


def test_listar_json_ignora_arquivos_ocultos_do_macos(tmp_path):
    gravar_json(tmp_path / "b.json", {})
    gravar_json(tmp_path / "a.json", {})
    (tmp_path / "._a.json").write_bytes(b"\x00\x05\x16\x07")
    (tmp_path / "nota.txt").write_text("x")
    assert [p.name for p in listar_json(tmp_path)] == ["a.json", "b.json"]
    assert listar_json(tmp_path / "nao-existe") == []


def test_titulo_e_palestrante():
    assert titulo_e_palestrante("Get Out of the Model's Way — Kevin Hou, Google Antigravity") == (
        "Get Out of the Model's Way", "Kevin Hou, Google Antigravity")
    assert titulo_e_palestrante("Keynote sem autor") == ("Keynote sem autor", None)


def test_chave_e_slug():
    assert chave("  LLM-as-Judge   ação ") == "llm-as-judge ação"
    assert slug("llm-as-judge ação") == "llm-as-judge-acao"


def test_ffmpeg_cai_para_imageio_quando_nao_esta_no_path(monkeypatch):
    import comum
    import imageio_ffmpeg
    monkeypatch.setattr(comum.shutil, "which", lambda nome: None)
    monkeypatch.setattr(imageio_ffmpeg, "get_ffmpeg_exe", lambda: "/tmp/ffmpeg-estatico")
    assert comum.ffmpeg_bin() == "/tmp/ffmpeg-estatico"
    cmd = comum.ytdlp_base()
    assert cmd[cmd.index("--ffmpeg-location") + 1] == "/tmp/ffmpeg-estatico"


def test_ffmpeg_do_sistema_tem_prioridade(monkeypatch):
    import comum
    monkeypatch.setattr(comum.shutil, "which", lambda nome: "/usr/bin/ffmpeg" if nome == "ffmpeg" else None)
    assert comum.ffmpeg_bin() == "/usr/bin/ffmpeg"
    assert "--ffmpeg-location" not in comum.ytdlp_base()
