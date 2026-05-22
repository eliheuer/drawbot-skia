# DrawBot API Gap Audit

Date: 2026-05-22

## Scope

This audit compares the current fork against:

- `justvanrossum/drawbot-skia` upstream README roadmap at `upstream/main` commit `582e2c5067234ee6c8c72bff524e8efb7cab51d4`.
- `typemytype/drawbot` public drawing API at commit `71cff6df68fff1fafd5a542ab58157b30e377bd1`.
- Current fork commit `d8bd1fbc4624a1aeabde4883964271348d861402`.

The test suite is green at this commit:

```text
301 passed, 3 skipped, 3 warnings
```

## Conclusion

The fork has moved past the original upstream README blockers for animated GIF export, multiline text, `FormattedString`, multistyle text, and `textBox()`. It has not reached full DrawBot API parity.

The remaining parity work is concentrated in:

- top-level DrawBot namespace gaps, including link annotations, font query wrappers, `opacity()`, installed font helpers, and text overflow/measurement helpers;
- `BezierPath` gaps, especially `intersectionPoints()` and `traceImage()`;
- `ImageObject`, where only a small cross-platform subset exists compared with DrawBot's Core Image-backed API;
- macOS/AppKit-only APIs that should be deliberately documented as unsupported instead of silently treated as parity gaps.

Do not call the larger feature-parity goal complete from this evidence.

## Upstream README Roadmap Status

| README item | Current status | Evidence |
|---|---:|---|
| Animated GIF export | Implemented | `RecordingDocument._saveImage_gif()`, `tests/test_api.py::test_saveImage_gif_frame_durations`, `tests/test_api.py::test_numberOfPages_gif` |
| Multi-line, single-style `text()` | Implemented | `Drawing.text()` handles multiline strings through `_formattedLines()`/line drawing; covered by `tests/apitests/multiLineText.py` |
| `FormattedString` | Implemented, not full DrawBot parity | `src/drawbot_skia/formattedString.py`; missing `url()` and macOS `getNSObject()` vs DrawBot |
| Multi-style `text()` | Implemented | `Drawing._textFormattedString()` and FormattedString API tests |
| Remaining `BezierPath` methods | Incomplete | Missing `intersectionPoints()`, `traceImage()`; macOS bridge methods not applicable |
| Many-things-I-forgot-to-mention | Incomplete | Top-level namespace gaps listed below |
| `textBox()` | Implemented, not CoreText-identical | `Drawing.textBox()`, FormattedString text box layout, overflow return tests |
| Fill further gaps in DrawBot API | Incomplete | Top-level, path, FormattedString, and ImageObject gaps listed below |

## Top-level DrawBot Namespace Gaps

Static comparison source: public methods on `typemytype/drawbot` `DrawBotDrawingTool` versus `drawbot_skia.drawbot.__all__`.

Missing in `drawbot_skia.drawbot`:

```text
Variable
baselineShift
colorSpace
drawing
fallbackFont
fontAscender
fontCapHeight
fontContainsCharacters
fontContainsGlyph
fontDescender
fontFileFontNumber
fontFilePath
fontLeading
fontLineHeight
fontXHeight
installFont
installedFonts
linkDestination
linkRect
linkURL
listColorSpaces
listFontGlyphNames
listLanguages
listOpenTypeFeatures
opacity
pages
pdfImage
printImage
sizes
strikethrough
textBoxBaselines
textBoxCharacterBounds
textOverflow
textProperties
tracking
underline
uninstallFont
url
```

Notes:

- Several missing names are straightforward wrappers around existing `FormattedString` or graphics-state capabilities (`tracking`, `baselineShift`, `underline`, `strikethrough`, font metric/query wrappers).
- `linkURL`, `linkDestination`, and `linkRect` require output-context support, at least for PDF.
- `Variable`, `drawing`, `pages`, `pdfImage`, and `printImage` are app/macOS-oriented and need a deliberate cross-platform support decision.
- `installFont`/`uninstallFont` are likely macOS-specific in original DrawBot; cross-platform behavior should be scoped before implementation.

## `BezierPath` Gaps

Static comparison source: public methods on `typemytype/drawbot` `BezierPath` versus `drawbot_skia.path.BezierPath`.

Missing:

```text
getNSBezierPath
intersectionPoints
optimizePath
setNSBezierPath
traceImage
```

Notes:

- `getNSBezierPath` and `setNSBezierPath` are macOS bridge APIs and should probably remain unsupported in `drawbot-skia`.
- `intersectionPoints()` and `traceImage()` are real DrawBot user-facing path features.
- `optimizePath()` may be implementable through existing path conversion or pathops cleanup, but needs behavior comparison.

## `FormattedString` Gaps

Static comparison source: public methods on `typemytype/drawbot` `FormattedString` versus `drawbot_skia.formattedString.FormattedString`.

Missing:

```text
getNSObject
url
```

Notes:

- `getNSObject()` is macOS bridge API and should remain unsupported or documented as intentionally absent.
- `url()` is relevant if PDF/link annotations are added.

## `ImageObject` Gaps

Static comparison source: public methods on `typemytype/drawbot` `ImageObject` versus `drawbot_skia.imageObject.ImageObject`.

Current fork supports:

```text
boxBlur
clearFilters
colorControls
colorInvert
copy
gaussianBlur
lockFocus
offset
open
photoEffectMono
photoEffectNoir
sepiaTone
sharpenLuminance
size
unlockFocus
```

DrawBot exposes 219 public `ImageObject` methods in the audited commit. The fork intentionally supports only a small subset. Representative missing groups:

- generators and barcodes: `QRCodeGenerator`, `PDF417BarcodeGenerator`, `aztecCodeGenerator`, `code128BarcodeGenerator`, gradient/checkerboard/stripe generators;
- blur and stylization filters: `motionBlur`, `zoomBlur`, `bokehBlur`, `comicEffect`, `pixellate`, `vignette`, `unsharpMask`, `noiseReduction`;
- color filters: `hueAdjust`, `gammaAdjust`, `exposureAdjust`, `temperatureAndTint`, `vibrance`, `colorMonochrome`, `falseColor`;
- compositing and blend filters: `multiplyCompositing`, `sourceOverCompositing`, `overlayBlendMode`, `screenBlendMode`, `hardLightBlendMode`;
- geometry and distortion filters: `crop`, `affineTile`, `perspectiveTransform`, `twirlDistortion`, `bumpDistortion`, `kaleidoscope`.

Given upstream README's caveat that DrawBot's `ImageObject` is macOS/Core Image-heavy and "huge", this should not be treated as a blocker for the headline text/path parity milestone unless the project explicitly chooses an ImageObject parity target.

## Recommended Next Work

1. Add the low-risk top-level text/font wrappers already backed by current internals: `tracking`, `baselineShift`, `underline`, `strikethrough`, `textProperties`, font metric/query wrappers, `listOpenTypeFeatures`, and `fallbackFont`.
2. Add `opacity()` as graphics-state alpha if it can compose cleanly with fill, stroke, text, image, and shadow paints.
3. Implement or explicitly document PDF link annotation support for `linkURL`, `linkDestination`, `linkRect`, and `FormattedString.url()`.
4. Scope `BezierPath.intersectionPoints()` and `traceImage()` separately; both need targeted tests and may need new dependencies or geometry algorithms.
5. Decide which app/macOS-only APIs are out of scope and document them: `Variable`, `drawing`, `pages`, `pdfImage`, `printImage`, `installFont`, `uninstallFont`, `getNSObject`, `getNSBezierPath`, `setNSBezierPath`.
6. Decide an `ImageObject` target subset rather than chasing all Core Image filters.
