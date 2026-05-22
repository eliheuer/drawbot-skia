size(720, 420)

fill(0.97)
rect(0, 0, width(), height())

path = BezierPath()
path.text("PATH", offset=(62, 190), fontSize=118)

shadow((8, -8), 14, (0, 0, 0, 0.22))
fill(0.12, 0.2, 0.34)
stroke(None)
drawPath(path)
shadow(None)

outline = path.copy()
stroke(0.95, 0.34, 0.16)
strokeWidth(3)
fill(None)
drawPath(outline)

box_path = BezierPath()
overflow = box_path.textBox(
    "BezierPath.textBox converts wrapped text to outlines.",
    (426, 158, 214, 112),
    fontSize=22,
)

fill(0.95, 0.34, 0.16)
stroke(None)
drawPath(box_path)

stroke(0.64)
strokeWidth(1)
fill(None)
rect(426, 158, 214, 112)

fill(0.08)
stroke(None)
fontSize(18)
text("BezierPath.text() and BezierPath.textBox()", (62, 58))
fontSize(13)
text(f"overflow characters: {len(overflow)}", (426, 132))
