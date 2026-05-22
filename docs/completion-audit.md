# Completion audit

This audit records the evidence that the local DrawBot docs/examples goal has
been satisfied for this repository.

## Requirements

- Create a `docs/` directory.
- Create an `examples/` directory.
- Mirror the main DrawBot documentation categories: Shapes, Colors, Canvas,
  Text, Images, Variables, and Quick Reference.
- Store example Python source and rendered image previews together in category
  subdirectories.
- Use markdown docs that reference the local rendered images.
- Add an extra repo-specific examples category for features this fork supports
  beyond the upstream roadmap state.
- Make the examples useful as visual tests for the port.

## Evidence

- `docs/` contains markdown pages for all requested categories, plus source map,
  coverage notes, and this audit.
- `examples/` contains category directories named after the requested docs
  categories: `shapes`, `colors`, `canvas`, `text`, `images`, `variables`, and
  `quick_reference`.
- `examples/showcase/` is the additional repo-specific category.
- Each example category contains Python source and rendered JPG previews.
- `examples/render_examples.py` regenerates previews at 2x pixel scale by
  default.
- `tests/test_examples.py` verifies that category directories exist, example
  source files render, preview images are written, and docs links resolve.
- `tests/test_runner.py` verifies CLI `--pixelScale` raster output support.

## Verification

Run from the repository root:

```sh
.venv/bin/python examples/render_examples.py
.venv/bin/python -m pytest -q
```

The DrawBot website remains the source of truth for exact macOS DrawBot
behavior. These local pages are adapted to the cross-platform `drawbot-skia`
port and use executable local examples rather than verbatim upstream docs.
