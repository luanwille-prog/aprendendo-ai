import extrair
from comum import ler_json, gravar_json
from estado import Estado

VID = "abcdefghijk"
INFO = {
    "id": VID,
    "title": "Scale the Judgment, Not the Model — Andrew Orobator, Reddit",
    "description": "Descrição do talk",
    "duration": 900,
    "timestamp": 1790524817,
    "live_status": "not_live",
    "chapters": [{"start_time": 0.0, "title": "Intro", "end_time": 25.0}],
    "formats": [
        {"format_id": "sb0", "width": 320, "height": 180, "rows": 3, "columns": 3, "fps": 0.2,
         "fragments": [{"url": "https://i.ytimg.com/sb/x/M0.jpg", "duration": 45.0}]},
        {"format_id": "137"},
    ],
    "automatic_captions": {
        "en-orig": [{"ext": "vtt", "url": "u-vtt"}, {"ext": "json3", "url": "u-orig"}],
        "en": [{"ext": "json3", "url": "u-en"}],
    },
    "subtitles": {},
}
JSON3 = {"events": [
    {"tStartMs": 0, "dDurationMs": 900000, "id": 1},
    {"tStartMs": 1000, "segs": [{"utf8": "Hello"}, {"utf8": " everyone"}]},
    {"tStartMs": 3000, "aAppend": 1, "segs": [{"utf8": "\n"}]},
    {"tStartMs": 40000, "segs": [{"utf8": "Evals matter."}]},
]}
APIFY = {"status": "success", "video_id": VID, "title": INFO["title"], "description": "d",
         "duration_seconds": 900, "published_at": "2026-09-27T16:00:17Z",
         "transcript": [{"start": 1.0, "end": 3.0, "duration": 2.0, "text": "Hello everyone"},
                        {"start": 40.0, "end": 42.0, "duration": 2.0, "text": " "}]}


def test_meta_de_info():
    m = extrair.meta_de_info(INFO)
    assert m["titulo_curto"] == "Scale the Judgment, Not the Model"
    assert m["palestrante"] == "Andrew Orobator, Reddit"
    assert m["capitulos"] == [{"t": 0, "titulo": "Intro"}]
    assert m["storyboard"]["colunas"] == 3
    assert m["storyboard"]["fragmentos"][0]["duracao"] == 45.0
    assert m["duracao"] == 900


def test_meta_de_apify():
    m = extrair.meta_de_apify(APIFY)
    assert m["id"] == VID and m["storyboard"] is None and m["capitulos"] == []
    assert m["publicado_ts"] == 1790524817.0


def test_escolher_legenda_prefere_manual_depois_en_orig():
    assert extrair.escolher_legenda(INFO) == "u-orig"
    com_manual = {**INFO, "subtitles": {"en": [{"ext": "json3", "url": "u-manual"}]}}
    assert extrair.escolher_legenda(com_manual) == "u-manual"
    so_en = {**INFO, "automatic_captions": {"en": [{"ext": "json3", "url": "u-en"}]}}
    assert extrair.escolher_legenda(so_en) == "u-en"
    assert extrair.escolher_legenda({**INFO, "automatic_captions": {}}) is None


def test_segmentos_e_formatacao():
    segs = extrair.segmentos_json3(JSON3)
    assert segs == [(1.0, "Hello everyone"), (40.0, "Evals matter.")]
    assert extrair.segmentos_apify(APIFY) == [(1.0, "Hello everyone")]
    texto = extrair.formatar_transcricao([(0, "a"), (10, "b"), (31, "c"), (65, "d")])
    assert texto == "[t=0] a b\n[t=31] c\n[t=65] d\n"


def _falha(*_a, **_k):
    raise RuntimeError("bloqueado")


def test_extrair_ok_via_json3(tmp_path, monkeypatch):
    monkeypatch.setattr(extrair, "obter_info", lambda vid: INFO)
    monkeypatch.setattr(extrair, "baixar_json3", lambda url: JSON3)
    r = extrair.extrair_video(VID, tmp_path / VID, token=None)
    assert r == {"id": VID, "status": "ok"}
    assert ler_json(tmp_path / VID / "meta.json")["titulo_curto"] == "Scale the Judgment, Not the Model"
    assert (tmp_path / VID / "transcricao.txt").read_text().startswith("[t=1] Hello everyone")


