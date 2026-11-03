(() => {
  // ---------- armazenamento (localStorage pode faltar: modo privado, bloqueio) ----------
  const ls = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} },
    chaves() { try { return Object.keys(localStorage); } catch (e) { return []; } },
  };
  const hoje = () => new Date().toLocaleDateString("sv-SE"); // AAAA-MM-DD no fuso do aparelho
  const sessao = new Set(); // vale mesmo sem localStorage
  // "estudei:<id>" guarda a data em que o talk foi marcado (versões antigas guardavam "1")
  const estudado = (id) => sessao.has(id) || ls.get("estudei:" + id) !== null;
  const normal = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  // ---------- tema ----------
  const botaoTema = document.querySelector(".tema-botao");
  if (botaoTema) {
    const ciclo = [null, "light", "dark"];
    const nome = { null: "automático", light: "claro", dark: "escuro" };
    const aplicar = (t) => {
      t ? document.documentElement.setAttribute("data-theme", t) : document.documentElement.removeAttribute("data-theme");
      botaoTema.setAttribute("aria-label", "Tema de cores: " + nome[t] + ". Trocar");
      botaoTema.textContent = t === "dark" ? "☾" : t === "light" ? "☀" : "◐";
    };
    aplicar(ls.get("tema"));
    botaoTema.addEventListener("click", () => {
      const atual = ls.get("tema");
      const prox = ciclo[(ciclo.indexOf(atual) + 1) % ciclo.length];
      ls.set("tema", prox);
      aplicar(prox);
    });
  }

  // ---------- progresso ----------
  function atualizarProgresso() {
    document.querySelectorAll(".progresso[data-ids]").forEach((el) => {
      const ids = el.dataset.ids.split(" ").filter(Boolean);
      if (!ids.length) return;
      const feitos = ids.filter(estudado).length;
      if (!feitos) { el.innerHTML = ""; return; } // nada de "0 de N": barra vazia desanima
      const pct = Math.round((feitos / ids.length) * 100);
      const rotulo = el.dataset.rotulo ? " " + el.dataset.rotulo : "";
      const sufixo = el.dataset.sufixo ? " " + el.dataset.sufixo : "";
      el.innerHTML = `<span class="barra" aria-hidden="true"><i style="width:${pct}%"></i></span><span>${feitos} de ${ids.length}${rotulo} estudados${sufixo}</span>`;
    });
    document.querySelectorAll(".indice li[data-id], .lista-busca li[data-id]").forEach((li) => {
      const feito = estudado(li.dataset.id);
      li.classList.toggle("feito", feito);
      let marca = li.querySelector(".marca-sr");
      if (feito && !marca) {
        marca = document.createElement("span");
        marca.className = "sr marca-sr";
        marca.textContent = " (estudado)";
        li.appendChild(marca);
      } else if (!feito && marca) marca.remove();
    });
    document.querySelectorAll(".radar-item[data-id]").forEach((d) => d.classList.toggle("feito", estudado(d.dataset.id)));
    atualizarContinuar();
    atualizarHabito();
  }

  // ---------- "Continuar": retoma a edição em andamento; as outras viram pendências arquiváveis ----------
  function atualizarContinuar() {
    const cont = document.getElementById("continuar");
    if (!cont) return;
    let eds = [];
    try { eds = JSON.parse(cont.dataset.talks || "[]"); } catch (e) {}
    const arquivada = (e) => ls.get("arquivei:" + e) === "1";
    const resumo = eds.map((ed) => ({ ...ed, feitos: ed.t.filter((t) => estudado(t.id)).length }));
    const andamento = resumo.filter((ed) => ed.feitos > 0 && ed.feitos < ed.t.length && !arquivada(ed.e));
    const alguem = resumo.some((ed) => ed.feitos > 0);
    const alvo = andamento[0] || resumo.find((ed) => ed.feitos === 0 && !arquivada(ed.e));
    const proximo = alvo && alvo.t.find((t) => !estudado(t.id));
    cont.hidden = !alguem || !proximo;
    if (proximo) {
      cont.href = proximo.h;
      cont.textContent = "Continuar: " + proximo.n;
    }
    const caixa = document.getElementById("pendencias");
    if (!caixa) return;
    const outras = andamento.filter((ed) => ed !== alvo);
    caixa.hidden = !outras.length;
    caixa.innerHTML = "";
    if (!outras.length) return;
    const titulo = document.createElement("p");
    titulo.className = "pendencias-titulo";
    titulo.textContent = "Ficou pela metade";
    const ul = document.createElement("ul");
    outras.forEach((ed) => {
      const falta = ed.t.length - ed.feitos;
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = ed.t.find((t) => !estudado(t.id)).h;
      a.textContent = `${falta} ${falta === 1 ? "talk" : "talks"} de ${ed.d}`;
      const b = document.createElement("button");
      b.type = "button";
      b.className = "arquivar";
      b.innerHTML = `Arquivar<span class="sr"> a edição de ${ed.d}</span>`;
      b.addEventListener("click", () => { ls.set("arquivei:" + ed.e, "1"); atualizarContinuar(); });
      li.append(a, " ", b);
      ul.appendChild(li);
    });
    caixa.append(titulo, ul);
  }

  // ---------- hábito: talks nesta semana e dias seguidos ----------
  function atualizarHabito() {
    const el = document.getElementById("habito");
    if (!el) return;
    const datas = ls.chaves().filter((k) => k.startsWith("estudei:")).map((k) => ls.get(k)).filter((v) => /^\d{4}-\d{2}-\d{2}$/.test(v || ""));
    if (!datas.length) { el.hidden = true; return; }
    const d0 = new Date(hoje() + "T12:00:00");
    const segunda = new Date(d0); segunda.setDate(d0.getDate() - ((d0.getDay() + 6) % 7));
    const semana = datas.filter((d) => d >= segunda.toLocaleDateString("sv-SE")).length;
    const dias = new Set(datas);
    let seguidos = 0;
    const cursor = new Date(d0);
    if (!dias.has(cursor.toLocaleDateString("sv-SE"))) cursor.setDate(cursor.getDate() - 1); // hoje ainda pode contar
    while (dias.has(cursor.toLocaleDateString("sv-SE"))) { seguidos++; cursor.setDate(cursor.getDate() - 1); }
    el.innerHTML = `<strong>${semana}</strong> ${semana === 1 ? "talk estudado" : "talks estudados"} nesta semana` +
      (seguidos > 1 ? ` · <strong>${seguidos}</strong> dias seguidos` : "");
    el.hidden = false;
  }

  // ---------- marcar como estudado e nota pessoal ----------
  document.querySelectorAll("input[data-id]").forEach((caixa) => {
    const id = caixa.dataset.id;
    const bloco = caixa.closest(".video");
    caixa.checked = estudado(id);
    bloco?.classList.toggle("feito", caixa.checked);
    caixa.addEventListener("change", () => {
      caixa.checked ? sessao.add(id) : sessao.delete(id);
      ls.set("estudei:" + id, caixa.checked ? hoje() : null);
      bloco?.classList.toggle("feito", caixa.checked);
      atualizarProgresso();
    });
  });
  document.querySelectorAll("textarea[data-nota]").forEach((t) => {
    t.value = ls.get("nota:" + t.dataset.nota) || "";
    t.addEventListener("input", () => ls.set("nota:" + t.dataset.nota, t.value.trim() ? t.value : null));
  });

  // ---------- filtro de edições por tema (home) ----------
  const botoes = document.querySelectorAll(".filtro:not(.filtro-talks) button");
  const status = document.querySelector(".filtro-status");
  botoes.forEach((b) => b.addEventListener("click", () => {
    const tema = b.dataset.tema;
    botoes.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    const cartoes = [...document.querySelectorAll(".cartao[data-temas]")];
    let visiveis = 0;
    cartoes.forEach((c) => {
      const mostra = !tema || c.dataset.temas.split(" ").includes(tema);
      c.hidden = !mostra;
      if (mostra) visiveis++;
    });
    document.querySelectorAll(".semana").forEach((s) => { s.hidden = !s.querySelector(".cartao:not([hidden])"); });
    if (status) status.textContent = tema ? `Mostrando ${visiveis} de ${cartoes.length} edições com "${b.textContent.replace("✓ ", "")}".` : "";
  }));

  // ---------- busca de talks ----------
  const buscaTalks = document.getElementById("busca-talks");
  if (buscaTalks) {
    const itens = [...document.querySelectorAll(".lista-busca li[data-busca]")];
    itens.forEach((li) => { li.dataset.norm = normal(li.dataset.busca); });
    const temas = document.querySelectorAll(".filtro-talks button");
    const soEss = document.getElementById("so-essenciais");
    const soPend = document.getElementById("so-pendentes");
    const saida = buscaTalks.closest(".talks-ferramentas").querySelector(".busca-status");
    let tema = "";
    const filtrar = () => {
      const termos = normal(buscaTalks.value.trim()).split(/\s+/).filter(Boolean);
      let n = 0;
      itens.forEach((li) => {
        const ok = termos.every((t) => li.dataset.norm.includes(t)) && (!tema || li.dataset.tema === tema) &&
          (!soEss.checked || li.hasAttribute("data-essencial")) && (!soPend.checked || !estudado(li.dataset.id));
        li.hidden = !ok;
        if (ok) n++;
      });
      saida.textContent = n === itens.length ? "" : `${n} ${n === 1 ? "talk encontrado" : "talks encontrados"}.`;
    };
    buscaTalks.addEventListener("input", filtrar);
    soEss.addEventListener("change", filtrar);
    soPend.addEventListener("change", filtrar);
    temas.forEach((b) => b.addEventListener("click", () => {
      tema = b.dataset.tema;
      temas.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      filtrar();
    }));
    const q = new URLSearchParams(location.search).get("q");
    if (q) { buscaTalks.value = q; filtrar(); }
  }

  // ---------- busca do glossário ----------
  const busca = document.getElementById("busca");
  if (busca) {
    const termos = [...document.querySelectorAll(".termo-card")];
    const saida = document.querySelector(".busca-status");
    const soAnalogia = document.getElementById("so-analogia");
    const filtrar = () => {
      const q = normal(busca.value.trim());
      const filtro = q || soAnalogia.checked;
      let n = 0;
      termos.forEach((t) => {
        const ok = (!q || normal(t.dataset.busca).includes(q)) && (!soAnalogia.checked || t.hasAttribute("data-analogia"));
        t.hidden = !ok;
        if (ok) n++;
      });
      document.querySelectorAll(".raros").forEach((d) => {
        const algum = d.querySelector(".termo-card:not([hidden])");
        if (filtro) { d.open = !!algum; d.hidden = !algum; } else { d.hidden = false; d.open = false; }
      });
      document.querySelectorAll(".letra").forEach((s) => {
        const vazia = !s.querySelector(".termo-card:not([hidden])");
        s.hidden = vazia;
        const link = document.querySelector(`.letras a[href="#${s.id}"]`);
        if (link) link.hidden = vazia;
      });
      saida.textContent = filtro ? (n ? `${n} ${n === 1 ? "termo encontrado" : "termos encontrados"}.` : "Nenhum termo com esse nome ainda.") : "";
    };
    busca.addEventListener("input", filtrar);
    soAnalogia.addEventListener("change", filtrar);
  }

  // ---------- âncora dentro de <details> fechado (radar, termos raros): abre antes de rolar ----------
  function abrirAlvo() {
    if (!location.hash || location.hash.length < 2) return;
    let alvo;
    try { alvo = document.querySelector(location.hash); } catch (e) { return; }
    if (!alvo) return;
    let pai = alvo.parentElement;
    let abriu = false;
    while (pai) {
      if (pai.tagName === "DETAILS" && !pai.open && !pai.classList.contains("indice")) { pai.open = true; abriu = true; }
      pai = pai.parentElement;
    }
    if (abriu) requestAnimationFrame(() => alvo.scrollIntoView());
  }
  window.addEventListener("hashchange", abrirAlvo);
  abrirAlvo();
  document.addEventListener("click", (ev) => {
    const a = ev.target.closest('a[href^="#"]');
    if (a && a.getAttribute("href") === location.hash) setTimeout(abrirAlvo, 0); // mesmo hash não dispara hashchange
  });

  // ---------- edição: índice, talk atual, barra de leitura e progresso ----------
  const indice = document.getElementById("indice");
  const blocos = [...document.querySelectorAll(".video[data-n]")];
  let atual = null;
  const visivel = (b) => !b.closest("details:not([open])");
  if (indice) {
    const largo = window.matchMedia("(min-width:1100px)");
    const ajustar = () => { indice.open = largo.matches; };
    ajustar();
    largo.addEventListener?.("change", ajustar);
    // no desktop o índice já está na tela: "↑ Índice" leva o foco a ele em vez de rolar a página até o topo
    document.querySelectorAll('a[href="#indice"]').forEach((a) => a.addEventListener("click", (ev) => {
      indice.open = true;
      if (largo.matches) {
        ev.preventDefault();
        (indice.querySelector("li.atual a") || indice.querySelector("li a"))?.focus();
      }
    }));
    indice.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => { if (!largo.matches) indice.open = false; }));

    const barra = document.querySelector(".barra-leitura");
    const pos = barra?.querySelector(".bl-pos");
    const prox = barra?.querySelector(".bl-proximo");
    const marcarAtual = (b) => {
      atual = b;
      indice.querySelectorAll("li.atual").forEach((li) => { li.classList.remove("atual"); li.querySelector("a")?.removeAttribute("aria-current"); });
      if (barra) barra.hidden = !b || largo.matches;
      if (!b) return;
      const li = indice.querySelector(`li[data-id="${b.id.slice(2)}"]`);
      if (li) {
        li.classList.add("atual");
        li.querySelector("a").setAttribute("aria-current", "location");
        if (largo.matches) { // mantém o item atual visível dentro do índice
          const r = li.getBoundingClientRect(), c = indice.getBoundingClientRect();
          if (r.top < c.top + 40 || r.bottom > c.bottom - 20) indice.scrollTop += r.top - c.top - c.height / 3;
        }
      }
      if (pos) pos.textContent = `Talk ${b.dataset.n} de ${b.dataset.total}`;
      const seguinte = blocos.filter(visivel)[blocos.filter(visivel).indexOf(b) + 1];
      if (prox) prox.href = seguinte ? "#" + seguinte.id : "#fim";
    };
    if (blocos.length && "IntersectionObserver" in window) {
      const vistos = new Set();
      const obs = new IntersectionObserver((entradas) => {
        entradas.forEach((e) => (e.isIntersecting ? vistos.add(e.target) : vistos.delete(e.target)));
        marcarAtual(blocos.find((b) => vistos.has(b)) || null);
      }, { rootMargin: "-40% 0px -55% 0px" });
      blocos.forEach((b) => obs.observe(b));
    }

    const barraTopo = document.querySelector(".progresso-leitura i");
    if (barraTopo) {
      let pendente = false;
      const medir = () => {
        pendente = false;
        const total = document.documentElement.scrollHeight - innerHeight;
        barraTopo.style.width = (total > 0 ? Math.min(100, (scrollY / total) * 100) : 0) + "%";
      };
      addEventListener("scroll", () => { if (!pendente) { pendente = true; requestAnimationFrame(medir); } }, { passive: true });
      medir();
    }
  }

  // nota pessoal já escrita: deixa o campo aberto
  document.querySelectorAll("details.levo").forEach((d) => { if (ls.get("nota:" + d.dataset.levo)) d.open = true; });

  // ---------- player do YouTube na própria página (Ctrl/Cmd+clique abre no YouTube) ----------
  if (typeof HTMLDialogElement === "function") {
    let player;
    document.addEventListener("click", (ev) => {
      const a = ev.target.closest("a[data-yt]");
      if (!a || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.button !== 0) return;
      ev.preventDefault();
      if (!player) {
        player = document.createElement("dialog");
        player.className = "player";
        player.setAttribute("aria-label", "Vídeo do talk");
        player.innerHTML = '<div class="moldura"></div><div class="player-rodape"><a target="_blank" rel="noopener">Abrir no YouTube<span class="sr"> (nova aba)</span></a><button type="button" class="fechar" aria-label="Fechar vídeo">×</button></div>';
        player.querySelector(".fechar").addEventListener("click", () => player.close());
        player.addEventListener("click", (e) => { if (e.target === player) player.close(); });
        player.addEventListener("close", () => { player.querySelector(".moldura").innerHTML = ""; }); // para o vídeo
        document.body.appendChild(player);
      }
      const t = parseInt(a.dataset.t || "0", 10);
      const ifr = document.createElement("iframe");
      ifr.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(a.dataset.yt)}?start=${t}&autoplay=1&rel=0`;
      ifr.title = "Vídeo do talk no YouTube";
      ifr.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      ifr.allowFullscreen = true;
      player.querySelector(".moldura").replaceChildren(ifr);
      player.querySelector(".player-rodape a").href = a.href;
      player.showModal();
    });
  }

  // ---------- atalhos de teclado (desktop) ----------
  if (blocos.length || document.getElementById("busca") || document.getElementById("busca-talks")) {
    let ajuda;
    const abrirAjuda = () => {
      if (!ajuda) {
        ajuda = document.createElement("dialog");
        ajuda.className = "atalhos";
        ajuda.id = "atalhos";
        ajuda.setAttribute("aria-labelledby", "atalhos-titulo");
        ajuda.innerHTML = '<h2 id="atalhos-titulo">Atalhos</h2><dl>' +
          '<dt><kbd>J</kbd> <kbd>K</kbd></dt><dd>próximo e anterior talk</dd>' +
          '<dt><kbd>E</kbd></dt><dd>marcar o talk atual como estudado</dd>' +
          '<dt><kbd>V</kbd></dt><dd>assistir o talk atual</dd>' +
          '<dt><kbd>I</kbd></dt><dd>ir para o índice</dd>' +
          '<dt><kbd>/</kbd></dt><dd>buscar (em Talks e no Glossário)</dd>' +
          '<dt><kbd>?</kbd></dt><dd>esta ajuda</dd></dl><button type="button" class="fechar" aria-label="Fechar">×</button>';
        ajuda.querySelector(".fechar").addEventListener("click", () => ajuda.close());
        document.body.appendChild(ajuda);
      }
      ajuda.showModal();
    };
    document.querySelectorAll(".abrir-atalhos").forEach((a) => a.addEventListener("click", (ev) => { ev.preventDefault(); abrirAjuda(); }));
    const aviso = (txt) => {
      const t = document.createElement("div");
      t.className = "toast";
      t.setAttribute("role", "status");
      t.textContent = txt;
      document.body.appendChild(t);
      setTimeout(() => t.remove(), 1800);
    };
    // o talk atual pela geometria: o último cujo topo já passou de 40% da tela
    const blocoAtual = () => {
      const lista = blocos.filter(visivel);
      let achado = null;
      for (const b of lista) { if (b.getBoundingClientRect().top <= innerHeight * 0.4) achado = b; else break; }
      return achado && achado.getBoundingClientRect().bottom > 0 ? achado : null;
    };
    const ir = (passo) => {
      const lista = blocos.filter(visivel);
      if (!lista.length) return;
      const agora = blocoAtual();
      const i = agora ? lista.indexOf(agora) : (passo > 0 ? -1 : 0);
      const alvo = lista[Math.max(0, Math.min(lista.length - 1, i + passo))];
      alvo.scrollIntoView({ block: "start", behavior: "instant" });
      alvo.querySelector("h2")?.setAttribute("tabindex", "-1");
      alvo.querySelector("h2")?.focus({ preventScroll: true });
    };
    document.addEventListener("keydown", (ev) => {
      if (ev.metaKey || ev.ctrlKey || ev.altKey || ev.defaultPrevented) return;
      const alvo = ev.target;
      if (alvo.closest?.("input, textarea, select, [contenteditable]") || document.querySelector("dialog[open]")) return;
      const k = ev.key;
      if (k === "?") { ev.preventDefault(); abrirAjuda(); }
      else if (k === "/") {
        const campo = document.getElementById("busca") || document.getElementById("busca-talks");
        if (campo) { ev.preventDefault(); campo.focus(); campo.select(); }
      } else if (!blocos.length) return;
      else if (k === "j") { ev.preventDefault(); ir(1); }
      else if (k === "k") { ev.preventDefault(); ir(-1); }
      else if (k === "i" && indice) { ev.preventDefault(); indice.open = true; (indice.querySelector("li.atual a") || indice.querySelector("li a"))?.focus(); }
      else if (k === "e" && blocoAtual()) {
        const caixa = blocoAtual().querySelector("input[data-id]");
        if (caixa) { caixa.click(); aviso(caixa.checked ? "Marcado como estudado" : "Marcação removida"); }
      } else if (k === "v" && blocoAtual()) blocoAtual().querySelector("a.chip-link[data-yt]")?.click();
    });
  }

  // ---------- lightbox dos prints ----------
  if (typeof HTMLDialogElement === "function") {
    let dialogo;
    document.addEventListener("click", (ev) => {
      const a = ev.target.closest("a.ampliar");
      if (!a || ev.metaKey || ev.ctrlKey) return;
      ev.preventDefault();
      if (!dialogo) {
        dialogo = document.createElement("dialog");
        dialogo.className = "lightbox";
        dialogo.innerHTML = '<button type="button" aria-label="Fechar imagem">×</button><img alt=""><p></p>';
        dialogo.addEventListener("click", (e) => { if (e.target !== dialogo.querySelector("img")) dialogo.close(); });
        document.body.appendChild(dialogo);
      }
      const img = a.querySelector("img");
      dialogo.querySelector("img").src = a.href;
      dialogo.querySelector("img").alt = img?.alt || "";
      dialogo.querySelector("p").textContent = a.dataset.legenda || "";
      dialogo.showModal();
    });
  }

  // ---------- levar o progresso para outro aparelho ----------
  const exportar = document.getElementById("exportar");
  if (exportar) {
    exportar.addEventListener("click", async () => {
      const itens = ls.chaves().filter((k) => k.startsWith("estudei:")).map((k) => {
        const d = ls.get(k);
        return k.slice(8) + "." + (/^\d{4}-\d{2}-\d{2}$/.test(d || "") ? d.replace(/-/g, "") : "0");
      });
      const saida = document.querySelector(".exportar-status");
      if (!itens.length) { saida.textContent = "Você ainda não marcou nenhum talk."; return; }
      const url = location.href.split("#")[0] + "#progresso=" + itens.join(",");
      try { await navigator.clipboard.writeText(url); saida.textContent = `Link copiado com ${itens.length} talks. Abra no outro aparelho.`; }
      catch (e) { window.prompt("Copie este link e abra no outro aparelho:", url); }
    });
  }
  let avisoImportacao = "";
  if (location.hash.startsWith("#progresso=")) {
    let n = 0;
    location.hash.slice(11).split(",").forEach((par) => {
      const [id, d] = par.split(".");
      if (!/^[\w-]{11}$/.test(id || "")) return;
      const data = /^\d{8}$/.test(d || "") ? `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6)}` : "1";
      if (ls.get("estudei:" + id) === null) { ls.set("estudei:" + id, data); n++; }
    });
    history.replaceState(null, "", location.pathname + location.search);
    avisoImportacao = `Progresso importado: ${n} ${n === 1 ? "talk novo marcado" : "talks novos marcados"}.`;
  }

  atualizarProgresso();
  const aviso = document.getElementById("habito");
  if (aviso && avisoImportacao) { aviso.textContent = avisoImportacao; aviso.hidden = false; }
})();
