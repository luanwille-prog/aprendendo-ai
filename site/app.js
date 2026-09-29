(() => {
  const ler = (k) => { try { return localStorage.getItem(k) === "1"; } catch (e) { return false; } };
  const guardar = (k, v) => { try { v ? localStorage.setItem(k, "1") : localStorage.removeItem(k); } catch (e) {} };

  function atualizarProgresso() {
    document.querySelectorAll(".progresso[data-ids]").forEach((el) => {
      const ids = el.dataset.ids.split(" ").filter(Boolean);
      if (!ids.length) return;
      const feitos = ids.filter((id) => ler("estudei:" + id)).length;
      const pct = Math.round((feitos / ids.length) * 100);
      el.innerHTML = `<span class="barra" aria-hidden="true"><i style="width:${pct}%"></i></span><span>${feitos} de ${ids.length} estudados</span>`;
    });
  }

  document.querySelectorAll("input[data-id]").forEach((caixa) => {
    const bloco = caixa.closest(".video");
    caixa.checked = ler("estudei:" + caixa.dataset.id);
    bloco?.classList.toggle("feito", caixa.checked);
    caixa.addEventListener("change", () => {
      guardar("estudei:" + caixa.dataset.id, caixa.checked);
      bloco?.classList.toggle("feito", caixa.checked);
      atualizarProgresso();
    });
  });

  document.querySelectorAll(".filtro button").forEach((b) => b.addEventListener("click", () => {
    const tema = b.dataset.tema;
    document.querySelectorAll(".filtro button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    document.querySelectorAll(".video").forEach((v) => { v.hidden = tema !== "" && v.dataset.tema !== tema; });
  }));

  atualizarProgresso();
})();
