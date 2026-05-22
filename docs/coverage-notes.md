# Coverage notes

This docs/examples corpus is a visual parity suite for the main DrawBot
documentation categories. It establishes the directory structure, render
workflow, and representative fixtures for every requested category.

## Current coverage

- Shapes: primitives, Bezier paths, drawing paths, clipping, boolean
  operations, text-to-path conversion, stroke caps, joins, and dashes.
- Colors: RGB and CMYK color state, gradients, alpha, blend modes, and shadows.
- Canvas: canvas size, transforms, state save/restore, multipage export, frame
  duration, and export targets.
- Text: point text, text boxes, `FormattedString`, line height, tracking,
  baseline shift, underline, hyphenation settings, variable font axes, text
  measurement, text box baselines, character bounds, and font query APIs.
- Images: `ImageObject` generators, focused drawing, drawing images to the
  canvas, image size/pixel sampling, representative filters, transitions, and
  distortions, tiling, and segmentation.
- Variables: repeatable examples using ordinary Python variables and parameter
  sweeps.
- Quick Reference: visual grouping of the major local API families.
- Port showcase: features called out by the upstream roadmap and compatibility
  notes that this fork now supports, including alpha-aware masks, barcode
  generators, path operations, shaping, variable fonts, and animation frame
  output.

## Known limits

- Keep `BezierPath.traceImage()` documented as optional because it requires
  external `mkbitmap` and `potrace` executables.
- Treat macOS application bridge APIs such as `Variable()` as out of scope for
  this cross-platform package; local variable examples use ordinary Python
  values instead.
- Keep the official DrawBot site as the source of truth for exact macOS
  DrawBot behavior. These pages are adapted docs tied to executable local
  examples, not a verbatim copy of the upstream site.
- Keep examples deterministic and small enough that rendered diffs point to one
  API family.
