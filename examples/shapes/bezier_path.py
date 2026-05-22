size(520, 360)

fill(1)
rect(0, 0, width(), height())

path = BezierPath()
path.moveTo((78, 100))
path.curveTo((118, 295), (265, 305), (278, 164))
path.curveTo((292, 42), (420, 72), (452, 220))

stroke(0.08, 0.16, 0.28)
strokeWidth(16)
fill(None)
drawPath(path)

stroke(0.95, 0.38, 0.2)
strokeWidth(5)
lineDash(14, 9)
drawPath(path)
lineDash(None)

fill(0.08, 0.16, 0.28)
stroke(None)
for point in [(78, 100), (278, 164), (452, 220)]:
    oval(point[0] - 7, point[1] - 7, 14, 14)

fontSize(20)
text("BezierPath curve drawing", (52, 42))
