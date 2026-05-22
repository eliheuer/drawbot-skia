[![Run tests](https://github.com/justvanrossum/drawbot-skia/workflows/Run%20tests/badge.svg)](https://github.com/justvanrossum/drawbot-skia/actions)

# drawbot-skia

A Python package implementing the [DrawBot](https://www.drawbot.com) drawing API using [Skia](https://skia.org/) as a backend.

Work in progress!

## Roadmap

1. Get basic shapes working ✅
1. Get basic colors working ✅
1. Get minimal `BezierPath` object working ✅
1. Get transformations working ✅
1. Get single-line, single style `text()` working ✅
1. Get Variable Fonts working ✅
1. Get HarfBuzz shaping working ✅
1. Get OpenType features working ✅
1. Get PNG, JPEG image export working ✅
1. Get PDF export working ✅
1. Get MP4 export working ✅
1. Get SVG export working ✅
1. Get Animated GIF export working ✅
1. Get multi-line, single style `text()` working ✅
1. Get `FormattedString` working ✅
1. Get multi-style `text()` working ✅
1. Get remaining `BezierPath` methods working ✅
1. Get many-things-I-forgot-to-mention working ✅ _(static API coverage; behavior caveats below)_
1. ...
1. `textBox()` ✅ _(implemented; not CoreText-identical)_
1. Fill further gaps in DrawBot API ✅ _(static method-name coverage; behavior caveats below)_

The current API audit is tracked in [`API_GAP_AUDIT.md`](API_GAP_AUDIT.md).

## Vision

This project is purely a Python package that implements (part of) the DrawBot drawing API. Using Skia ([skia-python](https://github.com/kyamagu/skia-python)) ensures this can be done in a cross-platform way.

A DrawBot-like cross-platform application shell can be developed, but that would be a separate project. Looking forward to the `drawbot-qt`, `drawbot-wx`, `drawbot-win` or any `drawbot-*` projects of the future!

## Compatibility caveats

Some parts of the DrawBot API will be hard or impractical to duplicate.

Skia has only low level support for text, so Unicode processing, line wrapping, hyphenation, and shaping are implemented in this package rather than delegated to CoreText. `textBox()` and `FormattedString` are available, but output should not be expected to match macOS DrawBot/CoreText pixel-for-pixel.

Generally, 100% text compatibility with DrawBot should not be top priority, as matching CoreText behavior will be a huge challenge.

The `ImageObject` API in DrawBot relies heavily on Core Image. This fork exposes the audited public `ImageObject` method names, but many filters are Pillow-backed compatibility implementations rather than Core Image-equivalent behavior. In particular:

- `aztecCodeGenerator()` uses `aztec-code-generator` for standards-compliant Aztec output; `QRCodeGenerator()` produces standards-compliant byte-mode QR output for messages that fit QR versions 1-4; `PDF417BarcodeGenerator()` uses `pdf417gen` for standards-compliant PDF417 output; `code128BarcodeGenerator()` produces standards-compliant Code 128 Set B output for text input;
- CIE Lab conversion and Delta E are implemented with sRGB/D65 color math; KMeans returns a one-dimensional palette image with alpha weights, palettize/paletteCentroid use color-distance assignment, and spotColor applies contrast-aware color-range replacement. Swipe/copy-machine transitions respect extent, color, opacity, angle, width, and time; disintegrate transitions use mask-threshold timing and shadow parameters; ripple transitions use shading-image displacement, extent, scale, width, center, and time; mod transitions use radius, angle, compression, center, and time; accordion transitions use fold count, fold shadow, bottom height, and time; page-curl transitions use target/backside images, shading, extent, angle, radius, time, and shadow parameters. Nine-part stretch/tile filters preserve breakpoint-defined edge and corner regions while expanding the center regions. `bokehBlur()` uses an aperture kernel with radius, ring amount, ring size, and softness controls. `spotLight()` uses `lightPointsAt` as the beam target and alpha-masks areas outside the highlight. Other transition details remain approximations. Saliency, segmentation, material, lighting, and advanced distortion filters are still approximations;
- exact pixel parity with Core Image should be treated as follow-up work on a method-by-method basis.

The macOS application/PDFKit bridge APIs are intentionally out of scope for drawbot-skia's cross-platform package target. Their method names exist only as explicit compatibility stubs and raise `DrawbotError`: `Variable()`, `pdfImage()`, `printImage()`, `FormattedString.getNSObject()`, `BezierPath.getNSBezierPath()`, and `BezierPath.setNSBezierPath()`.

Link annotations are supported for SVG and PDF output. PDF annotations are added by post-processing Skia's emitted PDF because skia-python does not expose PDF annotation hooks directly.

`BezierPath.traceImage()` follows DrawBot's external-tool model. It requires both `mkbitmap` and `potrace` on `PATH`; if either executable is missing it raises `DrawbotError`. On macOS, install them with `brew install potrace`. On Debian/Ubuntu Linux, install them with `apt install potrace`. They are optional system dependencies, not Python package dependencies.

## Strategy

So far no existing DrawBot code has been reused. Perhaps that small snippets will be copied, perhaps a part of the test suite will be adapted. Other than that I want this to be an independent project, and would like to use Skia’s powers to maximum effect, keeping efficiency and performance in mind. DrawBot's ties to macOS are so strong that it makes platform-neutral code reuse virtually impossible.

Potentially, some higher level code could be shared (for example, drawing code that uses lower level primitives), but that will have to been seen later.

## Install

The quickest way to install the latest release is with pip:

`pip install drawbot-skia`

_Note for Windows: skia-python is only supported for the 64-bit version of Python, so that goes for drawbot-skia as well, so make sure you use one of the x86-64 Python installers._

If you want to see the source code and possibly contribute: clone the repo, and do `pip install -e .` in the root directory.

## Usage

To adapt a DrawBot script to `drawbot-skia` you can do a couple of things:

- Add `from drawbot_skia.drawbot import *` at the top of your script
- Or `import drawbot_skia.drawbot as db` if that's your preferred style

Or you can use the `drawbot` runner tool from the command line:

- `drawbot mydrawbotscript.py output.png`

With the `drawbot` runner tool, you won't need any Drawbot import in the script, nor do you need a `saveImage(...)` to export results. It pretty much behaves as if you hit "Run" in the classic Drawbot application.
