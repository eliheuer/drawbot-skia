# DrawBot API Gap Audit

Date: 2026-05-22

## Scope

This audit compares the current fork against:

- `justvanrossum/drawbot-skia` upstream README roadmap at `upstream/main` commit `582e2c5067234ee6c8c72bff524e8efb7cab51d4`.
- `typemytype/drawbot` public drawing API at commit `71cff6df68fff1fafd5a542ab58157b30e377bd1`.
- Current fork baseline commit `d8bd1fbc4624a1aeabde4883964271348d861402`, with the latest parity wrapper batch reflected below.

The test suite is green after the latest parity wrapper batch:

```text
395 passed, 3 skipped, 3 warnings
```

## Conclusion

The fork has moved past the original upstream README blockers for animated GIF export, multiline text, `FormattedString`, multistyle text, and `textBox()`. It has also reached static method-name coverage for the audited top-level, `BezierPath`, `FormattedString`, and `ImageObject` APIs. It has not reached pixel/behavior-identical DrawBot parity.

The remaining parity work is concentrated in:

- `ImageObject`, where many methods are cross-platform Pillow-backed approximations instead of Core Image-equivalent implementations;
- true pixel parity for text layout and shaping where DrawBot delegates to macOS CoreText; tracked in [#12](https://github.com/eliheuer/drawbot-skia/issues/12).

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
- `ImageObject.lockFocus()`, `ImageObject.unlockFocus()`, and `with ImageObject():` drawing have been added for module-level drawing into image objects while preserving the surrounding drawing state.

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
- `textBox()` now supports plain-string hyphenation and `FormattedString` input when converting wrapped text into path outlines.

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

DrawBot exposes 219 public `ImageObject` methods in the audited commit. The fork now supports all 219 of those method names, including focused drawing into an image object with `lockFocus()`, `unlockFocus()`, and `with imageObject:`. The newly added methods are Pillow-backed approximations of common Core Image filters, color operations, morphology filters, generators, simple geometry filters, analysis/statistical filters, stylization filters, screen/halftone filters, masked blur/upsample filters, distortion/tiling filters, transition filters, segmentation/saliency/material filters, and blend/compositing modes rather than pixel-identical Core Image implementations. `aztecCodeGenerator()` is backed by `aztec-code-generator` for standards-compliant Aztec output. `QRCodeGenerator()` is backed by a standards-compliant byte-mode QR encoder for messages that fit QR versions 1-4. `PDF417BarcodeGenerator()` is backed by `pdf417gen` for standards-compliant PDF417 output. `code128BarcodeGenerator()` is backed by a standards-compliant Code 128 Set B encoder for text input.

Representative behavior follow-up groups:

- generators and barcodes: barcode and advanced Core Image generator method names now exist. `aztecCodeGenerator()` uses `aztec-code-generator` for standards-compliant Aztec output, `checkerboardGenerator()` and `stripesGenerator()` use sharpness to soften pattern boundaries, `QRCodeGenerator()` produces standards-compliant byte-mode QR output for messages that fit QR versions 1-4, `PDF417BarcodeGenerator()` uses `pdf417gen` for standards-compliant PDF417 output, and `code128BarcodeGenerator()` produces standards-compliant Code 128 Set B output for text input; tracked in [#6](https://github.com/eliheuer/drawbot-skia/issues/6).
- blur, stylization, saliency, segmentation, material, and lighting filters now exist as Pillow-backed approximations. `bloom()` and `gloom()` preserve source alpha while applying their glow colors. `colorMonochrome()` and `whitePointAdjust()` tint RGB while preserving source alpha. Photo-effect filters use `extrapolate` to strengthen their existing color/contrast curve. `bokehBlur()` treats zero radius as a no-op and uses an aperture kernel with radius, ring amount, ring size, and softness controls for positive radii. `cannyEdgeDetector()` uses low/high thresholds with hysteresis passes and Lab-lightness edge input when `perceptual=True`. Screen and halftone filters interpret angle values as radians; `CMYKHalftone()` uses CMYK separations with GCR/UCR controls before recomposing subtractive dot screens. `depthOfField()` uses the point0/point1 focus line to preserve nearby detail and blur farther pixels. `documentEnhancer()` treats `amount=0` as a no-op and blends stronger enhancement as amount increases. `edges()` and `edgeWork()` preserve alpha while emphasizing edge content. `guidedFilter()` uses radius-controlled smoothing and guide-edge preservation controlled by epsilon. `highlightShadowAdjust()` uses radius-controlled luminance context while preserving alpha. `lenticularHaloGenerator()` uses halo overlap, striation strength/contrast, and time. `lineOverlay()` uses noise reduction, sharpness, and contrast controls before thresholding edge detail. `maskedVariableBlur()` uses mask luminance to select local blur radius. `morphologyMaximum()` and `morphologyMinimum()` treat zero radius as a no-op, `morphologyGradient()` allows zero radius to produce a zero-difference image, and rectangle morphology uses separate width and height kernels. `motionBlur()` treats zero radius as a no-op and uses radius plus radians-based angle for explicit directional sampling. `noiseReduction()` treats zero noise and sharpness as a no-op and applies denoising and sharpening independently. `personSegmentation()` uses `qualityLevel` to control matte thresholding and softening. `saliencyMapFilter()` emits a grayscale local-contrast saliency map. `shadedMaterial()` treats the shading image as a height field for relief lighting controlled by scale. `sharpenLuminance()` sharpens the luminance plane while preserving original chroma and alpha. `unsharpMask()` sharpens RGB content while preserving source alpha. `vignetteEffect()` darkens RGB content while preserving source alpha. `spotLight()` uses `lightPointsAt` as the beam target, applies directional falloff from `lightPosition`, and alpha-masks areas outside the highlight. `starShineGenerator()` uses cross opacity and epsilon controls for ray intensity and glow softness. `sunbeamsGenerator()` uses striation radius, strength, contrast, and time when generating ray patterns. `zoomBlur()` treats zero amount as a no-op and uses the provided center as the zoom anchor. The remaining filters still need deeper Core Image-equivalent behavior; tracked in [#8](https://github.com/eliheuer/drawbot-skia/issues/8).
- color/statistical filters now exist. `hueAdjust()` interprets angle values as radians and preserves exact no-op behavior for zero and full-turn angles. CIE Lab conversion and Delta E use sRGB/D65 color math; KMeans returns a one-dimensional palette image with alpha weights, uses `passes` for iterative refinement, and uses Lab-space distance when `perceptual=True`; palettize and paletteCentroid use color-distance assignment against supplied palette images; spotColor applies contrast-aware color-range replacement. Remaining differences are expected to be pixel-level Core Image implementation details rather than known placeholder behavior.
- compositing, transition, and mask workflow method names now exist. Swipe/copy-machine transitions respect extent, color, opacity, angle, width, and time; flash transitions respect extent, color, time, fade threshold, and striation parameters; disintegrate transitions use mask-threshold timing and shadow parameters; ripple transitions use shading-image displacement, extent, scale, width, center, and time; mod transitions use radius, angle, compression, center, and time; accordion transitions use fold count, fold shadow, bottom height, and time; page-curl transitions use target/backside images, shading, extent, angle, radius, time, and shadow parameters. Transition approximations preserve the source image exactly at `time=0` and the target image exactly at `time=1`. Remaining transition filters still need deeper Core Image-equivalent semantics; tracked in [#9](https://github.com/eliheuer/drawbot-skia/issues/9).
- geometry and distortion method names now exist as Pillow-backed approximations. `affineTile()` applies affine sampling with wraparound tiling. `displacementDistortion()` uses red and green channels for independent x/y displacement. `droste()` uses inset points, strands, periodicity, rotation, and zoom for recursive inset composition. `glassDistortion()` samples the texture relative to the supplied center. `lightTunnel()` uses center, radius, and rotation for radial tunnel warping. `perspectiveCorrection()` respects crop=False by preserving the expanded transform canvas and offset. `keystoneCorrectionCombined()` scales supplied corner correction by focal length, and `perspectiveRotate()` projects rotated corners through focal length before transforming the image. `pixellate()` anchors the pixel grid on the supplied center, and `pointillize()` anchors its dot grid on the supplied center. `stretchCrop()` uses crop amount to interpolate between stretching and aspect-crop fitting, and uses center stretch amount to control the resized center band. Nine-part stretch/tile filters now preserve breakpoint-defined edge and corner regions while expanding the center regions. Kaleidoscope and reflected/rotated tile filters now use their center/point argument as the rotation pivot, `triangleKaleidoscope()` uses size for the sampled triangular span and decay for repeated wedge brightness, reflected/rotated tile filters use width to seed the repeated tile source, fourfold tile filters use acute angle for the second tile vector, and translated/parallelogram tile filters use center as a phase or reflection pivot. Keystone and advanced warps still need deeper Core Image-equivalent behavior; tracked in [#10](https://github.com/eliheuer/drawbot-skia/issues/10).

Given upstream README's caveat that DrawBot's `ImageObject` is macOS/Core Image-heavy and "huge", this should not be treated as a blocker for the headline text/path parity milestone unless the project explicitly chooses an ImageObject parity target.

## Recommended Next Work

1. Decide whether the Pillow-backed `ImageObject` approximations are sufficient for this fork or whether specific filters need Core Image-equivalent behavior; umbrella tracked in [#2](https://github.com/eliheuer/drawbot-skia/issues/2), with specific follow-up issues [#8](https://github.com/eliheuer/drawbot-skia/issues/8), [#9](https://github.com/eliheuer/drawbot-skia/issues/9), and [#10](https://github.com/eliheuer/drawbot-skia/issues/10).
2. Build macOS DrawBot comparison fixtures for CoreText-backed text layout, shaping, hyphenation, and BezierPath text outlines; tracked in [#12](https://github.com/eliheuer/drawbot-skia/issues/12).
