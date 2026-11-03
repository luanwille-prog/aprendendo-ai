import copy
from pathlib import Path

import validar
from comum import gravar_json, ler_json

FIX = Path(__file__).parent / "fixtures" / "video"
ANALISE = ler_json(FIX / "analise.json")
META = ler_json(FIX / "meta.json")


def test_fixtures_validas():
    assert validar.validar(ANALISE, "analise") == []
    assert validar.validar(ler_json(FIX / "explicacao.json"), "explicacao") == []
    assert validar.validar(ler_json(FIX / "curadoria.json"), "curadoria") == []
    assert validar.checar_analise(ANALISE, META) == []


def test_campo_faltando_e_tema_invalido():
    ruim = copy.deepcopy(ANALISE)
    del ruim["leitura_critica"]
    ruim["tema"] = "marketing"
    erros = validar.validar(ruim, "analise")
    assert any("leitura_critica" in e for e in erros)
    assert any(e.startswith("tema:") for e in erros)


def test_minuto_alem_da_duracao_e_id_trocado():
    ruim = copy.deepcopy(ANALISE)
    ruim["ideias"][1]["momento"]["t"] = 1200
    ruim["numeros"][0]["t"] = 999
    ruim["id"] = "zzzzzzzzzzz"
    erros = validar.checar_analise(ruim, META)
    assert "ideias/1/momento/t: 1200s passa da duração 900s" in erros
    assert "numeros/0/t: 999s passa da duração 900s" in erros
    assert any(e.startswith("id:") for e in erros)


def test_dia():
    ok = {"edicao": "2026-09-28", "titulo": "O dia dos juízes", "abertura": "a" * 50,
          "ordem": ["abcdefghijk"], "conceitos_novos": ["LLM-as-judge"],
          "essenciais": [{"id": "abcdefghijk", "por_que": "Ensina o mecanismo central do dia."}]}
    assert validar.validar(ok, "dia") == []
    assert validar.validar({**ok, "edicao": "28/09/2026"}, "dia") != []
    sem_essenciais = {k: v for k, v in ok.items() if k != "essenciais"}
    assert any("essenciais" in e for e in validar.validar(sem_essenciais, "dia"))
    dialogo = {"id": "abcdefghijk", "com": "zyxwvutsrqp", "relacao": "contradiz", "nota": "Discorda sobre o tamanho do juiz."}
    assert validar.validar({**ok, "dialogos": [dialogo]}, "dia") == []


def test_didatica():
    from test_validar import ANALISE as a
    ok = {"id": a["id"], **{k: a[k] for k in ("rotulo", "objetivo", "perguntas", "experimento")}}
    assert validar.validar(ok, "didatica") == []
    assert validar.validar({**ok, "experimento": None}, "didatica") == []
    duas = {**ok, "perguntas": ok["perguntas"][:2]}
    assert validar.validar(duas, "didatica") != []


def test_cli(tmp_path, capsys):
    arq = tmp_path / "analise.json"
    gravar_json(arq, ANALISE)
    assert validar.main(["analise", str(arq), "--meta", str(FIX / "meta.json")]) == 0
    assert capsys.readouterr().out.strip() == "ok"
    gravar_json(arq, {**ANALISE, "tldr": ["curta"]})
    assert validar.main(["analise", str(arq)]) == 1
    assert validar.main(["analise", str(tmp_path / "nao-existe.json")]) == 1
