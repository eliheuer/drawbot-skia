# Coverage notes

This docs/examples corpus is meant to become a visual parity suite for the main
DrawBot documentation categories. The current milestone establishes the
directory structure, render workflow, and representative fixtures for every
requested category.

## Current coverage

- Shapes: primitives, Bezier paths, drawing paths, clipping, boolean
  operations, stroke caps, joins, and dashes.
- Colors: RGB and CMYK color state, gradients, alpha, blend modes, and shadows.
- Canvas: canvas size, transforms, state save/restore, multipage export, frame
  duration, and export targets.
- Text: point text, text boxes, `FormattedString`, line height, tracking,
  baseline shift, underline, hyphenation settings, variable font axes, text
  measurement, text box baselines, and character bounds.
- Images: `ImageObject` generators, focused drawing, drawing images to the
  canvas, image size/pixel sampling, representative filters, transitions, and
  distortions.
- Variables: repeatable examples using ordinary Python variables and parameter
  sweeps.
- Quick Reference: visual grouping of the major local API families.
- Port showcase: features called out by the upstream roadmap and compatibility
  notes that this fork now supports, including alpha-aware masks, barcode
  generators, path operations, and animation frame output.

## Expansion targets

- Add one local example for each official DrawBot subpage where the API is
  implemented here.
- Expand `showcase/` with examples for text shaping, variable fonts, barcode
  generators, path operations, and improved `ImageObject` filters.
- Keep examples deterministic and small enough that rendered diffs point to one
  API family.
