import canonizar
from comum import gravar_json, ler_json


def entrada(k, vid, analogia=None):
    return {"chave": k, "nome": k, "traducao": "t", "analogia": analogia, "explicacao": ["a"] if analogia else [],
            "video_id": vid, "video_titulo": vid, "edicao": "2026-09-28",
            "aparicoes": [{"video_id": vid, "video_titulo": vid, "edicao": "2026-09-28"}]}


def conceito(k):
    return {"nome": k, "traducao": "t", "nivel": "basico", "chave": k, "analogia": None, "explicacao": [],
            "pre_requisitos": [], "desenho": None, "no_glossario": False}


def test_funde_duplicatas_e_troca_chaves(tmp_path):
    gravar_json(tmp_path / "aliases.json", {"Skills": "skill", "llm judge": "llm-as-a-judge"})
    gravar_json(tmp_path / "glossario.json", {"skill": entrada("skill", "aaaaaaaaaaa"),
                                              "skills": entrada("skills", "bbbbbbbbbbb", analogia="Uma receita."),
                                              "llm judge": entrada("llm judge", "aaaaaaaaaaa")})
    gravar_json(tmp_path / "videos" / "bbbbbbbbbbb.json", {"id": "bbbbbbbbbbb",
                "conceitos": [conceito("skills"), conceito("skill")]})
    r = canonizar.canonizar(tmp_path)
    g = ler_json(tmp_path / "glossario.json")
    assert set(g) == {"skill", "llm-as-a-judge"}
    assert {a["video_id"] for a in g["skill"]["aparicoes"]} == {"aaaaaaaaaaa", "bbbbbbbbbbb"}
    assert g["skill"]["analogia"] == "Uma receita."  # a duplicata empresta a analogia
    v = ler_json(tmp_path / "videos" / "bbbbbbbbbbb.json")
    assert [c["chave"] for c in v["conceitos"]] == ["skill"]
    assert r["videos"] == 1
    assert canonizar.canonizar(tmp_path)["fundidos"] == {}  # idempotente


def test_resolvedor_aceita_plural_alias_e_acento():
    g = {"embedding": {}, "llm": {}, "agente de ia": {}}
    r = canonizar.Resolvedor(g, {"modelo de linguagem": "llm"})
    assert r("Embeddings") == "embedding"
    assert r("Modelo de linguagem") == "llm"
    assert r("Agente de IA") == "agente de ia"
    assert r("Inexistente") is None
