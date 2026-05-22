# Quick Reference

Official DrawBot reference: <https://www.drawbot.com/content/quickReference.html>

This local quick reference is intentionally visual: it groups the major API
families covered by the examples and points back to source files that can be
rendered with the local runner.

![API overview](../examples/quick_reference/api_overview.jpg)

Source:
[`examples/quick_reference/api_overview.py`](../examples/quick_reference/api_overview.py)

## Local API families

| Area | Common calls covered by visual examples |
| --- | --- |
| Canvas | `size`, `newPage`, `width`, `height`, `pageCount`, `frameDuration`, `save`, `restore`, `savedState` |
| Shapes | `rect`, `oval`, `line`, `polygon`, `BezierPath`, `newPath`, `moveTo`, `lineTo`, `curveTo`, `qCurveTo`, `drawPath`, `clipPath` |
| Path operations | `union`, `intersection`, `difference`, `xor`, `removeOverlap`, `reverse`, `appendPath`, `pointInside` |
| Color | `fill`, `stroke`, `cmykFill`, `cmykStroke`, `linearGradient`, `radialGradient`, `opacity`, `blendMode`, `shadow` |
| Text | `font`, `fontSize`, `lineHeight`, `tracking`, `baselineShift`, `underline`, `text`, `textBox`, `FormattedString` |
| Text metrics | `textSize`, `textOverflow`, `textBoxBaselines`, `textBoxCharacterBounds` |
| Images | `image`, `imageSize`, `imagePixelColor`, `ImageObject`, focused drawing, generators, filters, transitions, distortions |
| Variables | Ordinary Python names, lists, loops, and functions for deterministic parameterized examples |
| Export | The command-line runner plus `saveImage` support for raster, vector, document, and animation-oriented outputs |
