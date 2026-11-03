(() => {
  const ler = (k) => { try { return localStorage.getItem(k) === "1"; } catch (e) { return false; } };
  const guardar = (k, v) => { try { v ? localStorage.setItem(k, "1") : localStorage.removeItem(k); } catch (e) {} };
  const sessao = new Set(); // vale mesmo sem localStorage
  const estudado = (id) => sessao.has(id) || ler("estudei:" + id);

  function atualizarProgresso() {
    document.querySelectorAll(".progresso[data-ids]").forEach((el) => {
      const ids = el.dataset.ids.split(" ").filter(Boolean);
      if (!ids.length) return;
      const feitos = ids.filter(estudado).length;
      const pct = Math.round((feitos / ids.length) * 100);
      el.innerHTML = `<span class="barra" aria-hidden="true"><i style="width:${pct}%"></i></span><span>${feitos} de ${ids.length} estudados</span>`;
    });
    document.querySelectorAll(".indice li[data-id]").forEach((li) => li.classList.toggle("feito", estudado(li.dataset.id)));
    atualizarContinuar();
  }

  // "Continuar": retoma a edição mais recente que ficou pela metade, não a primeira com talk pendente.
  // As outras edições começadas aparecem como pendências, com opção de arquivar sem culpa.
  const arquivada = (e) => { try { return localStorage.getItem("arquivei:" + e) === "1"; } catch (x) { return false; } };
  function atualizarContinuar() {
    const cont = document.getElementById("continuar");
    if (!cont) return;
    let eds = [];
    try { eds = JSON.parse(cont.dataset.talks || "[]"); } catch (e) {}
    const resumo = eds.map((ed) => ({ ...ed, feitos: ed.t.filter((t) => estudado(t.id)).length }));
    const andamento = resumo.filter((ed) => ed.feitos > 0 && ed.feitos < ed.t.length && !arquivada(ed.e));
    const alguem = resumo.some((ed) => ed.feitos > 0);
    // em andamento primeiro; senão, a edição mais nova ainda não começada
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
    caixa.innerHTML = outras.length ? `<p class="pendencias-titulo">Ficou pela metade</p><ul>${outras.map((ed) => {
      const falta = ed.t.length - ed.feitos;
      const prox = ed.t.find((t) => !estudado(t.id));
      return `<li><a href="${prox.h}">${falta} ${falta === 1 ? "talk" : "talks"} de ${ed.d}</a> <button type="button" class="arquivar" data-edicao="${ed.e}">Arquivar<span class="sr"> a edição de ${ed.d}</span></button></li>`;
    }).join("")}</ul>` : "";
    caixa.querySelectorAll(".arquivar").forEach((b) => b.addEventListener("click", () => {
      try { localStorage.setItem("arquivei:" + b.dataset.edicao, "1"); } catch (x) {}
      atualizarContinuar();
    }));
  }

  document.querySelectorAll("input[data-id]").forEach((caixa) => {
    const id = caixa.dataset.id;
    const bloco = caixa.closest(".video");
    caixa.checked = estudado(id);
    bloco?.classList.toggle("feito", caixa.checked);
    caixa.addEventListener("change", () => {
      caixa.checked ? sessao.add(id) : sessao.delete(id);
      guardar("estudei:" + id, caixa.checked);
      bloco?.classList.toggle("feito", caixa.checked);
      atualizarProgresso();
    });
  });

  const botoes = document.querySelectorAll(".filtro button");
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
    if (status) status.textContent = tema ? `Mostrando ${visiveis} de ${cartoes.length} edições com "${b.textContent}".` : "";
  }));

  const busca = document.getElementById("busca");
  if (busca) {
    const termos = [...document.querySelectorAll(".termo-card")];
    const saida = document.querySelector(".busca-status");
    const normal = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    busca.addEventListener("input", () => {
      const q = normal(busca.value.trim());
      let n = 0;
      termos.forEach((t) => { const ok = !q || normal(t.dataset.busca).includes(q); t.hidden = !ok; if (ok) n++; });
      document.querySelectorAll(".letra").forEach((s) => { s.hidden = !s.querySelector(".termo-card:not([hidden])"); });
      saida.textContent = q ? (n ? `${n} ${n === 1 ? "termo encontrado" : "termos encontrados"}.` : "Nenhum termo com esse nome ainda.") : "";
    });
  }

  atualizarProgresso();
})();
