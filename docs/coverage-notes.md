# Coverage notes

This docs/examples corpus is meant to become a visual parity suite for the main
DrawBot documentation categories. The current milestone establishes the
directory structure, render workflow, and representative fixtures for every
requested category.

## Current coverage

- Shapes: primitives, Bezier paths, stroke caps, joins, and dashes.
- Colors: RGB and CMYK color state, gradients, alpha, blend modes, and shadows.
- Canvas: canvas size, transforms, state save/restore, and multipage export.
- Text: point text, text boxes, `FormattedString`, line height, tracking,
  baseline shift, underline, and hyphenation settings.
- Images: `ImageObject` generators, focused drawing, drawing images to the
  canvas, and representative filters.
- Variables: repeatable examples using ordinary Python variables and parameter
  sweeps.
- Quick Reference: visual grouping of the major local API families.
- Port showcase: features called out by the upstream roadmap and compatibility
  notes that this fork now supports.

## Expansion targets

- Add one local example for each official DrawBot subpage where the API is
  implemented here.
- Add focused examples for export formats and animation once the docs structure
  needs them.
- Expand `showcase/` with examples for text shaping, variable fonts, barcode
  generators, path operations, and improved `ImageObject` filters.
- Keep examples deterministic and small enough that rendered diffs point to one
  API family.
