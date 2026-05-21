size(420, 280)
fill(1)
rect(0, 0, width(), height())

box = (40, 120, 160, 90)
fill(None)
stroke(0.7)
rect(*box)

fill(0)
stroke(None)
fontSize(22)
lineHeight(28)
overflow = textBox(
    "DrawBot Skia wraps text into a rectangle and returns the overflow.",
    box,
)

fill(1, 0, 0)
textBox(overflow, (240, 70, 140, 140), align="center")
