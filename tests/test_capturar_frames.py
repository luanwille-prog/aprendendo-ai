import shutil
from pathlib import Path

from PIL import Image

import capturar_frames as cf
from comum import gravar_json, ler_json

FIX = Path(__file__).parent / "fixtures" / "video"
SB = {"largura": 320, "altura": 180, "linhas": 3, "colunas": 3, "fps": 0.2026,
      "fragmentos": [{"url": f"https://sb/M{i}.jpg", "duracao": 44.4} for i in range(18)]}


def test_posicao_storyboard():
    assert cf.posicao_storyboard(SB, 0) == ("https://sb/M0.jpg", (0, 0, 320, 180))
    # t=50 -> quadro 10 -> folha 1, posição 1
    assert cf.posicao_storyboard(SB, 50) == ("https://sb/M1.jpg", (320, 0, 640, 180))
    # além do fim: último quadro da última folha
    assert cf.posicao_storyboard(SB, 10000) == ("https://sb/M17.jpg", (640, 360, 960, 540))


def _pasta(tmp_path, storyboard=None):
    pasta = tmp_path / "abcdefghijk"
    pasta.mkdir()
    shutil.copy(FIX / "analise.json", pasta / "analise.json")
    meta = ler_json(FIX / "meta.json")
    meta["storyboard"] = storyboard
    gravar_json(pasta / "meta.json", meta)
    return pasta


def _gera(n):
    def fn(*args):
        prefixo = args[-1]
        saida = []
        for k in range(n):
            p = prefixo.with_name(f"{prefixo.name}_{k}.jpg")
            Image.new("RGB", (64, 36)).save(p)
            saida.append(p)
        return saida
    return fn


def _falha(*_a):
    raise RuntimeError("bloqueado")


def test_video_ok(tmp_path):
    pasta = _pasta(tmp_path)
    m = cf.capturar_momentos(pasta, video_fn=_gera(3), storyboard_fn=_falha, thumb_fn=_falha)
    assert [x["fonte"] for x in m["momentos"]] == ["video"] * 3
    assert m["momentos"][0]["frames"] == ["frames/m0_0.jpg", "frames/m0_1.jpg", "frames/m0_2.jpg"]
    assert ler_json(pasta / "frames" / "manifesto.json") == m


def test_cai_para_storyboard(tmp_path):
    pasta = _pasta(tmp_path, storyboard=SB)
    m = cf.capturar_momentos(pasta, video_fn=_falha, storyboard_fn=_gera(3), thumb_fn=_falha)
    assert m["momentos"][1]["fonte"] == "storyboard"
    assert "video: bloqueado" in m["momentos"][1]["erros"]


def test_thumbnail_so_uma_vez_e_bloco_sem_imagem(tmp_path):
    pasta = _pasta(tmp_path, storyboard=None)
    m = cf.capturar_momentos(pasta, video_fn=_falha, storyboard_fn=_falha, thumb_fn=_gera(1))
    assert [x["fonte"] for x in m["momentos"]] == ["thumbnail", None, None]
    assert m["momentos"][1]["frames"] == []


def test_nada_funciona(tmp_path):
    pasta = _pasta(tmp_path, storyboard=SB)
    m = cf.capturar_momentos(pasta, video_fn=_falha, storyboard_fn=_falha, thumb_fn=_falha)
    assert all(x["fonte"] is None and x["frames"] == [] for x in m["momentos"])
