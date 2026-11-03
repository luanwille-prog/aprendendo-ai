from pathlib import Path

import montar_site
from comum import gravar_json, ler_json
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
    gravar_json(data / "videos" / "bbbbbbbbbbb.json", video("bbbbbbbbbbb", "2026-09-28", tema="agentes",
                titulo_curto='Agents <script>alert("x")</script> & Co'))
    gravar_json(data / "videos" / "ccccccccccc.json", video("ccccccccccc", "2026-09-27"))
    gravar_json(data / "dias" / "2026-09-28.json", {"edicao": "2026-09-28", "titulo": "O dia dos juízes",
                "abertura": "Hoje dois talks falam de avaliação.", "ordem": ["bbbbbbbbbbb", "aaaaaaaaaaa"],
                "conceitos_novos": []})
    gravar_json(data / "glossario.json", {"eval": {"chave": "eval", "nome": "eval", "traducao": "avaliação",
                "analogia": "Uma prova com gabarito.", "explicacao": ["a", "b", "c"], "video_id": "ccccccccccc",
                "video_titulo": "Talk ccccccccccc", "edicao": "2026-09-27",
                "aparicoes": [{"video_id": "ccccccccccc", "video_titulo": "Talk ccccccccccc", "edicao": "2026-09-27"},
                              {"video_id": "aaaaaaaaaaa", "video_titulo": "Talk aaaaaaaaaaa", "edicao": "2026-09-28"}]}})
    e = Estado(data)
    e.registrar_falha("ddddddddddd", "Pendente & cia", 1.0, "extracao", "x")
    for _ in range(3):
        e.registrar_falha("eeeeeeeeeee", "Desistido", 1.0, "extracao", "x")
    e.registrar_execucao(3)
    e.salvar()
    return data


