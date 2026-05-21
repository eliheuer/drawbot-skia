size(260, 180)

textPath = BezierPath()
overflow = textPath.textBox(
    "DrawBot Skia turns wrapped box text into reusable Bezier outlines.",
    (24, 34, 212, 96),
    fontSize=22,
    align="center",
)

fill(1)
rect(0, 0, width(), height())

fill(None)
stroke(0.8)
strokeWidth(1)
rect(24, 34, 212, 96)

fill(0.05)
stroke(None)
drawPath(textPath)

fill(1, 0, 0)
for x, y in textPath.onCurvePoints[::18]:
    oval(x - 1.5, y - 1.5, 3, 3)

assert overflow
