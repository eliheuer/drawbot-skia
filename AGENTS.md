# Agent Onboarding

This file is the durable entry point for AI agents and future maintainers
working in this repository. Keep it factual, current, and tool-agnostic.

## Project Summary

`drawbot-skia` implements the DrawBot drawing API on top of Skia. It is a Python
package and CLI, not the macOS DrawBot app. The main command is `drawbot`, and
the main import path is `drawbot_skia.drawbot`.

The fork currently focuses on:

- broad DrawBot API coverage;
- cross-platform rendering through Skia;
- visual docs/examples that can be regenerated and inspected;
- explicit documentation of compatibility limits instead of hidden behavior
  differences.

## Repository Map

- `src/drawbot_skia/__main__.py`: CLI entry point for `drawbot`.
- `src/drawbot_skia/drawbot.py`: module-level DrawBot-style namespace.
- `src/drawbot_skia/drawing.py`: main drawing state and high-level API.
- `src/drawbot_skia/document.py`: page recording and export backends.
- `src/drawbot_skia/gstate.py`: graphics/text state.
- `src/drawbot_skia/path.py`: `BezierPath` and path operations.
- `src/drawbot_skia/formattedString.py`: styled text API.
- `src/drawbot_skia/shaping.py`: HarfBuzz/font shaping support.
- `src/drawbot_skia/imageObject.py`: `ImageObject` generators, filters,
  compositing, transitions, and barcode helpers.
- `tests/`: API, runner, shaping, document, and example-render tests.
- `tests/apitests/`: script-level visual/API fixtures.
- `tests/apitests_expected_output/`: expected image/PDF/SVG outputs.
- `docs/`: local markdown docs adapted for this fork.
- `examples/`: executable docs examples plus rendered JPG previews.
- `examples/showcase/`: repo-specific examples for features this fork supports
  beyond the original upstream roadmap state.
- `API_GAP_AUDIT.md`: current parity audit and known compatibility limits.
- `.agents/`: durable task notes and templates for multi-agent handoff.

## Setup

Use an editable install for development:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[mp4]"
python -m pip install -r requirements-dev.txt
```

Equivalent `uv` setup:

```sh
uv venv
source .venv/bin/activate
uv pip install -e ".[mp4]"
uv pip install -r requirements-dev.txt
```

## Verification Commands

Run the full suite:

```sh
.venv/bin/python -m pytest -q
```

Regenerate visual docs examples:

```sh
.venv/bin/python examples/render_examples.py
```

Check the CLI:

```sh
.venv/bin/python -m drawbot_skia --help
```

Focused checks for docs/examples work:

```sh
.venv/bin/python -m pytest -q tests/test_examples.py tests/test_runner.py
```

## Development Workflow

- Prefer small, coherent commits.
- Keep generated example JPGs in sync with their `.py` sources.
- When changing CLI output behavior, update `tests/test_runner.py`.
- When changing examples or docs links, run `tests/test_examples.py`.
- When touching broad rendering behavior, run the full pytest suite.
- Do not remove existing generated fixtures unless the corresponding source
  fixture changes or the fixture is intentionally retired.
- Use `API_GAP_AUDIT.md` as the source of truth for parity caveats and open
  DrawBot behavior differences.

## Compatibility Boundaries

This project is cross-platform and does not use macOS CoreText, Core Image,
AppKit, or PDFKit.

Important implications:

- Text output is not expected to match macOS DrawBot/CoreText pixel-for-pixel.
- Many `ImageObject` methods are compatibility implementations rather than
  Core Image-identical filters.
- macOS bridge APIs such as `Variable()`, `pdfImage()`, `printImage()`,
  `FormattedString.getNSObject()`, `BezierPath.getNSBezierPath()`, and
  `BezierPath.setNSBezierPath()` intentionally raise `DrawbotError`.
- `BezierPath.traceImage()` requires external `mkbitmap` and `potrace`
  executables.

Document compatibility changes explicitly. Do not imply full pixel parity when
the implementation is intentionally approximate.

## Docs And Examples

The local docs/examples system is also a visual test surface:

- docs pages live in `docs/`;
- example scripts and previews live in `examples/<category>/`;
- previews are JPGs rendered at 2x scale by `examples/render_examples.py`;
- `tests/test_examples.py` verifies category coverage, renderability, preview
  output, and local docs links.

If adding a new docs example:

1. Add a deterministic `.py` script in the right `examples/` category.
2. Run `.venv/bin/python examples/render_examples.py`.
3. Link the generated JPG and source from the relevant markdown page.
4. Run `.venv/bin/python -m pytest -q tests/test_examples.py`.

## Agent Handoff Notes

Use `.agents/active/` for task-specific notes when work is long-running,
multi-agent, or likely to be interrupted. Start from
`.agents/active/_template.md`.

Keep task notes concise:

- current branch and cleanliness;
- exact commands already run;
- files touched;
- known blockers or caveats;
- next concrete step.

Do not create tool-specific rule directories unless explicitly requested.
