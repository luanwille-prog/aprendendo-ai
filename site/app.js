(() => {
  const ler = (k) => { try { return localStorage.getItem(k) === "1"; } catch (e) { return false; } };
  const guardar = (k, v) => { try { v ? localStorage.setItem(k, "1") : localStorage.removeItem(k); } catch (e) {} };
  let temaAtivo = "";

  function aplicarFiltro(raiz = document) {
    raiz.querySelectorAll(".video").forEach((v) => { v.hidden = temaAtivo !== "" && v.dataset.tema !== temaAtivo; });
  }

  function preparar(raiz) {
    raiz.querySelectorAll("input[data-id]").forEach((caixa) => {
      const bloco = caixa.closest(".video");
      caixa.checked = ler("estudei:" + caixa.dataset.id);
      bloco?.classList.toggle("feito", caixa.checked);
      caixa.addEventListener("change", () => {
        guardar("estudei:" + caixa.dataset.id, caixa.checked);
        bloco?.classList.toggle("feito", caixa.checked);
      });
    });
    aplicarFiltro(raiz);
  }

  const carregamentos = new WeakMap();
  function carregar(det) {
    if (!carregamentos.has(det)) {
      const alvo = det.querySelector(".conteudo");
      alvo.textContent = "Carregando…";
      const p = fetch(det.dataset.src)
        .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.text(); })
        .then((html) => { alvo.innerHTML = html; preparar(alvo); })
        .catch(() => {
          carregamentos.delete(det);
          alvo.textContent = "Não consegui carregar esta edição. Feche e abra de novo.";
        });
      carregamentos.set(det, p);
    }
    return carregamentos.get(det);
  }

  document.querySelectorAll("details.arquivo").forEach((d) => d.addEventListener("toggle", () => { if (d.open) carregar(d); }));

  document.querySelectorAll(".filtro button").forEach((b) => b.addEventListener("click", () => {
    temaAtivo = b.dataset.tema;
    document.querySelectorAll(".filtro button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    aplicarFiltro();
  }));

  document.addEventListener("click", async (ev) => {
    const link = ev.target.closest("a[data-edicao]");
    if (!link || document.querySelector(link.getAttribute("href"))) return;
    const det = document.querySelector(`details.arquivo[data-src="dias/${link.dataset.edicao}.html"]`);
    if (!det) return;
    ev.preventDefault();
    det.open = true;
    await carregar(det);
    const suave = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.querySelector(link.getAttribute("href"))?.scrollIntoView({ behavior: suave ? "smooth" : "auto" });
  });

  preparar(document);
})();
