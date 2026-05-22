# DrawBot API Gap Audit

Date: 2026-05-22

## Scope

This audit compares the current fork against:

- `justvanrossum/drawbot-skia` upstream README roadmap at `upstream/main` commit `582e2c5067234ee6c8c72bff524e8efb7cab51d4`.
- `typemytype/drawbot` public drawing API at commit `71cff6df68fff1fafd5a542ab58157b30e377bd1`.
- Current fork baseline commit `d8bd1fbc4624a1aeabde4883964271348d861402`, with the latest parity wrapper batch reflected below.

The test suite is green after the latest parity wrapper batch:

```text
324 passed, 3 skipped, 3 warnings
```

## Conclusion

The fork has moved past the original upstream README blockers for animated GIF export, multiline text, `FormattedString`, multistyle text, and `textBox()`. It has also reached static method-name coverage for the audited top-level, `BezierPath`, `FormattedString`, and `ImageObject` APIs. It has not reached pixel/behavior-identical DrawBot parity.

The remaining parity work is concentrated in:

- `ImageObject`, where many methods are cross-platform Pillow-backed approximations instead of Core Image-equivalent implementations;
- true pixel parity for text layout and shaping where DrawBot delegates to macOS CoreText.

The macOS/AppKit/PDFKit bridge APIs are intentionally out of scope for drawbot-skia's cross-platform package target. Their method names are present as explicit compatibility stubs that raise `DrawbotError`, so they should not be counted as open implementation gaps.

Do not call the larger feature-parity goal complete from this evidence.

## Upstream README Roadmap Status

| README item | Current status | Evidence |
|---|---:|---|
| Animated GIF export | Implemented | `RecordingDocument._saveImage_gif()`, `tests/test_api.py::test_saveImage_gif_frame_durations`, `tests/test_api.py::test_numberOfPages_gif` |
| Multi-line, single-style `text()` | Implemented | `Drawing.text()` handles multiline strings through `_formattedLines()`/line drawing; covered by `tests/apitests/multiLineText.py` |
| `FormattedString` | Implemented | `src/drawbot_skia/formattedString.py`; macOS `getNSObject()` exists as an explicit unsupported API |
| Multi-style `text()` | Implemented | `Drawing._textFormattedString()` and FormattedString API tests |
| Remaining `BezierPath` methods | Implemented | `intersectionPoints()`, `optimizePath()`, and `traceImage()` have been added; macOS bridge methods exist as explicit unsupported APIs |
| Many-things-I-forgot-to-mention | Incomplete | Static API coverage is complete; ImageObject and pixel-parity behavior gaps listed below |
| `textBox()` | Implemented, not CoreText-identical | `Drawing.textBox()`, FormattedString text box layout, overflow return tests |
| Fill further gaps in DrawBot API | Incomplete | Static API coverage is complete; ImageObject behavior gaps listed below |

## Top-level DrawBot Namespace Gaps

Static comparison source: public methods on `typemytype/drawbot` `DrawBotDrawingTool` versus `drawbot_skia.drawbot.__all__`.

Missing in `drawbot_skia.drawbot` after the latest parity wrapper batch:

```text
None
```

Notes:

- The low-risk wrappers around existing `FormattedString` or graphics-state capabilities have been added: `tracking`, `baselineShift`, `underline`, `strikethrough`, `url`, `fallbackFont`, font metric/query wrappers, `listOpenTypeFeatures`, `opacity`, `sizes`, `textOverflow`, and `textBoxBaselines`.
- `textBoxCharacterBounds()` has been added for rectangular text boxes using drawbot-skia's current line wrapping and shaping stack.
- `colorSpace()` and `listColorSpaces()` have been added as compatibility-level API/state support for DrawBot's standard color-space names. Rendering remains RGB-backed in Skia rather than CoreGraphics color-managed.
- `listLanguages()` has been added with Python-locale-derived identifiers.
- `drawing()` has been added as a reset/cleanup context manager.
- `installedFonts()`, `installFont()`, and `uninstallFont()` have been added. Temporary font installation is process-local in drawbot-skia: `installFont(path)` returns the font's PostScript name and registers that name as an alias for the path so it can be passed to `font()`. As in DrawBot, these functions are deprecated in favor of passing font paths directly.
- `pages()` has been added for recorded drawings, including context-manager support for drawing back into an existing page.
- `linkURL`, `linkDestination`, and `linkRect` have been added with SVG output annotations and PDF link annotations. PDF support is implemented as a post-processing pass over Skia's emitted PDF because skia-python's PDF API does not expose URL/destination annotation hooks.
- `Variable`, `pdfImage`, and `printImage` are intentionally out of scope for drawbot-skia's cross-platform package target. They now exist and raise explicit `DrawbotError`s explaining that they are macOS application/PDFKit features and are unavailable in drawbot-skia.

## `BezierPath` Gaps

