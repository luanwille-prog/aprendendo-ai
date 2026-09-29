import shutil
from pathlib import Path

from PIL import Image

import consolidar
from comum import gravar_json, ler_json
from estado import Estado

FIX = Path(__file__).parent / "fixtures" / "video"
VID = "abcdefghijk"


def _pasta(tmp_path, com_curadoria=True):
    pasta = tmp_path / "trab" / VID
    (pasta / "frames").mkdir(parents=True)
    for nome in ("meta.json", "analise.json", "explicacao.json"):
        shutil.copy(FIX / nome, pasta / nome)
    if com_curadoria:
        shutil.copy(FIX / "curadoria.json", pasta / "curadoria.json")
    momentos = []
    for i in range(3):
        frames = []
        for k in range(3):
            Image.new("RGB", (1280, 720), (i * 60, k * 60, 90)).save(pasta / "frames" / f"m{i}_{k}.jpg")
            frames.append(f"frames/m{i}_{k}.jpg")
        momentos.append({"i": i, "t": 0, "fonte": "video", "frames": frames, "erros": []})
    gravar_json(pasta / "frames" / "manifesto.json", {"id": VID, "momentos": momentos})
    return pasta


def test_consolidar_video(tmp_path):
    pasta = _pasta(tmp_path)
    glossario = {}
    v = consolidar.consolidar_video(pasta, "2026-09-28", tmp_path / "data", tmp_path / "site", glossario)
    assert v["url"] == f"https://www.youtube.com/watch?v={VID}"
    assert [i["print"] for i in v["ideias"]] == [f"img/{VID}/0.jpg", None, f"img/{VID}/2.jpg"]
    with Image.open(tmp_path / "site" / "img" / VID / "0.jpg") as im:
        assert im.width <= 960
    eval_, judge = v["conceitos"]
    assert eval_["analogia"] is None and eval_["no_glossario"] is False
    # todo termo entra no glossário, mesmo sem analogia, com as aparições
    assert glossario["eval"]["analogia"] is None and glossario["eval"]["traducao"] == "avaliação"
    assert [a["video_id"] for a in glossario["eval"]["aparicoes"]] == [VID]
    assert judge["analogia"].startswith("Um LLM como juiz")
    assert judge["desenho"]["nos"][0]["rotulo"] == "CRITÉRIOS"
    assert glossario["llm-as-judge"]["video_id"] == VID
    assert glossario["llm-as-judge"]["chave"] == "llm-as-judge"
    assert ler_json(tmp_path / "data" / "videos" / f"{VID}.json") == v


def test_conceito_ja_no_glossario_nao_e_sobrescrito(tmp_path):
    pasta = _pasta(tmp_path)
    glossario = {"eval": {"chave": "eval", "nome": "eval", "analogia": "Uma prova.", "video_id": "outro000001"},
                 "llm-as-judge": {"chave": "llm-as-judge", "nome": "LLM-as-judge", "analogia": "Um juiz.",
                                  "video_id": "outro000001"}}
    v = consolidar.consolidar_video(pasta, "2026-09-28", tmp_path / "data", tmp_path / "site", glossario)
    assert v["conceitos"][0]["no_glossario"] is True  # explicado em outro vídeo
    assert glossario["llm-as-judge"]["video_id"] == "outro000001"
    assert glossario["llm-as-judge"]["analogia"] == "Um juiz."
    assert [a["video_id"] for a in glossario["eval"]["aparicoes"]] == [VID]


def test_termo_basico_ganha_explicacao_depois(tmp_path):
    pasta = _pasta(tmp_path)
    glossario = {"llm-as-judge": {"chave": "llm-as-judge", "nome": "LLM-as-judge", "traducao": "juiz", "analogia": None,
                                  "explicacao": [], "video_id": "outro000001", "video_titulo": "Outro", "edicao": "2026-09-20",
                                  "aparicoes": [{"video_id": "outro000001", "video_titulo": "Outro", "edicao": "2026-09-20"}]}}
    consolidar.consolidar_video(pasta, "2026-09-28", tmp_path / "data", tmp_path / "site", glossario)
    g = glossario["llm-as-judge"]
    assert g["analogia"].startswith("Um LLM como juiz") and g["video_id"] == VID
    assert [a["video_id"] for a in g["aparicoes"]] == ["outro000001", VID]


def test_sem_curadoria_usa_frame_do_meio(tmp_path):
    pasta = _pasta(tmp_path, com_curadoria=False)
    assert consolidar.escolher_frame(pasta, 1, ler_json(pasta / "frames" / "manifesto.json"), None) == \
        pasta / "frames" / "m1_1.jpg"


def test_main_valida_e_grava_publicados(tmp_path):
    dia = tmp_path / "trab"
    _pasta(tmp_path)
    ruim = dia / "ruim0000001"
    ruim.mkdir()
    shutil.copy(FIX / "meta.json", ruim / "meta.json")
    gravar_json(ruim / "analise.json", {"id": "ruim0000001"})
    gravar_json(dia / "fila.json", {"hoje": "2026-09-29", "modo": "diario", "videos": [
        {"id": VID, "titulo": "A", "publicado_ts": 1.0, "edicao": "2026-09-28"},
        {"id": "ruim0000001", "titulo": "Ruim", "publicado_ts": 1.0, "edicao": "2026-09-28"},
    ]})
    gravar_json(dia / "extracao.json", {"ok": [VID, "ruim0000001"], "resultados": []})
    rc = consolidar.main(["--dia", str(dia), "--data", str(tmp_path / "data"), "--site", str(tmp_path / "site")])
    assert rc == 0
    assert ler_json(dia / "publicados.json") == {VID: "2026-09-28"}
    assert "llm-as-judge" in ler_json(tmp_path / "data" / "glossario.json")
    assert Estado(tmp_path / "data").pendentes["ruim0000001"]["ultima_etapa"] == "consolidacao"


def test_imagem_corrompida_nao_derruba_o_video(tmp_path):
    pasta = _pasta(tmp_path)
    (pasta / "frames" / "m0_1.jpg").write_bytes(b"isto nao e uma imagem")
    v = consolidar.consolidar_video(pasta, "2026-09-28", tmp_path / "data", tmp_path / "site", {})
    assert v["ideias"][0]["print"] is None
    assert v["ideias"][2]["print"] == f"img/{VID}/2.jpg"


def test_curadoria_so_aceita_frames_do_manifesto(tmp_path):
    pasta = _pasta(tmp_path)
    curadoria = ler_json(pasta / "curadoria.json")
    curadoria["momentos"][0]["frame"] = "meta.json"  # existe, mas não é frame do manifesto
    manifesto = ler_json(pasta / "frames" / "manifesto.json")
    assert consolidar.escolher_frame(pasta, 0, manifesto, curadoria) == pasta / "frames" / "m0_1.jpg"
