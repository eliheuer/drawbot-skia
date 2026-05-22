# DrawBot visual examples

This directory contains DrawBot-style scripts plus rendered JPG previews. The
scripts are grouped after the main example categories on
[drawbot.com](https://www.drawbot.com/): shapes, colors, canvas, text, images,
variables, and quick reference.

The `showcase/` directory is specific to this fork. It demonstrates features
called out in the upstream `drawbot-skia` roadmap and compatibility notes that
are now implemented here.

Regenerate all previews from the repository root. Previews are rendered at 2x
pixel scale by default so the markdown docs have enough resolution for visual
inspection.

```sh
.venv/bin/python examples/render_examples.py
```

Each example should remain a small visual fixture: easy to read, deterministic,
and narrow enough that a changed output points to a specific API family.
