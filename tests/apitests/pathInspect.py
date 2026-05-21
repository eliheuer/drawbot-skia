size(360, 220)
fill(1)
rect(0, 0, width(), height())

path = BezierPath()
path.moveTo((40, 50))
path.lineTo((130, 50))
path.curveTo((170, 80), (170, 150), (90, 160))
path.qCurveTo((40, 150), (40, 90))
path.closePath()

fill(0.9)
stroke(0)
strokeWidth(2)
drawPath(path)

fill(1, 0, 0)
stroke(None)
for x, y in path.onCurvePoints:
    oval(x - 4, y - 4, 8, 8)

fill(0, 0, 1)
for x, y in path.offCurvePoints:
    oval(x - 3, y - 3, 6, 6)

fill(0)
fontSize(14)
text(f"points: {len(path.points)}", (210, 140))
text(f"on: {len(path.onCurvePoints)}", (210, 115))
text(f"off: {len(path.offCurvePoints)}", (210, 90))
text(f"open: {path.contours[0].open}", (210, 65))
