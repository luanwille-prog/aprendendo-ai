"""Monta o site estático (site/) a partir de data/, no template Quadro Anotado.

Saída:
- index.html: home com a última edição em destaque e as anteriores agrupadas por semana;
- edicoes/<data>.html: uma página por edição, com os essenciais completos e o resto no radar;
- talks.html e trilhas/<tema>.html: todos os talks, com busca, e uma trilha de estudo por tema;
- semanas/<segunda>.html: a semana em 5 ideias, para quem lê uma vez por semana;
- glossario.html, status.html, 404.html e feed.xml (Atom).
"""
from __future__ import annotations

import argparse
import math
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from canonizar import Resolvedor, ler_aliases
from comum import (DATA, MESES, SITE, SITE_CAMINHO, SITE_URL, TEMAS, TEMPLATES, TZ, chave, fmt_data, fmt_datahora,
                   fmt_tempo, ler_json, listar_json, slug, titulo_e_palestrante)
from estado import MAX_TENTATIVAS, Estado

PALAVRAS_POR_MINUTO = 200
REVISAO_DIAS = (1, 7, 30)  # repetição espaçada: perguntas de edições de ontem, da semana passada e do mês passado


def _ambiente() -> Environment:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2", "xml"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["tempo"] = fmt_tempo
    env.filters["slug"] = slug
    env.globals["TEMAS"] = TEMAS
    env.globals["MAX_TENTATIVAS"] = MAX_TENTATIVAS
    return env


