# DrawBot API Gap Audit

Date: 2026-05-22

## Scope

This audit compares the current fork against:

- `justvanrossum/drawbot-skia` upstream README roadmap at `upstream/main` commit `582e2c5067234ee6c8c72bff524e8efb7cab51d4`.
- `typemytype/drawbot` public drawing API at commit `71cff6df68fff1fafd5a542ab58157b30e377bd1`.
- Current fork baseline commit `d8bd1fbc4624a1aeabde4883964271348d861402`, with the latest parity wrapper batch reflected below.

The test suite is green after the latest parity wrapper batch:

```text
315 passed, 3 skipped, 3 warnings
```

## Conclusion

The fork has moved past the original upstream README blockers for animated GIF export, multiline text, `FormattedString`, multistyle text, and `textBox()`. It has not reached full DrawBot API parity.

The remaining parity work is concentrated in:

- behavior gaps behind top-level compatibility names, especially PDF link annotations and macOS app/PDFKit helpers;
- `ImageObject`, where only a small cross-platform subset exists compared with DrawBot's Core Image-backed API;
- macOS/AppKit-only APIs that should be deliberately documented as unsupported instead of silently treated as parity gaps.

Do not call the larger feature-parity goal complete from this evidence.

## Upstream README Roadmap Status

| README item | Current status | Evidence |
|---|---:|---|
| Animated GIF export | Implemented | `RecordingDocument._saveImage_gif()`, `tests/test_api.py::test_saveImage_gif_frame_durations`, `tests/test_api.py::test_numberOfPages_gif` |
| Multi-line, single-style `text()` | Implemented | `Drawing.text()` handles multiline strings through `_formattedLines()`/line drawing; covered by `tests/apitests/multiLineText.py` |
| `FormattedString` | Implemented | `src/drawbot_skia/formattedString.py`; macOS `getNSObject()` exists as an explicit unsupported API |
| Multi-style `text()` | Implemented | `Drawing._textFormattedString()` and FormattedString API tests |
| Remaining `BezierPath` methods | Implemented | `intersectionPoints()`, `optimizePath()`, and `traceImage()` have been added; macOS bridge methods exist as explicit unsupported APIs |
| Many-things-I-forgot-to-mention | Incomplete | Top-level namespace is complete; behavior gaps listed below |
| `textBox()` | Implemented, not CoreText-identical | `Drawing.textBox()`, FormattedString text box layout, overflow return tests |
| Fill further gaps in DrawBot API | Incomplete | Top-level, path, FormattedString, and ImageObject gaps listed below |

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
- `linkURL`, `linkDestination`, and `linkRect` have been added with SVG output annotations. PDF annotations remain unsupported because skia-python's PDF API does not expose URL/destination annotation hooks.
- `Variable`, `pdfImage`, and `printImage` now exist and raise explicit `DrawbotError`s explaining that they are macOS application/PDFKit features and are unavailable in drawbot-skia.

## `BezierPath` Gaps

Static comparison source: public methods on `typemytype/drawbot` `BezierPath` versus `drawbot_skia.path.BezierPath`.

Missing:

```text
None
```

Notes:

- `getNSBezierPath` and `setNSBezierPath` are macOS bridge APIs and now exist as explicit unsupported APIs.
- `intersectionPoints()` has been added using `fontTools.misc.bezierTools` segment intersections, with support for path-to-path intersections and self-intersections.
- `traceImage()` has been added using DrawBot's external-tool model: it requires `mkbitmap` and `potrace`, raises `DrawbotError` if they are unavailable, and imports the traced SVG path data into the `BezierPath`.
- `optimizePath()` has been added for DrawBot's trailing-empty-`moveTo` cleanup behavior.

## `FormattedString` Gaps

Static comparison source: public methods on `typemytype/drawbot` `FormattedString` versus `drawbot_skia.formattedString.FormattedString`.

Missing:

```text
None
```

Notes:

- `getNSObject()` is a macOS bridge API and now exists as an explicit unsupported API.
- `url()` has been added as text-style state; rendering URL annotations still depends on the output context and is tracked with the link APIs.

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

1. Implement PDF link annotations for `linkURL`, `linkDestination`, `linkRect`, and richer `FormattedString.url()` behavior if a cross-platform PDF annotation backend is added.
2. Decide whether `mkbitmap`/`potrace` should be documented as optional traceImage dependencies, bundled, or replaced with a Python tracing dependency.
3. Decide whether to keep explicit unsupported errors for macOS-only APIs or document them as permanently out of scope: `Variable`, `pdfImage`, `printImage`, `getNSObject`, `getNSBezierPath`, `setNSBezierPath`.
4. Decide an `ImageObject` target subset rather than chasing all Core Image filters.
