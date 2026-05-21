size(220, 160)

base = BezierPath()
base.moveTo((20, 30))
base.curveTo((80, 140), (140, 20), (200, 130))

fill(None)
stroke(0.85)
strokeWidth(10)
drawPath(base)

dashed = base.dashStroke(18, 10, 6, 10, offset=8)

stroke(0, 0.2, 1)
strokeWidth(4)
drawPath(dashed)

fill(1, 0, 0)
stroke(None)
for contour in dashed.contours:
    x, y = contour[0][0]
    oval(x - 3, y - 3, 6, 6)