def _data_curta(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {MESES[d.month - 1]}"


def _duracao_fmt(segundos: int) -> str:
    minutos = round(segundos / 60)
    h, m = divmod(minutos, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def _leitura_fmt(minutos: int) -> str:
    h, m = divmod(minutos, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def _letra(nome: str) -> str:
    inicial = unicodedata.normalize("NFKD", nome.strip()[:1]).encode("ascii", "ignore").decode().upper()
    return inicial if inicial.isalpha() else "#"


def _normalizar_video(v: dict) -> dict:
    """Corrige na renderização o que a extração antiga deixou passar (palestrante grudado no título)."""
    if not v.get("palestrante"):
        curto, palestrante = titulo_e_palestrante(v.get("titulo_curto") or v["titulo"])
        if palestrante:
            v["titulo_curto"], v["palestrante"] = curto, palestrante
    return v


def _palavras(*textos) -> int:
    return sum(len(re.findall(r"\w+", t or "")) for t in textos)


def minutos_de_leitura(v: dict) -> int:
    """Estimativa do tempo de leitura do bloco (não do vídeo), a 200 palavras por minuto."""
    n = _palavras(v.get("tese"), v.get("objetivo"), v.get("leitura_critica"), *v.get("tldr", []), *v.get("acoes", []))
    n += sum(_palavras(i.get("titulo"), i.get("texto")) for i in v.get("ideias", []))
    n += sum(_palavras(c.get("analogia"), *c.get("explicacao", [])) for c in v.get("conceitos", []))
    n += sum(_palavras(p.get("pergunta")) for p in v.get("perguntas") or [])
    exp = v.get("experimento") or {}
    n += _palavras(exp.get("titulo"), exp.get("precisa"), exp.get("sucesso"), *exp.get("passos", []))
    return max(2, math.ceil(n / PALAVRAS_POR_MINUTO))


def _ordenar(videos: list[dict], dia: dict | None) -> list[dict]:
    posicao = {vid: i for i, vid in enumerate((dia or {}).get("ordem", []))}
    return sorted(videos, key=lambda v: (posicao.get(v["id"], len(posicao)), v.get("publicado_ts") or 0))


def _essenciais(videos: list[dict], dia: dict | None) -> dict[str, str]:
    """{id: por_que} dos talks para ler por completo. Sem escolha do editor, os 2 primeiros da ordem."""
    ids = {v["id"] for v in videos}
    escolhidos = {e["id"]: e["por_que"] for e in (dia or {}).get("essenciais", []) if e["id"] in ids}
    if escolhidos:
        return escolhidos
    return {v["id"]: "" for v in videos[: (len(videos) if len(videos) <= 3 else 2)]}


def _relacionados(videos: list[dict], limite: int = 3) -> dict[str, list[dict]]:
    """Talks que compartilham conceitos, pesando os conceitos raros (IDF): "agente" liga pouco, "KV cache" liga muito.
    Para entrar, a afinidade precisa valer ao menos 60% de um conceito que só dois talks citam."""
    chaves = {v["id"]: {c["chave"] for c in v["conceitos"]} for v in videos}
    df = Counter(k for ks in chaves.values() for k in ks)
    n = len(videos)
    idf = {k: math.log(n / d) for k, d in df.items()}
    minimo = 0.6 * math.log(n / 2) if n > 2 else float("inf")
    por_id = {v["id"]: v for v in videos}
    saida = {}
    for v in videos:
        notas = []
        for outro, ks in chaves.items():
            if outro == v["id"]:
                continue
            comuns = chaves[v["id"]] & ks
            nota = sum(idf[k] for k in comuns)
            if nota >= minimo:
                notas.append((nota, outro, comuns))
        notas.sort(key=lambda x: (-x[0], x[1]))
        saida[v["id"]] = [{"video": por_id[o], "comuns": sorted(por_id[o]["conceitos_nomes"].get(k, k) for k in c)[:3]}
                          for _, o, c in notas[:limite]]
    return saida


def _semana(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _cinco_ideias(edicoes: list[dict]) -> list[dict]:
    """Até 5 talks da semana: os essenciais, variando o tema."""
    candidatos = [v for ed in sorted(edicoes, key=lambda e: e["edicao"]) for v in ed["essenciais"]]
    escolhidos, temas = [], set()
    for v in candidatos:  # primeiro um por tema
        if v["tema"] not in temas and len(escolhidos) < 5:
            escolhidos.append(v)
            temas.add(v["tema"])
    for v in candidatos:  # depois completa
        if v not in escolhidos and len(escolhidos) < 5:
            escolhidos.append(v)
    return escolhidos


def _revisao(edicao: dict, edicoes_por_data: dict[str, dict]) -> list[dict]:
    """Uma pergunta de recuperação de edições de ~1, ~7 e ~30 dias antes desta."""
    datas = sorted(edicoes_por_data)
    d0 = date.fromisoformat(edicao["edicao"])
    itens, usadas = [], set()
    for dias in REVISAO_DIAS:
        alvo = d0 - timedelta(days=dias)
        candidatas = [d for d in datas if alvo - timedelta(days=max(2, dias // 3)) <= date.fromisoformat(d) <= alvo]
        if not candidatas or candidatas[-1] in usadas:
            continue
        ed = edicoes_por_data[candidatas[-1]]
        for v in ed["essenciais"] + ed["radar"]:
            perguntas = [p for p in v.get("perguntas") or [] if p["tipo"] == "lembrar"]
            if perguntas:
                usadas.add(ed["edicao"])
                distancia = (d0 - date.fromisoformat(ed["edicao"])).days
                itens.append({"rotulo": "ontem" if distancia == 1 else f"há {distancia} dias",
                              "video": v, "edicao": ed, "pergunta": perguntas[0]})
                break
    return itens


def _glossario(entradas: list[dict]) -> list[dict]:
    grupos: dict[str, list] = defaultdict(list)
    for g in sorted(entradas, key=lambda g: chave(g["nome"])):
        g = dict(g)
        g.setdefault("chave", chave(g["nome"]))
        if g.get("aparicoes") is None:
            g["aparicoes"] = [{"video_id": g["video_id"], "video_titulo": g["video_titulo"], "edicao": g["edicao"]}]
        grupos[_letra(g["nome"])].append(g)
    saida = []
    for letra in sorted(grupos, key=lambda x: (x == "#", x)):
        termos = grupos[letra]
        # termos citados uma vez e sem analogia ficam recolhidos: ainda achados pela busca
        principais = [g for g in termos if g.get("analogia") or len(g["aparicoes"]) != 1]
        raros = [g for g in termos if g not in principais]
        saida.append({"letra": letra, "termos": principais, "raros": raros})
    return saida


def montar(pasta_data: Path, pasta_site: Path) -> list[str]:
    pasta_data, pasta_site = Path(pasta_data), Path(pasta_site)
    env = _ambiente()
    glossario = ler_json(pasta_data / "glossario.json", {})
    resolver = Resolvedor(glossario, ler_aliases(pasta_data))

    def ancora_glossario(nome: str) -> str | None:
        """Âncora do termo no glossário, ou None quando o termo não tem entrada (vira texto simples)."""
        k = resolver(nome)
        return f"g-{slug(k)}" if k else None

    env.globals["ancora_glossario"] = ancora_glossario
    env.globals["analogia_no_glossario"] = lambda k: bool((glossario.get(k) or {}).get("analogia"))

    por_edicao: dict[str, list] = defaultdict(list)
    todos = []
    for arq in listar_json(pasta_data / "videos"):
        v = _normalizar_video(ler_json(arq))
        for c in v["conceitos"]:  # tradução canônica: a mesma em todo o site
            g = glossario.get(c["chave"])
            if g and g.get("traducao"):
                c["traducao"] = g["traducao"]
        v["conceitos_nomes"] = {c["chave"]: c["nome"] for c in v["conceitos"]}
        v["minutos"] = minutos_de_leitura(v)
        v["edicao_curta"] = _data_curta(v["edicao"])
        consolidado = v.get("consolidado_em")
        v["acrescentado"] = (_data_curta(consolidado[:10]) if consolidado and
                             (date.fromisoformat(consolidado[:10]) - date.fromisoformat(v["edicao"])).days > 2 else None)
        por_edicao[v["edicao"]].append(v)
        todos.append(v)
    dias = {arq.stem: ler_json(arq) for arq in listar_json(pasta_data / "dias")}
    por_id = {v["id"]: v for v in todos}

    edicoes = []
    for e in sorted(por_edicao, reverse=True):
        dia = dias.get(e)
        videos = _ordenar(por_edicao[e], dia)
        motivos = _essenciais(videos, dia)
        essenciais = [v for v in videos if v["id"] in motivos]
        radar = [v for v in videos if v["id"] not in motivos]
        for v in videos:
            v["essencial"] = v["id"] in motivos
            v["por_que"] = motivos.get(v["id"]) or None
        temas_ids = list(dict.fromkeys(v["tema"] for v in videos))
        leitura = sum(v["minutos"] for v in videos)
        edicoes.append({
            "edicao": e, "data_fmt": fmt_data(e), "data_curta": _data_curta(e), "dia": dia,
            "videos": essenciais + radar, "essenciais": essenciais, "radar": radar,
            "titulo": (dia or {}).get("titulo") or "Talks do dia",
            "temas": [TEMAS.get(t, t) for t in temas_ids], "temas_ids": temas_ids,
            "duracao_fmt": _duracao_fmt(sum(v.get("duracao") or 0 for v in videos)),
            "leitura_fmt": _leitura_fmt(leitura), "leitura_essenciais": sum(v["minutos"] for v in essenciais),
            "objetivos": [v["objetivo"] for v in essenciais if v.get("objetivo")],
            "capa": next((i["print"] for v in essenciais + radar for i in v["ideias"] if i.get("print")), None),
        })
    edicoes_por_data = {ed["edicao"]: ed for ed in edicoes}

    relacionados = _relacionados(todos)
    conversas = defaultdict(list)  # diálogos que o editor anotou entre talks de dias diferentes
    for dia in dias.values():
        for d in dia.get("dialogos", []):
            if d["id"] in por_id and d["com"] in por_id:
                conversas[d["id"]].append({**d, "video": por_id[d["com"]]})
    for v in todos:
        v["relacionados"] = relacionados[v["id"]]
        v["conversas"] = conversas.get(v["id"], [])

    estado = Estado(pasta_data)
    execucao = dict(estado.execucao)
    if execucao.get("em"):
        execucao["em_fmt"] = fmt_datahora(execucao["em"])
        execucao["dia_curto"] = _data_curta(datetime.fromisoformat(execucao["em"]).astimezone(TZ).date().isoformat())
    comum = {"execucao": execucao or None}

    for antigo in ("dias",):  # fragmentos da versão com edições recolhidas
        if (pasta_site / antigo).exists():
            shutil.rmtree(pasta_site / antigo)
    for pasta in ("edicoes", "trilhas", "semanas"):
        (pasta_site / pasta).mkdir(parents=True, exist_ok=True)

    semanas_ids = {}
    for ed in edicoes:
        semanas_ids.setdefault(_semana(date.fromisoformat(ed["edicao"])).isoformat(), []).append(ed)

    pagina_edicao = env.get_template("edicao.html.j2")
    for i, ed in enumerate(edicoes):
        html = pagina_edicao.render(
            raiz="../", pagina="edicao", ed=ed, edicao=ed["edicao"], dia=ed["dia"], titulo=ed["titulo"],
            revisao=_revisao(ed, edicoes_por_data),
            anterior=edicoes[i + 1] if i + 1 < len(edicoes) else None,
            proxima=edicoes[i - 1] if i > 0 else None, **comum)
        (pasta_site / "edicoes" / f"{ed['edicao']}.html").write_text(html, encoding="utf-8")

    # semana em 5 ideias
    semanas = []
    for seg, eds in semanas_ids.items():
        d = date.fromisoformat(seg)
        semana = {"id": seg, "rotulo": f"Semana de {d.day} {MESES[d.month - 1]}", "edicoes": eds,
                  "ideias": _cinco_ideias(eds), "total": sum(len(e["videos"]) for e in eds)}
        semanas.append(semana)
        html = env.get_template("semana.html.j2").render(raiz="../", pagina="semana", semana=semana, **comum)
        (pasta_site / "semanas" / f"{seg}.html").write_text(html, encoding="utf-8")

    # "continuar de onde parei": edições da mais nova para a mais antiga, talks na ordem de exibição
    talks = [{"e": ed["edicao"], "d": ed["data_curta"],
              "t": [{"id": v["id"], "h": f"edicoes/{ed['edicao']}.html#v-{v['id']}", "n": v.get("rotulo") or v["titulo_curto"]}
                    for v in ed["videos"]]} for ed in edicoes]
    anteriores = edicoes[1:]
    index = env.get_template("index.html.j2").render(
        raiz="", pagina="home", atual=edicoes[0] if edicoes else None,
        semanas=[s for s in semanas if any(e in anteriores for e in s["edicoes"])], anteriores=anteriores,
        temas_todos=sorted({t for ed in anteriores for t in ed["temas_ids"]}), talks=talks, **comum)
    (pasta_site / "index.html").write_text(index, encoding="utf-8")

    # todos os talks e trilhas por tema
    lista = [v for ed in edicoes for v in ed["videos"]]
    trilhas = []
    for tema, nome in TEMAS.items():
        dele = [v for v in lista if v["tema"] == tema]
        if not dele:
            continue
        ordem = sorted(dele, key=lambda v: (v["complexidade"], not v["essencial"], v["edicao"]))
        comeco = [v for v in ordem if v["essencial"]][:3] or ordem[:3]
        trilhas.append({"tema": tema, "nome": nome, "talks": ordem, "comeco": comeco,
                        "niveis": Counter(v["complexidade"] for v in dele)})
    html = env.get_template("talks.html.j2").render(raiz="", pagina="talks", talks=lista, trilhas=trilhas, **comum)
    (pasta_site / "talks.html").write_text(html, encoding="utf-8")
    for t in trilhas:
        html = env.get_template("trilha.html.j2").render(raiz="../", pagina="talks", trilha=t, **comum)
        (pasta_site / "trilhas" / f"{t['tema']}.html").write_text(html, encoding="utf-8")

    titulos = {v["id"]: v["titulo_curto"] for v in todos}
    entradas = [dict(g) for g in glossario.values()]
    for g in entradas:
        g["aparicoes"] = [{**a, "video_titulo": titulos.get(a["video_id"], a["video_titulo"])}
                          for a in (g.get("aparicoes") if g.get("aparicoes") is not None else
                                    [{"video_id": g["video_id"], "video_titulo": g["video_titulo"], "edicao": g["edicao"]}])
                          if a["video_id"] in titulos]
    html = env.get_template("glossario.html.j2").render(
        raiz="", pagina="glossario", grupos=_glossario(entradas), total=len(entradas),
        com_analogia=sum(1 for g in entradas if g.get("analogia")), **comum)
    (pasta_site / "glossario.html").write_text(html, encoding="utf-8")

    html = env.get_template("status.html.j2").render(
        raiz="", pagina="status",
        pendentes=[{"id": vid, **estado.pendentes[vid]} for vid in estado.pendentes_ativos()],
        abandonados=[{"id": vid, **p} for vid, p in estado.abandonados().items()],
        total_videos=sum(len(ed["videos"]) for ed in edicoes), total_edicoes=len(edicoes), **comum)
    (pasta_site / "status.html").write_text(html, encoding="utf-8")

    html = env.get_template("404.html.j2").render(
        raiz=SITE_CAMINHO, pagina="404", atual=edicoes[0] if edicoes else None, **comum)
    (pasta_site / "404.html").write_text(html, encoding="utf-8")

    feed = env.get_template("feed.xml.j2").render(
        site_url=SITE_URL, edicoes=edicoes[:30],
        atualizado=execucao.get("em") or (f"{edicoes[0]['edicao']}T10:00:00-03:00" if edicoes else "2026-01-01T00:00:00Z"))
    (pasta_site / "feed.xml").write_text(feed, encoding="utf-8")

    for estatico in ("estilo.css", "app.js", "favicon.svg"):
        shutil.copy(TEMPLATES / estatico, pasta_site / estatico)
    (pasta_site / ".nojekyll").touch()
    return [ed["edicao"] for ed in edicoes]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--site", type=Path, default=SITE)
    a = ap.parse_args(argv)
    edicoes = montar(a.data, a.site)
    print(f"site montado com {len(edicoes)} edição(ões) em {a.site}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
