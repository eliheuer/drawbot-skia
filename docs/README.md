# DrawBot documentation and visual examples

These pages are an adapted companion to the official
[DrawBot documentation](https://www.drawbot.com/). They are organized around
the same top-level example categories, but the examples live in this repository
and are rendered by `drawbot-skia` so they can double as visual parity fixtures.

## Categories

- [Shapes](shapes.md)
- [Colors](colors.md)
- [Canvas](canvas.md)
- [Text](text.md)
- [Images](images.md)
- [Variables](variables.md)
- [Quick Reference](quick-reference.md)
- [Port showcase](port-showcase.md)
- [DrawBot source map](source-map.md)
- [Coverage notes](coverage-notes.md)
- [Completion audit](completion-audit.md)

Regenerate preview images with the default 2x pixel scale:

```sh
.venv/bin/python examples/render_examples.py
```

The official DrawBot pages remain the source of truth for the macOS DrawBot
application. These docs describe what this port can render and where intentional
cross-platform limits remain.