Static comparison source: public methods on `typemytype/drawbot` `BezierPath` versus `drawbot_skia.path.BezierPath`.

Missing:

```text
None
```

Notes:

- `getNSBezierPath` and `setNSBezierPath` are intentionally out-of-scope macOS bridge APIs and now exist as explicit unsupported APIs.
- `intersectionPoints()` has been added using `fontTools.misc.bezierTools` segment intersections, with support for path-to-path intersections and self-intersections.
- `traceImage()` has been added using DrawBot's external-tool model: it requires `mkbitmap` and `potrace`, raises `DrawbotError` if they are unavailable, imports the traced SVG path data into the `BezierPath`, and documents the optional system dependency in the README.
- `optimizePath()` has been added for DrawBot's trailing-empty-`moveTo` cleanup behavior.

## `FormattedString` Gaps

Static comparison source: public methods on `typemytype/drawbot` `FormattedString` versus `drawbot_skia.formattedString.FormattedString`.

Missing:

```text
None
```

Notes:

- `getNSObject()` is an intentionally out-of-scope macOS bridge API and now exists as an explicit unsupported API.
- `url()` has been added as text-style state; rendering URL annotations still depends on the output context and is tracked with the link APIs.

## `ImageObject` Gaps

Static comparison source: public methods on `typemytype/drawbot` `ImageObject` versus `drawbot_skia.imageObject.ImageObject`.

Current fork supports:

```text
CMYKHalftone
SRGBToneCurveToLinear
XRay
accordionFoldTransition
additionCompositing
affineClamp
affineTile
areaAverage
areaHistogram
areaLogarithmicHistogram
areaMaximum
areaMaximumAlpha
areaMinMax
areaMinMaxRed
areaMinimum
areaMinimumAlpha
aztecCodeGenerator
barsSwipeTransition
blendWithAlphaMask
blendWithBlueMask
blendWithMask
blendWithRedMask
bloom
blurredRectangleGenerator
bokehBlur
boxBlur
bumpDistortion
bumpDistortionLinear
cannyEdgeDetector
checkerboardGenerator
circleSplashDistortion
circularScreen
circularWrap
clamp
clearFilters
code128BarcodeGenerator
colorAbsoluteDifference
colorBlendMode
colorBurnBlendMode
colorClamp
colorControls
colorCrossPolynomial
colorDodgeBlendMode
colorInvert
colorMap
colorMatrix
colorMonochrome
colorPolynomial
colorPosterize
colorThreshold
colorThresholdOtsu
columnAverage
comicEffect
constantColorGenerator
convertLabToRGB
convertRGBtoLab
copy
copyMachineTransition
crop
crystallize
darkenBlendMode
depthOfField
depthToDisparity
differenceBlendMode
discBlur
dither
disintegrateWithMaskTransition
disparityToDepth
displacementDistortion
dissolveTransition
divideBlendMode
documentEnhancer
dotScreen
droste
edgeWork
edgePreserveUpsampleFilter
eightfoldReflectedTile
edges
exclusionBlendMode
exposureAdjust
falseColor
flashTransition
fourfoldReflectedTile
fourfoldRotatedTile
fourfoldTranslatedTile
gaborGradients
gammaAdjust
gaussianBlur
gaussianGradient
glassDistortion
glassLozenge
glideReflectedTile
gloom
guidedFilter
hardLightBlendMode
hatchedScreen
heightFieldFromMask
hexagonalPixellate
highlightShadowAdjust
histogramDisplayFilter
holeDistortion
hueAdjust
hueBlendMode
kaleidoscope
keystoneCorrectionCombined
keystoneCorrectionHorizontal
keystoneCorrectionVertical
KMeans
labDeltaE
lanczosScaleTransform
lenticularHaloGenerator
lightenBlendMode
lightTunnel
lineOverlay
lineScreen
linearBurnBlendMode
linearDodgeBlendMode
linearGradient
linearLightBlendMode
linearToSRGBToneCurve
lockFocus
luminosityBlendMode
maskToAlpha
maskedVariableBlur
maximumComponent
maximumCompositing
meshGenerator
minimumComponent
minimumCompositing
mix
modTransition
morphologyGradient
morphologyMaximum
morphologyMinimum
morphologyRectangleMaximum
morphologyRectangleMinimum
motionBlur
multiplyBlendMode
multiplyCompositing
noiseReduction
ninePartStretched
ninePartTiled
offset
open
opTile
overlayBlendMode
pageCurlTransition
pageCurlWithShadowTransition
paletteCentroid
palettize
parallelogramTile
PDF417BarcodeGenerator
personSegmentation
perspectiveCorrection
perspectiveRotate
perspectiveTile
perspectiveTransform
perspectiveTransformWithExtent
photoEffectChrome
photoEffectFade
photoEffectInstant
photoEffectMono
photoEffectNoir
photoEffectProcess
photoEffectTonal
photoEffectTransfer
pinchDistortion
pinLightBlendMode
pixellate
pointillize
QRCodeGenerator
radialGradient
randomGenerator
rippleTransition
roundedRectangleGenerator
roundedRectangleStrokeGenerator
rowAverage
saliencyMapFilter
sampleNearest
saturationBlendMode
screenBlendMode
sepiaTone
shadedMaterial
sharpenLuminance
sixfoldReflectedTile
sixfoldRotatedTile
size
smoothLinearGradient
sobelGradients
softLightBlendMode
sourceAtopCompositing
sourceInCompositing
sourceOutCompositing
sourceOverCompositing
spotColor
spotLight
starShineGenerator
straightenFilter
stretchCrop
stripesGenerator
subtractBlendMode
sunbeamsGenerator
swipeTransition
temperatureAndTint
thermal
torusLensDistortion
triangleKaleidoscope
triangleTile
twelvefoldReflectedTile
twirlDistortion
unlockFocus
unsharpMask
vibrance
vignette
vignetteEffect
vividLightBlendMode
vortexDistortion
whitePointAdjust
zoomBlur
```