def ler(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_home_com_destaque_e_cartoes(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    assert montar_site.montar(data, site) == ["2026-09-28", "2026-09-27"]
    html = ler(site / "index.html")
    assert "O dia dos juízes" in html and "Hoje dois talks falam de avaliação." in html
    assert 'class="botao" href="edicoes/2026-09-28.html"' in html
    assert 'class="cartao" href="edicoes/2026-09-28.html"' not in html  # a última edição não se repete na grade
    assert 'class="cartao" href="edicoes/2026-09-27.html"' in html
    assert 'data-temas="evals"' in html  # filtro por tema entre edições
    assert 'data-ids="bbbbbbbbbbb aaaaaaaaaaa"' in html  # progresso segue a ordem de leitura
    assert 'id="continuar"' in html and "edicoes/2026-09-28.html#v-bbbbbbbbbbb" in html
    assert '"d": "28 set", "e": "2026-09-28"' in html  # progresso agrupado por edição
    assert 'href="glossario.html"' in html
    assert 'class="video"' not in html  # a home não carrega os blocos completos
    for arq in ("estilo.css", "app.js", ".nojekyll", "favicon.svg"):
        assert (site / arq).exists()


def test_pagina_de_edicao_com_navegacao(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    nova, antiga = ler(site / "edicoes" / "2026-09-28.html"), ler(site / "edicoes" / "2026-09-27.html")
    assert nova.lower().startswith("<!doctype html>")
    assert 'href="../estilo.css"' in nova and 'src="../app.js"' in nova and 'href="../index.html"' in nova
    assert 'href="2026-09-27.html"' in nova  # anterior
    assert 'href="2026-09-28.html"' in antiga  # próxima
    assert 'rel="prev"' not in antiga  # a primeira edição não tem anterior
    assert 'class="filtro"' not in nova  # o filtro por tema fica na home
    assert 'class="fim-edicao' in nova


def test_bloco_de_video_orienta_a_leitura(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = ler(site / "edicoes" / "2026-09-28.html")
    bloco = html[html.index('id="v-aaaaaaaaaaa"'):]
    assert '<h2 id="t-aaaaaaaaaaa" lang="en">Talk aaaaaaaaaaa</h2>' in bloco
    assert bloco.index("Antes de ler") < bloco.index("Critério")  # termos antes das ideias
    assert 'role="img" aria-label="Complexidade 4 de 5"' in bloco
    # o primeiro talk da ordem (bbb) aponta para o próximo (aaa)
    primeiro = html[html.index('id="v-bbbbbbbbbbb"'):html.index('id="v-aaaaaaaaaaa"')]
    assert 'href="#v-aaaaaaaaaaa"' in primeiro


def test_ordem_de_leitura_e_escape(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    for html in (ler(site / "edicoes" / "2026-09-28.html"), ler(site / "index.html")):
        assert "<script>alert" not in html
        assert "Agents &lt;script&gt;alert(&#34;x&#34;)&lt;/script&gt; &amp; Co" in html
    ed = ler(site / "edicoes" / "2026-09-28.html")
    assert ed.index('id="v-bbbbbbbbbbb"') < ed.index('id="v-aaaaaaaaaaa"')
    assert "Weights &amp; Biases" in ed


def test_links_de_minuto_prints_e_conceitos(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = ler(site / "edicoes" / "2026-09-28.html")
    assert 'href="https://www.youtube.com/watch?v=aaaaaaaaaaa&amp;t=312s"' in html
    assert 'src="../img/aaaaaaaaaaa/0.jpg"' in html
    assert "06:40" in html  # ideia sem print mostra o link do minuto em texto
    assert "É como um corretor com gabarito." in html
    assert 'href="../glossario.html#g-eval"' in html  # termo linka para o glossário
    assert "pedaço de texto" in html  # termo básico aparece com tradução
    assert "●●●●○" in html


def test_glossario_em_pagina_propria(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = ler(site / "glossario.html")
    assert 'id="g-eval"' in html and '<h2 class="termo">eval</h2>' in html
    assert 'id="letra-E"' in html and 'type="search"' in html
    assert 'href="edicoes/2026-09-27.html#v-ccccccccccc"' in html
    assert 'href="edicoes/2026-09-28.html#v-aaaaaaaaaaa"' in html  # todas as aparições
    assert 'href="index.html"' in html


def test_status_da_rotina_em_pagina_propria(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    status, home = ler(site / "status.html"), ler(site / "index.html")
    assert "Pendente &amp; cia" in status and "(1/3)" in status and "Desistido" in status
    assert "Desistido" not in home and 'href="status.html"' in home
    assert 'class="pular" href="#conteudo"' in home
    assert home.index("</main>") < home.index("<footer")


def test_remove_fragmentos_da_versao_antiga(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    (site / "dias").mkdir(parents=True)
    (site / "dias" / "2026-09-27.html").write_text("velho")
    montar_site.montar(data, site)
    assert not (site / "dias").exists()


def test_ignora_arquivos_ocultos_do_macos(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    (data / "videos" / "._aaaaaaaaaaa.json").write_bytes(b"\x00\x05\x16\x07\x00")
    (data / "dias" / "._2026-09-28.json").write_bytes(b"\x00\x05\x16\x07\x00")
    assert montar_site.montar(data, site) == ["2026-09-28", "2026-09-27"]


def test_site_vazio(tmp_path):
    site = tmp_path / "site"
    assert montar_site.montar(tmp_path / "data", site) == []
    assert "Nenhuma edição publicada ainda." in ler(site / "index.html")
    assert (site / "glossario.html").exists()


def test_letra_de_mao_legivel_e_tese_em_fonte_de_texto(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = ler(site / "edicoes" / "2026-09-28.html")
    assert "family=Kalam:wght@400;700" in html and "Covered+By+Your+Grace" not in html
    assert '<p class="tese">' in html  # tese longa sai da letra de mão
    css = ler(site / "estilo.css")
    assert '--hand:"Kalam"' in css and "Covered By Your Grace" not in css


def ancoras_quebradas(site: Path) -> list[str]:
    """Links internos (página#âncora) cujo id não existe na página de destino."""
    import re
    ids, quebrados = {}, []
    paginas = [p for p in site.rglob("*.html") if not p.name.startswith(".")]
    for p in paginas:
        ids[p.resolve()] = set(re.findall(r'id="([^"]+)"', ler(p)))
    for p in paginas:
        for alvo, ancora in re.findall(r'href="([^"#:]*\.html|)#([^"]+)"', ler(p)):
            destino = (p.parent / alvo).resolve() if alvo else p.resolve()
            if destino in ids and ancora not in ids[destino]:
                quebrados.append(f"{p.name} -> {alvo}#{ancora}")
    return quebrados


def test_nenhuma_ancora_interna_quebrada(tmp_path):
    data = preparar(tmp_path)
    v = video("fffffffffff", "2026-09-27")
    v["conceitos"][0]["pre_requisitos"] = ["eval", "Agente de IA"]  # o segundo não está no glossário
    gravar_json(data / "videos" / "fffffffffff.json", v)
    site = tmp_path / "site"
    montar_site.montar(data, site)
    assert ancoras_quebradas(site) == []
    html = ler(site / "edicoes" / "2026-09-27.html")
    assert 'glossario.html#g-agente-de-ia' not in html and "Agente de IA" in html
    assert 'href="../glossario.html#g-eval">eval</a>' in html


def test_palestrante_sai_do_titulo_com_hifen(tmp_path):
    data = preparar(tmp_path)
    gravar_json(data / "videos" / "ggggggggggg.json", video(
        "ggggggggggg", "2026-09-27", titulo="Ship It Faster - Bia Souza, Acme",
        titulo_curto="Ship It Faster - Bia Souza, Acme", palestrante=None))
    site = tmp_path / "site"
    montar_site.montar(data, site)
    html = ler(site / "edicoes" / "2026-09-27.html")
    assert '<h2 id="t-ggggggggggg" lang="en">Ship It Faster</h2>' in html
    assert '<span class="chip">Bia Souza, Acme</span>' in html


def test_rotulo_do_checkbox_igual_ao_texto_visivel(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = ler(site / "edicoes" / "2026-09-28.html")
    assert 'aria-label="Marcar' not in html
    assert '<span class="estudei-txt">Marquei como estudado</span><span class="sr">: <span lang="en">Talk aaaaaaaaaaa</span></span>' in html


def test_pagina_404(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    montar_site.montar(data, site)
    html = ler(site / "404.html")
    assert "Página não encontrada" in html
    assert "/aprendendo-ai/edicoes/2026-09-28.html" in html  # links absolutos: o 404 vale para qualquer caminho


DIDATICA = {
    "rotulo": "Juízes automáticos para avaliar respostas",
    "objetivo": "escrever três critérios e usar um modelo como juiz",
    "perguntas": [{"tipo": "lembrar", "pergunta": "O que o juiz recebe?", "resposta": "Os critérios e a resposta."},
                  {"tipo": "aplicar", "pergunta": "Que critério você usaria?", "resposta": "Fidelidade ao ticket."},
                  {"tipo": "criticar", "pergunta": "Qual o limite da evidência?", "resposta": "Um único produto."}],
    "experimento": {"titulo": "Seu primeiro juiz", "minutos": 30, "precisa": "Claude e 10 respostas",
                    "passos": ["Escreva três critérios.", "Peça notas de 1 a 5."], "sucesso": "Concorda em 8 de 10."},
}


def preparar_camadas(tmp_path):
    """Uma edição com 5 talks (2 essenciais) e edições 1 e 7 dias antes, com perguntas para revisar."""
    data = preparar(tmp_path)
    ids = [c * 11 for c in "hijkl"]
    for vid in ids:
        gravar_json(data / "videos" / f"{vid}.json", video(vid, "2026-10-05", **DIDATICA))
    gravar_json(data / "dias" / "2026-10-05.json", {"edicao": "2026-10-05", "titulo": "Dia de camadas",
                "abertura": "Cinco talks sobre juízes.", "ordem": ids, "conceitos_novos": [],
                "essenciais": [{"id": ids[2], "por_que": "Mostra o mecanismo inteiro."},
                               {"id": ids[4], "por_que": "Traz números de produção."}]})
    gravar_json(data / "videos" / "mmmmmmmmmmm.json", video("mmmmmmmmmmm", "2026-10-04", **DIDATICA))
    gravar_json(data / "videos" / "nnnnnnnnnnn.json", video("nnnnnnnnnnn", "2026-09-28", **{**DIDATICA,
                "perguntas": [{**DIDATICA["perguntas"][0], "pergunta": "Pergunta da semana passada?"}] + DIDATICA["perguntas"][1:]}))
    return data, ids


def test_edicao_em_camadas_essenciais_e_radar(tmp_path):
    data, ids = preparar_camadas(tmp_path)
    site = tmp_path / "site"
    montar_site.montar(data, site)
    html = ler(site / "edicoes" / "2026-10-05.html")
    radar = html.index('id="radar"')
    assert html.index(f'id="v-{ids[2]}"') < radar and html.index(f'id="v-{ids[4]}"') < radar  # essenciais antes
    assert html.index(f'id="v-{ids[0]}"') > radar  # o resto vai para o radar
    assert html.count('class="radar-item"') == 3
    assert "Mostra o mecanismo inteiro." in html and "essencial do dia" in html
    assert "Começar pelos 2 essenciais" in html
    assert "min de leitura" in html and "de talks" not in html.split("<main")[1].split("</header>")[0]
    assert ancoras_quebradas(site) == []


def test_bloco_didatico_e_revisao_espacada(tmp_path):
    data, ids = preparar_camadas(tmp_path)
    site = tmp_path / "site"
    montar_site.montar(data, site)
    html = ler(site / "edicoes" / "2026-10-05.html")
    assert "<h2 id=\"t-" + ids[2] + "\">Juízes automáticos para avaliar respostas</h2>" in html
    assert "Depois deste talk você consegue</span> escrever três critérios" in html
    assert "Teste você mesmo" in html and "Ver resposta" in html
    assert "experimente · 30 min" in html and "Deu certo se:" in html
    assert "Hoje você vai conseguir" in html
    revise = html[html.index('class="revise"'):]
    assert "ontem" in revise  # pergunta da edição de 4/10
    assert "há 7 dias" in revise
    assert "Pergunta da semana passada?" in revise  # 28/9 = 7 dias antes
    assert 'data-nota="' + ids[2] + '"' in html  # "o que eu levo deste talk"


def test_relacionados_por_conceito_raro(tmp_path):
    data, ids = preparar_camadas(tmp_path)
    raro = {"nome": "KV cache", "traducao": "cache", "nivel": "avancado", "chave": "kv cache", "analogia": None,
            "explicacao": [], "pre_requisitos": [], "desenho": None, "no_glossario": False}
    for vid in (ids[2], "mmmmmmmmmmm"):
        v = ler_json(data / "videos" / f"{vid}.json")
        v["conceitos"].append(raro)
        gravar_json(data / "videos" / f"{vid}.json", v)
    site = tmp_path / "site"
    montar_site.montar(data, site)
    html = ler(site / "edicoes" / "2026-10-05.html")
    bloco = html[html.index(f'id="v-{ids[2]}"'):html.index(f'id="v-{ids[4]}"')]
    assert "Conversa com outros talks" in bloco and "em comum: KV cache" in bloco
    assert "edicoes/2026-10-04.html#v-mmmmmmmmmmm" in bloco
    assert "Conversa com outros talks" not in html[html.index(f'id="v-{ids[4]}"'):html.index('id="radar"')]


def test_paginas_talks_trilhas_semana_e_feed(tmp_path):
    data, ids = preparar_camadas(tmp_path)
    site = tmp_path / "site"
    montar_site.montar(data, site)
    talks = ler(site / "talks.html")
    assert talks.count("<li data-id=") == 10 and 'id="busca-talks"' in talks
    assert 'href="trilhas/evals.html"' in talks
    trilha = ler(site / "trilhas" / "evals.html")
    assert "Comece por aqui" in trilha and "Nível ●●●●○" in trilha
    semana = ler(site / "semanas" / "2026-09-28.html")
    assert "A semana em" in semana and "ideias" in semana
    assert 'href="semanas/2026-09-28.html"' in ler(site / "index.html")
    feed = ler(site / "feed.xml")
    assert feed.startswith('<?xml') and "<entry>" in feed and "edicoes/2026-10-05.html" in feed
    assert ancoras_quebradas(site) == []


def test_glossario_recolhe_termos_raros_e_limita_aparicoes(tmp_path):
    data, site = preparar(tmp_path), tmp_path / "site"
    g = ler_json(data / "glossario.json")
    g["raro"] = {"chave": "raro", "nome": "raro", "traducao": "t", "analogia": None, "explicacao": [],
                 "video_id": "aaaaaaaaaaa", "video_titulo": "x", "edicao": "2026-09-28",
                 "aparicoes": [{"video_id": "aaaaaaaaaaa", "video_titulo": "x", "edicao": "2026-09-28"}]}
    g["base"] = {"chave": "base", "nome": "Base", "traducao": "t", "analogia": "Como uma régua.", "explicacao": ["a", "b", "c"],
                 "base": True, "video_id": None, "video_titulo": None, "edicao": None, "aparicoes": []}
    gravar_json(data / "glossario.json", g)
    montar_site.montar(data, site)
    html = ler(site / "glossario.html")
    assert 'class="raros"' in html and "citado uma vez só" in html
    assert "Termo de base" in html and 'data-analogia' in html
