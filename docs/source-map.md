# DrawBot source map

This page maps the official DrawBot documentation categories to local markdown
pages and visual fixtures. The source pages on drawbot.com are the reference
for category structure; these local pages are adapted for this cross-platform
port and use rendered examples from this repository.

| Official category | Local docs | Local examples |
| --- | --- | --- |
| Shapes | [shapes.md](shapes.md) | `examples/shapes/` |
| Colors | [colors.md](colors.md) | `examples/colors/` |
| Canvas | [canvas.md](canvas.md) | `examples/canvas/` |
| Text | [text.md](text.md) | `examples/text/` |
| Images | [images.md](images.md) | `examples/images/` |
| Variables | [variables.md](variables.md) | `examples/variables/` |
| Quick Reference | [quick-reference.md](quick-reference.md) | `examples/quick_reference/` |
| Fork-specific showcase | [port-showcase.md](port-showcase.md) | `examples/showcase/` |

## Subtopic checklist

| Area | Covered locally | Still expanding |
| --- | --- | --- |
| Shapes | primitives, paths, path properties, clipping | path boolean operations, text-to-path, tracing |
| Colors | fill, stroke, CMYK, gradients, opacity, shadows, blend modes | color spaces and overprint-specific behavior |
| Canvas | page size, transforms, state stack, multipage output, export targets | animation timing and format-specific export docs |
| Text | point text, text boxes, formatting, line metrics, variable font axes | full OpenType feature matrix and font query examples |
| Images | drawing, properties, focused drawing, generators, filters | transition, distortion, tiling, and segmentation groups |
| Variables | deterministic Python variables and parameter sweeps | macOS `Variable()` UI remains out of scope |
| Quick Reference | broad visual API overview | full function-by-function local quick reference |
| Showcase | roadmap features, alpha-aware masks, barcode generators | shaping, path operations, animation, and more ImageObject parity wins |
