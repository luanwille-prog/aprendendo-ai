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
    const cont = document.getElementById("continuar");
    if (cont) {
      let talks = [];
      try { talks = JSON.parse(cont.dataset.talks || "[]"); } catch (e) {}
      const alguem = talks.some((t) => estudado(t.id));
      const proximo = talks.find((t) => !estudado(t.id));
      cont.hidden = !alguem || !proximo;
      if (proximo) {
        cont.href = proximo.href;
        cont.textContent = "Continuar: " + proximo.titulo;
      }
    }
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
