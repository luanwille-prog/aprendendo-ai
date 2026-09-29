from pathlib import Path

import montar_site
from comum import gravar_json
from estado import Estado


def video(vid, edicao, **extra):
    base = {
        "id": vid, "titulo": f"Talk {vid} — Ana, Weights & Biases", "titulo_curto": f"Talk {vid}",
        "palestrante": "Ana, Weights & Biases", "url": f"https://www.youtube.com/watch?v={vid}",
        "duracao": 900, "publicado_ts": 1790524817, "edicao": edicao,
        "tese": "Escale o julgamento, não o modelo", "tldr": ["Frase um aqui.", "Frase dois aqui.", "Frase três aqui."],
        "tema": "evals", "complexidade": 4,
        "ideias": [
            {"titulo": "Critério", "texto": "Texto da ideia um.", "t": 312, "legenda": "O slide", "print": f"img/{vid}/0.jpg"},
            {"titulo": "Sem imagem", "texto": "Texto da ideia dois.", "t": 400, "legenda": "Sem print", "print": None},
        ],
        "conceitos": [
            {"nome": "LLM-as-judge", "traducao": "modelo como juiz", "nivel": "avancado", "chave": "llm-as-judge",
             "analogia": "É como um corretor com gabarito.", "explicacao": ["Passo um.", "Passo dois.", "Passo três."],
             "pre_requisitos": ["eval"], "desenho": {"nos": [{"rotulo": "A", "nota": "n1"}, {"rotulo": "B", "nota": "n2"}]},
             "no_glossario": False},
            {"nome": "eval", "traducao": "avaliação", "nivel": "basico", "chave": "eval", "analogia": None,
             "explicacao": [], "pre_requisitos": [], "desenho": None, "no_glossario": True},
            {"nome": "token", "traducao": "pedaço de texto", "nivel": "basico", "chave": "token", "analogia": None,
             "explicacao": [], "pre_requisitos": [], "desenho": None, "no_glossario": False},
        ],
        "leitura_critica": "Amostra de um único produto.", "acoes": ["Escreva três critérios."],
        "numeros": [{"valor": "3x", "contexto": "menos regressões", "t": 610}],
    }
    base.update(extra)
    return base


def preparar(tmp_path):
    data = tmp_path / "data"
    gravar_json(data / "videos" / "aaaaaaaaaaa.json", video("aaaaaaaaaaa", "2026-09-28"))
    gravar_json(data / "videos" / "bbbbbbbbbbb.json", video("bbbbbbbbbbb", "2026-09-28",
                titulo_curto='Agents <script>alert("x")</script> & Co'))
    gravar_json(data / "videos" / "ccccccccccc.json", video("ccccccccccc", "2026-09-27"))
    gravar_json(data / "dias" / "2026-09-28.json", {"edicao": "2026-09-28", "titulo": "O dia dos juízes",
                "abertura": "Hoje dois talks falam de avaliação.", "ordem": ["bbbbbbbbbbb", "aaaaaaaaaaa"],
                "conceitos_novos": []})
    gravar_json(data / "glossario.json", {"eval": {"chave": "eval", "nome": "eval", "traducao": "avaliação",
                "analogia": "Uma prova com gabarito.", "explicacao": ["a", "b", "c"], "video_id": "ccccccccccc",
                "video_titulo": "Talk ccccccccccc", "edicao": "2026-09-27"}})
    e = Estado(data)
    e.registrar_falha("ddddddddddd", "Pendente & cia", 1.0, "extracao", "x")
    for _ in range(3):
        e.registrar_falha("eeeeeeeeeee", "Desistido", 1.0, "extracao", "x")
    e.registrar_execucao(3)
    e.salvar()
    return data


def test_monta_index_e_fragmentos(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    assert montar_site.montar(data, site) == ["2026-09-28", "2026-09-27"]
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "O dia dos juízes" in html
    assert 'data-src="dias/2026-09-27.html"' in html
    assert (site / "dias" / "2026-09-27.html").exists()
    assert "<html" not in (site / "dias" / "2026-09-27.html").read_text(encoding="utf-8")
    for arq in ("estilo.css", "app.js", ".nojekyll"):
        assert (site / arq).exists()


def test_ignora_arquivos_ocultos_do_macos(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    (data / "videos" / "._aaaaaaaaaaa.json").write_bytes(b"\x00\x05\x16\x07\x00")
    (data / "dias" / "._2026-09-28.json").write_bytes(b"\x00\x05\x16\x07\x00")
    assert montar_site.montar(data, site) == ["2026-09-28", "2026-09-27"]


def test_ordem_de_leitura_e_escape(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert html.index('id="v-bbbbbbbbbbb"') < html.index('id="v-aaaaaaaaaaa"')
    assert "<script>alert" not in html
    assert "Agents &lt;script&gt;alert(&#34;x&#34;)&lt;/script&gt; &amp; Co" in html
    assert "Weights &amp; Biases" in html


def test_links_de_minuto_prints_e_conceitos(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert 'href="https://www.youtube.com/watch?v=aaaaaaaaaaa&amp;t=312s"' in html
    assert 'src="img/aaaaaaaaaaa/0.jpg"' in html
    assert "▶ 06:40" in html  # ideia sem print mostra o link do minuto em texto
    assert "É como um corretor com gabarito." in html
    assert 'href="#g-eval"' in html  # conceito já no glossário vira link
    assert "token (pedaço de texto)" in html  # termo básico aparece com tradução
    assert 'id="g-eval"' in html
    assert "●●●●○" in html


def test_rodape(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "Pendente &amp; cia" in html and "(1/3)" in html
    assert "Desistido" in html


def test_site_vazio(tmp_path):
    site = tmp_path / "site"
    assert montar_site.montar(tmp_path / "data", site) == []
    assert "Nenhuma edição publicada ainda." in (site / "index.html").read_text(encoding="utf-8")