def test_extrair_cai_para_apify_quando_json3_falha(tmp_path, monkeypatch):
    monkeypatch.setattr(extrair, "obter_info", lambda vid: INFO)
    monkeypatch.setattr(extrair, "baixar_json3", _falha)
    monkeypatch.setattr(extrair, "transcricao_apify", lambda vid, token: APIFY)
    assert extrair.extrair_video(VID, tmp_path / VID, token="t")["status"] == "ok"


def test_extrair_sem_ytdlp_usa_meta_da_apify(tmp_path, monkeypatch):
    monkeypatch.setattr(extrair, "obter_info", _falha)
    monkeypatch.setattr(extrair, "transcricao_apify", lambda vid, token: APIFY)
    assert extrair.extrair_video(VID, tmp_path / VID, token="t")["status"] == "ok"
    assert ler_json(tmp_path / VID / "meta.json")["storyboard"] is None


def test_extrair_falha_quando_tudo_falha(tmp_path, monkeypatch):
    monkeypatch.setattr(extrair, "obter_info", lambda vid: INFO)
    monkeypatch.setattr(extrair, "baixar_json3", _falha)
    monkeypatch.setattr(extrair, "transcricao_apify", _falha)
    r = extrair.extrair_video(VID, tmp_path / VID, token="t")
    assert r["status"] == "falha" and "json3" in r["erro"] and "apify" in r["erro"]


def test_premiere_adiada_e_curto_ignorado(tmp_path, monkeypatch):
    monkeypatch.setattr(extrair, "obter_info", lambda vid: {**INFO, "live_status": "is_upcoming"})
    assert extrair.extrair_video(VID, tmp_path / VID, None)["status"] == "adiado"
    monkeypatch.setattr(extrair, "obter_info", lambda vid: {**INFO, "duration": 50})
    assert extrair.extrair_video(VID, tmp_path / VID, None) == {"id": VID, "status": "ignorado", "motivo": "curto"}


def test_main_registra_estado(tmp_path, monkeypatch):
    dia = tmp_path / "trab" / "2026-09-29"
    gravar_json(dia / "fila.json", {"hoje": "2026-09-29", "modo": "diario", "videos": [
        {"id": VID, "titulo": "A", "publicado_ts": 1.0, "edicao": "2026-09-28"},
        {"id": "curto000001", "titulo": "B", "publicado_ts": 1.0, "edicao": "2026-09-28"},
        {"id": "quebrado001", "titulo": "C", "publicado_ts": 1.0, "edicao": "2026-09-28"},
    ]})

    def falso(vid, pasta, token):
        if vid == VID:
            return {"id": vid, "status": "ok"}
        if vid == "curto000001":
            return {"id": vid, "status": "ignorado", "motivo": "curto"}
        raise ValueError("inesperado")

    monkeypatch.setattr(extrair, "extrair_video", falso)
    assert extrair.main(["--fila", str(dia / "fila.json"), "--data", str(tmp_path / "data")]) == 0
    assert ler_json(dia / "extracao.json")["ok"] == [VID]
    e = Estado(tmp_path / "data")
    assert e.processados["curto000001"]["ignorado"] == "curto"
    assert e.pendentes["quebrado001"]["tentativas"] == 1


def test_premiere_que_faz_ytdlp_falhar_e_adiada_sem_gastar_tentativa(tmp_path, monkeypatch):
    def premiere(vid):
        raise RuntimeError("ERROR: [youtube] abcdefghijk: Premieres in 3 days")
    chamou_apify = []
    monkeypatch.setattr(extrair, "obter_info", premiere)
    monkeypatch.setattr(extrair, "transcricao_apify", lambda vid, token: chamou_apify.append(vid))
    assert extrair.extrair_video(VID, tmp_path / VID, token="t") == {"id": VID, "status": "adiado", "motivo": "is_upcoming"}
    assert chamou_apify == []
    monkeypatch.setattr(extrair, "obter_info", lambda vid: (_ for _ in ()).throw(RuntimeError("This live event will begin in a few moments")))
    assert extrair.extrair_video(VID, tmp_path / VID, token=None)["status"] == "adiado"


def test_obter_info_ignora_erro_de_formatos(monkeypatch):
    capturado = {}

    class R:
        returncode, stdout, stderr = 0, '{"id": "x"}', ""

    def falso_run(cmd, **kw):
        capturado["cmd"] = cmd
        return R()

    monkeypatch.setattr(extrair.subprocess, "run", falso_run)
    extrair.obter_info("abcdefghijk")
    assert "--ignore-no-formats-error" in capturado["cmd"]
