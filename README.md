# drawbot-skia

`drawbot-skia` is a Python implementation of the
[DrawBot](https://www.drawbot.com/) drawing API using
[Skia](https://skia.org/) as the rendering backend.

DrawBot is a friendly, Python-based way to make 2D graphics: posters, diagrams,
type specimens, generated images, animations, PDFs, SVGs, and quick visual
experiments. Classic DrawBot is a macOS app. This project is a package and
command-line tool that lets similar DrawBot scripts run in a normal Python
environment.

This fork focuses on broad DrawBot API coverage, visual test examples, and
cross-platform use.

## What It Does

- Runs DrawBot-style Python scripts from the command line.
- Provides a Python module you can import in your own scripts.
- Draws shapes, paths, colors, gradients, text, formatted text, and images.
- Exports PNG, JPEG, PDF, SVG, animated GIF, and MP4 output.
- Supports `BezierPath`, `FormattedString`, variable fonts, HarfBuzz shaping,
  many `ImageObject` filters, barcode generators, and visual docs examples.
- Includes local [`docs/`](docs/) and [`examples/`](examples/) directories with
  rendered JPG previews that double as visual test fixtures.

The current API audit is tracked in [`API_GAP_AUDIT.md`](API_GAP_AUDIT.md).

## Quick Start

Install the package, then run a DrawBot script:

```sh
drawbot poster.py poster.png
```

A tiny script looks like this:

```python
size(600, 400)

fill(0.95)
rect(0, 0, width(), height())

fill(0.1, 0.2, 0.35)
fontSize(64)
text("Hello Skia", (60, 190))

fill(0.95, 0.35, 0.15)
oval(420, 120, 110, 110)
```

Save it as `poster.py`, then render it:

```sh
drawbot poster.py poster.png
```

The CLI behaves like running a script in the DrawBot app: the drawing API names
are injected into the script namespace, so the script does not need imports.

## Installation

### Install This Fork From The CLI

To use this fork as your installed `drawbot-skia` package:

```sh
python -m pip install --upgrade "drawbot-skia @ git+https://github.com/eliheuer/drawbot-skia.git"
```

That installs the package and the `drawbot` command.

If you already installed the upstream package from PyPI and want this fork
instead, reinstall from the GitHub URL above. The package name and import path
are still `drawbot-skia` / `drawbot_skia`, so existing scripts that already use
`drawbot_skia` should keep the same imports.

### Install With `uv`

For a local project:

```sh
uv venv
source .venv/bin/activate
uv pip install "drawbot-skia @ git+https://github.com/eliheuer/drawbot-skia.git"
```

Run the CLI:

```sh
uv run drawbot poster.py poster.png
```

For development from a clone:

```sh
git clone https://github.com/eliheuer/drawbot-skia.git
cd drawbot-skia
uv venv
source .venv/bin/activate
uv pip install -e ".[mp4]"
uv pip install -r requirements-dev.txt
```

Run tests:

```sh
uv run pytest -q
```

### Install With A Regular `venv`

For a local project:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "drawbot-skia @ git+https://github.com/eliheuer/drawbot-skia.git"
```

Run the CLI:

```sh
drawbot poster.py poster.png
```

For development from a clone:

```sh
git clone https://github.com/eliheuer/drawbot-skia.git
cd drawbot-skia
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[mp4]"
python -m pip install -r requirements-dev.txt
```

Run tests:

```sh
python -m pytest -q
```

Windows note: `skia-python` requires 64-bit Python, so use a 64-bit Python
installer.

## Using It From Python

You can write scripts with explicit imports:

```python
from drawbot_skia.drawbot import *

size(400, 300)
fill(1, 0, 0)
oval(100, 75, 200, 150)
saveImage("oval.png")
```

Or use a module alias:

```python
import drawbot_skia.drawbot as db

db.size(400, 300)
db.fill(0.1, 0.2, 0.4)
db.rect(40, 40, 320, 220)
db.saveImage("rectangle.png")
```

Use the command-line runner when you want your script to look like a DrawBot app
script with no imports:

```sh
drawbot script.py output.png
```

You can pass more than one output file:

```sh
drawbot script.py output.png output.pdf output.svg
```

Raster outputs can be rendered at a higher pixel scale:

```sh
drawbot --pixelScale 2 script.py output.jpg
```

## Using It As A Replacement

### Replacing Upstream `drawbot-skia`

This fork keeps the same package name, CLI command, and import path:

- package: `drawbot-skia`
- import path: `drawbot_skia`
- CLI command: `drawbot`

If a script already uses upstream `drawbot-skia`, install this fork from GitHub
and keep the script as-is:

```python
from drawbot_skia.drawbot import *
```

Then run:

```sh
drawbot script.py output.png
```

### Porting A DrawBot App Script

Most simple DrawBot app scripts can be run directly with the CLI:

```sh
drawbot my-drawbot-script.py output.pdf
```

If you want to run the script with plain Python instead of the CLI, add this at
the top:

```python
from drawbot_skia.drawbot import *
```

Then make sure the script calls `saveImage(...)`:

```python
saveImage("output.pdf")
```

Some macOS DrawBot app APIs are intentionally not available in this
cross-platform package. See [Compatibility Notes](#compatibility-notes).

## Project Architecture

The package is organized around a small set of core layers:

- `drawbot_skia.drawbot`: a module-level DrawBot-style namespace for scripts.
- `Drawing`: the main stateful drawing object. It owns the current page,
  drawing state, text state, transforms, and export calls.
- `runner`: builds the script namespace used by the `drawbot` CLI.
- `document`: records Skia pictures and exports them as PNG, JPEG, PDF, SVG,
  GIF, or MP4.
- `gstate`: stores fill, stroke, shadow, blend mode, text, and transform state.
- `path`: implements `BezierPath` and path operations.
- `formattedString`: implements styled text runs.
- `shaping` and `segmenting`: handle Unicode text shaping, bidi behavior, and
  text segmentation using HarfBuzz and related libraries.
- `imageObject`: implements DrawBot-style `ImageObject` generators, filters,
  compositing, transitions, and barcode helpers.

At a high level:

1. A script calls DrawBot-style functions such as `rect()`, `text()`, or
   `image()`.
2. Those calls update a `Drawing` object and draw into a Skia recording canvas.
3. Each page is stored as a Skia picture.
4. `saveImage()` or the CLI exports the recorded pages to the requested format.

## Documentation And Visual Examples

Local docs live in [`docs/`](docs/). Local examples live in
[`examples/`](examples/). The examples are grouped after the main DrawBot
documentation categories:

- Shapes
- Colors
- Canvas
- Text
- Images
- Variables
- Quick Reference

The extra `examples/showcase/` directory shows features this fork supports that
were missing or incomplete in the original upstream roadmap.

Regenerate the example previews with the default 2x pixel scale:

```sh
.venv/bin/python examples/render_examples.py
```

The docs completion audit is in [`docs/completion-audit.md`](docs/completion-audit.md).

## Development

Clone the repo, install it in editable mode, and run tests:

```sh
git clone https://github.com/eliheuer/drawbot-skia.git
cd drawbot-skia
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[mp4]"
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Regenerate visual examples:

```sh
.venv/bin/python examples/render_examples.py
```

## Roadmap Status

The original roadmap items are now broadly implemented in this fork:

- basic shapes and colors
- `BezierPath`
- transformations
- text and `textBox()`
- variable fonts
- HarfBuzz shaping
- OpenType features
- PNG, JPEG, PDF, SVG, MP4, and animated GIF export
- `FormattedString`
- many `ImageObject` APIs
- static DrawBot API method coverage, with behavior caveats below

The detailed parity status is tracked in [`API_GAP_AUDIT.md`](API_GAP_AUDIT.md).

## Compatibility Notes

This project is cross-platform and Skia-backed. It is not the macOS DrawBot app,
and it does not use CoreText, Core Image, AppKit, or PDFKit internally.

Important differences:

- Text layout and shaping are implemented in this package using Skia,
  HarfBuzz, FontTools, and related libraries. `textBox()` and
  `FormattedString` are available, but output should not be expected to match
  macOS DrawBot/CoreText pixel-for-pixel.
- Many `ImageObject` methods are Pillow-backed compatibility implementations
  rather than Core Image-equivalent filters. They are useful and tested, but
  exact Core Image pixel parity should be treated as method-by-method follow-up
  work.
- macOS bridge APIs are intentionally out of scope for this package. These names
  exist as explicit compatibility stubs and raise `DrawbotError`: `Variable()`,
  `pdfImage()`, `printImage()`, `FormattedString.getNSObject()`,
  `BezierPath.getNSBezierPath()`, and `BezierPath.setNSBezierPath()`.
- `BezierPath.traceImage()` follows DrawBot's external-tool model. It requires
  both `mkbitmap` and `potrace` on `PATH`. On macOS, install them with
  `brew install potrace`. On Debian/Ubuntu Linux, install them with
  `apt install potrace`.

Some improvements specific to this fork include focused `ImageObject` drawing,
barcode generators, alpha-aware mask behavior, broader transition/distortion
approximations, link annotations for SVG/PDF, and radial gradient parity for
DrawBot's radius and point controls.

## License

This project uses the Apache License 2.0. See [`LICENSE.txt`](LICENSE.txt).
