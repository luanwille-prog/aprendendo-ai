# Aprendendo AI

Rotina que transforma os talks do canal AI Engineer em blocos de estudo em português, publicados em GitHub Pages no estilo Quadro Anotado (`docs/guia-quadro-anotado.pdf`).

- Spec: `docs/superpowers/specs/2026-09-29-rotina-aprendizado-ai-design.md`
- Receita da rotina diária: `ROTINA.md`. Só execute quando pedirem explicitamente.
- Branch única: `claude/biblioteca`.
- Testes: `.venv/bin/pytest` (local) ou `python3 -m pytest` (nuvem).
- Nenhum modelo escreve HTML: o site sai de `scripts/montar_site.py` + `templates/`.
- `data/` é estado de produção (processados, glossário, vídeos). Não edite à mão sem necessidade.