DrawBot exposes 219 public `ImageObject` methods in the audited commit. The fork now supports all 219 of those method names. The newly added methods are Pillow-backed approximations of common Core Image filters, color operations, morphology filters, generators, simple geometry filters, analysis/statistical filters, stylization filters, screen/halftone filters, masked blur/upsample filters, distortion/tiling filters, transition filters, segmentation/saliency/material filters, and blend/compositing modes rather than pixel-identical Core Image implementations. `aztecCodeGenerator()` is backed by `aztec-code-generator` for standards-compliant Aztec output. `QRCodeGenerator()` is backed by a standards-compliant byte-mode QR encoder for messages that fit QR versions 1-4. `PDF417BarcodeGenerator()` is backed by `pdf417gen` for standards-compliant PDF417 output. `code128BarcodeGenerator()` is backed by a standards-compliant Code 128 Set B encoder for text input.

Representative behavior follow-up groups:

- generators and barcodes: barcode and advanced Core Image generator method names now exist. `aztecCodeGenerator()` uses `aztec-code-generator` for standards-compliant Aztec output, `QRCodeGenerator()` produces standards-compliant byte-mode QR output for messages that fit QR versions 1-4, `PDF417BarcodeGenerator()` uses `pdf417gen` for standards-compliant PDF417 output, and `code128BarcodeGenerator()` produces standards-compliant Code 128 Set B output for text input; tracked in [#6](https://github.com/eliheuer/drawbot-skia/issues/6).
- blur, stylization, saliency, segmentation, material, and lighting filters now exist as Pillow-backed approximations and still need deeper Core Image-equivalent behavior; tracked in [#8](https://github.com/eliheuer/drawbot-skia/issues/8).
- color/statistical filters now exist. CIE Lab conversion and Delta E use sRGB/D65 color math; KMeans returns a one-dimensional palette image with alpha weights; palettize and paletteCentroid use color-distance assignment against supplied palette images; spotColor applies contrast-aware color-range replacement. Remaining differences are expected to be pixel-level Core Image implementation details rather than known placeholder behavior.
- compositing, transition, and mask workflow method names now exist. Swipe/copy-machine transitions respect extent, color, opacity, angle, width, and time; disintegrate transitions use mask-threshold timing and shadow parameters; ripple transitions use shading-image displacement, extent, scale, width, center, and time; mod transitions use radius, angle, compression, center, and time; accordion transitions use fold count, fold shadow, bottom height, and time; page-curl transitions use target/backside images, shading, extent, angle, radius, time, and shadow parameters. Remaining transition filters still need deeper Core Image-equivalent semantics; tracked in [#9](https://github.com/eliheuer/drawbot-skia/issues/9).
- geometry and distortion method names now exist as Pillow-backed approximations. Nine-part stretch/tile filters now preserve breakpoint-defined edge and corner regions while expanding the center regions. Keystone, Droste, and advanced warps still need deeper Core Image-equivalent behavior; tracked in [#10](https://github.com/eliheuer/drawbot-skia/issues/10).

Given upstream README's caveat that DrawBot's `ImageObject` is macOS/Core Image-heavy and "huge", this should not be treated as a blocker for the headline text/path parity milestone unless the project explicitly chooses an ImageObject parity target.

## Recommended Next Work

1. Decide whether the Pillow-backed `ImageObject` approximations are sufficient for this fork or whether specific filters need Core Image-equivalent behavior; umbrella tracked in [#2](https://github.com/eliheuer/drawbot-skia/issues/2), with specific follow-up issues [#8](https://github.com/eliheuer/drawbot-skia/issues/8), [#9](https://github.com/eliheuer/drawbot-skia/issues/9), and [#10](https://github.com/eliheuer/drawbot-skia/issues/10).
