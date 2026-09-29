from datetime import date

from comum import gravar_json
import estado as mod
from estado import MAX_TENTATIVAS, Estado


def test_estado_vazio(tmp_path):
    e = Estado(tmp_path)
    assert e.elegivel("abcdefghijk")
    assert e.inicio is None
    assert e.backfill_concluido is False


def test_marcar_processado_remove_de_pendentes(tmp_path):
    e = Estado(tmp_path)
    e.registrar_falha("abcdefghijk", "Título", 1790000000, "extracao", "sem legenda")
    e.marcar_processado("abcdefghijk", "2026-09-28")
    e.salvar()
    e2 = Estado(tmp_path)
    assert not e2.elegivel("abcdefghijk")
    assert "abcdefghijk" not in e2.pendentes
    assert e2.processados["abcdefghijk"]["edicao"] == "2026-09-28"


def test_tres_falhas_abandonam(tmp_path):
    e = Estado(tmp_path)
    for _ in range(MAX_TENTATIVAS):
        assert e.elegivel("abcdefghijk")
        e.registrar_falha("abcdefghijk", "T", 1790000000, "analise", "json inválido")
    assert not e.elegivel("abcdefghijk")
    assert list(e.abandonados()) == ["abcdefghijk"]
    assert e.pendentes_ativos() == []


def test_erro_longo_truncado(tmp_path):
    e = Estado(tmp_path)
    e.registrar_falha("abcdefghijk", "T", 0, "extracao", "e" * 1000)
    assert len(e.pendentes["abcdefghijk"]["ultimo_erro"]) == 300


def test_inicio_backfill_e_execucao(tmp_path):
    e = Estado(tmp_path)
    e.definir_inicio(date(2026, 9, 25))
    e.definir_inicio(date(2026, 9, 22))
    e.definir_inicio(date(2026, 9, 27))
    e.concluir_backfill()
    e.registrar_execucao(5)
    e.salvar()
    e2 = Estado(tmp_path)
    assert e2.inicio == date(2026, 9, 22)
    assert e2.backfill_concluido is True
    assert e2.execucao["videos"] == 5


def test_cli_processado_via_arquivo(tmp_path):
    arquivo = tmp_path / "publicados.json"
    gravar_json(arquivo, {"abcdefghijk": "2026-09-28", "bbbbbbbbbbb": "2026-09-27"})
    assert mod.main(["--data", str(tmp_path), "processado", "--arquivo", str(arquivo)]) == 0
    e = Estado(tmp_path)
    assert e.processados["bbbbbbbbbbb"]["edicao"] == "2026-09-27"


def test_cli_modo(tmp_path, capsys):
    mod.main(["--data", str(tmp_path), "modo"])
    assert capsys.readouterr().out.strip() == "backfill"
    mod.main(["--data", str(tmp_path), "backfill-concluido"])
    mod.main(["--data", str(tmp_path), "modo"])
    assert capsys.readouterr().out.strip() == "diario"


def test_cli_falha_por_pasta_le_meta_e_tira_analise_das_etapas_seguintes(tmp_path):
    import shutil
    from pathlib import Path
    fix = Path(__file__).parent / "fixtures" / "video"
    pasta = tmp_path / "trab" / "abcdefghijk"
    pasta.mkdir(parents=True)
    shutil.copy(fix / "meta.json", pasta / "meta.json")
    shutil.copy(fix / "analise.json", pasta / "analise.json")
    (pasta / "erros.txt").write_text('tema: "x" is not one of [...]\n$(rm -rf /)')
    assert mod.main(["--data", str(tmp_path / "data"), "falha", "--pasta", str(pasta), "--etapa", "analise"]) == 0
    p = Estado(tmp_path / "data").pendentes["abcdefghijk"]
    assert p["titulo"] == "Scale the Judgment, Not the Model — Andrew Orobator, Reddit"
    assert p["publicado_ts"] == 1790524817
    assert p["ultimo_erro"].startswith('tema: "x"')
    assert not (pasta / "analise.json").exists() and (pasta / "analise.invalido.json").exists()
