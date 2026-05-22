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

## Documentation and examples

The local [`docs/`](docs/) and [`examples/`](examples/) directories provide a
DrawBot-style documentation scaffold with rendered visual fixtures. The examples
are grouped after the main categories on drawbot.com, and `examples/showcase/`
is reserved for features that this fork supports beyond the original upstream
roadmap state.

Regenerate the example previews with:

```sh
.venv/bin/python examples/render_examples.py
```

## Vision

This project is purely a Python package that implements (part of) the DrawBot drawing API. Using Skia ([skia-python](https://github.com/kyamagu/skia-python)) ensures this can be done in a cross-platform way.

A DrawBot-like cross-platform application shell can be developed, but that would be a separate project. Looking forward to the `drawbot-qt`, `drawbot-wx`, `drawbot-win` or any `drawbot-*` projects of the future!

## Compatibility caveats

Some parts of the DrawBot API will be hard or impractical to duplicate.

Skia has only low level support for text, so Unicode processing, line wrapping, hyphenation, and shaping are implemented in this package rather than delegated to CoreText. `textBox()` and `FormattedString` are available, rectangular BezierPath text boxes are accepted, and `BezierPath.textBox()` can convert wrapped plain or formatted text into path outlines, but output should not be expected to match macOS DrawBot/CoreText pixel-for-pixel.

Generally, 100% text compatibility with DrawBot should not be top priority, as matching CoreText behavior will be a huge challenge.

The `ImageObject` API in DrawBot relies heavily on Core Image. This fork exposes the audited public `ImageObject` method names, but many filters are Pillow-backed compatibility implementations rather than Core Image-equivalent behavior. In particular:

- `ImageObject` supports focused drawing with `with im:`, `lockFocus()`, and `unlockFocus()`, rendering module-level drawing commands into the image object while restoring the surrounding drawing state;
- `aztecCodeGenerator()` uses `aztec-code-generator` for standards-compliant Aztec output; `checkerboardGenerator()` and `stripesGenerator()` use sharpness to soften pattern boundaries; `QRCodeGenerator()` produces standards-compliant byte-mode QR output for messages that fit QR versions 1-4; `PDF417BarcodeGenerator()` uses `pdf417gen` for standards-compliant PDF417 output, with advanced compaction/style option parity tracked in [#13](https://github.com/eliheuer/drawbot-skia/issues/13); `code128BarcodeGenerator()` produces standards-compliant Code 128 Set B output for text input;
- `hueAdjust()` interprets angle values as radians and preserves exact no-op behavior for zero and full-turn angles. CIE Lab conversion and Delta E are implemented with sRGB/D65 color math; KMeans returns a one-dimensional palette image with alpha weights, uses `passes` for iterative refinement, and uses Lab-space distance when `perceptual=True`; palettize/paletteCentroid use color-distance assignment, and spotColor applies contrast-aware color-range replacement. Swipe/copy-machine transitions respect extent, color, opacity, radians-based angle, width, and time; flash transitions respect extent, color, time, fade threshold, and striation parameters; disintegrate transitions use mask-threshold timing and shadow parameters; ripple transitions use shading-image displacement, extent, scale, width, center, and time; mod transitions use radius, radians-based angle, compression, center, and time; accordion transitions use fold count, fold shadow, bottom height, and time; page-curl transitions use target/backside images, shading, extent, radians-based angle, radius, time, and shadow parameters. Transition approximations preserve the source image exactly at `time=0` and the target image exactly at `time=1`. `affineTile()` applies affine sampling with wraparound tiling. `bumpDistortionLinear()` uses radians-based angle for the linear bump direction, and `circularWrap()`, `twirlDistortion()`, and `vortexDistortion()` treat all angle values as radians without degree fallback. `displacementDistortion()` uses red and green channels for independent x/y displacement. `droste()` uses inset points, strands, periodicity, rotation, and zoom for recursive inset composition. `glassDistortion()` samples the texture relative to the supplied center. `lightTunnel()` uses center, radius, and radians-based rotation for radial tunnel warping. `perspectiveCorrection()` respects crop=False by preserving the expanded transform canvas and offset. `keystoneCorrectionCombined()` scales supplied corner correction by focal length, and `perspectiveRotate()` projects radians-based pitch/yaw/roll corners through focal length before transforming the image. `pixellate()` anchors the pixel grid on the supplied center, and `pointillize()` anchors its dot grid on the supplied center. `stretchCrop()` uses crop amount to interpolate between stretching and aspect-crop fitting, and uses center stretch amount to control the resized center band. Nine-part stretch/tile filters preserve breakpoint-defined edge and corner regions while expanding the center regions. Kaleidoscope and reflected/rotated tile filters use radians-based angles and their center/point argument as the rotation pivot, `triangleKaleidoscope()` uses size for the sampled triangular span and decay for repeated wedge brightness, reflected/rotated tile filters use width to seed the repeated tile source, fourfold tile filters use acute angle for the second tile vector, and translated/parallelogram tile filters use center as a phase or reflection pivot. `bloom()` and `gloom()` preserve source alpha while applying their glow colors. `colorMonochrome()` and `whitePointAdjust()` tint RGB while preserving source alpha. Photo-effect filters use `extrapolate` to strengthen their existing color/contrast curve. `bokehBlur()` treats zero radius as a no-op and uses an aperture kernel with radius, ring amount, ring size, and softness controls for positive radii. `cannyEdgeDetector()` uses low/high thresholds with hysteresis passes and Lab-lightness edge input when `perceptual=True`. Screen and halftone filters interpret angle values as radians; `CMYKHalftone()` uses CMYK separations with GCR/UCR controls before recomposing subtractive dot screens. `depthOfField()` uses the point0/point1 focus line to preserve nearby detail and blur farther pixels. `documentEnhancer()` treats amount zero as a no-op and blends stronger enhancement as amount increases. `edges()` and `edgeWork()` preserve alpha while emphasizing edge content. `guidedFilter()` uses radius-controlled smoothing and guide-edge preservation controlled by epsilon. `highlightShadowAdjust()` uses radius-controlled luminance context while preserving alpha. `lenticularHaloGenerator()` uses halo overlap, striation strength/contrast, and time. `lineOverlay()` uses noise reduction, sharpness, and contrast controls before thresholding edge detail. `maskedVariableBlur()` uses mask luminance to select local blur radius. `morphologyMaximum()` and `morphologyMinimum()` treat zero radius as a no-op, `morphologyGradient()` allows zero radius to produce a zero-difference image, and rectangle morphology uses separate width and height kernels. `motionBlur()` treats zero radius as a no-op and uses radius plus radians-based angle for explicit directional sampling. `noiseReduction()` treats zero noise and sharpness as a no-op and applies denoising and sharpening independently. `personSegmentation()` uses `qualityLevel` to control matte thresholding and softening. `saliencyMapFilter()` emits a grayscale local-contrast saliency map. `shadedMaterial()` treats the shading image as a height field for relief lighting controlled by scale. `sharpenLuminance()` sharpens the luminance plane while preserving original chroma and alpha. `unsharpMask()` sharpens RGB content while preserving source alpha. `vignetteEffect()` darkens RGB content while preserving source alpha. `spotLight()` uses `lightPointsAt` as the beam target and alpha-masks areas outside the highlight. `starShineGenerator()` uses cross opacity and epsilon controls for ray intensity and glow softness. `sunbeamsGenerator()` uses striation radius, strength, contrast, and time when generating ray patterns. `zoomBlur()` treats zero amount as a no-op and uses the provided center as the zoom anchor. Other transition details remain approximations. Saliency, segmentation, material, lighting, and advanced distortion filters are still approximations;
- exact pixel parity with Core Image should be treated as follow-up work on a method-by-method basis.

The macOS application/PDFKit bridge APIs are intentionally out of scope for drawbot-skia's cross-platform package target; tracked in [#17](https://github.com/eliheuer/drawbot-skia/issues/17). Their method names exist only as explicit compatibility stubs and raise `DrawbotError`: `Variable()`, `pdfImage()`, `printImage()`, `FormattedString.getNSObject()`, `BezierPath.getNSBezierPath()`, and `BezierPath.setNSBezierPath()`.

Link annotations are supported for SVG and PDF output. PDF annotations are added by post-processing Skia's emitted PDF because skia-python does not expose PDF annotation hooks directly.

`radialGradient()` and `cmykRadialGradient()` support DrawBot's `startRadius`, `endRadius`, `startPoint`, and `endPoint` controls through Skia radial/two-point conical shaders.

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
