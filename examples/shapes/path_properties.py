size(560, 380)

fill(0.97)
rect(0, 0, width(), height())

styles = [
    ("butt / miter", "butt", "miter", None),
    ("round / round", "round", "round", (10, 7)),
    ("square / bevel", "square", "bevel", (2, 8)),
]

for index, (label, cap, join, dash) in enumerate(styles):
    y = 278 - index * 92
    path = BezierPath()
    path.moveTo((72, y))
    path.lineTo((176, y + 36))
    path.lineTo((286, y - 18))
    path.lineTo((408, y + 20))

    fill(None)
    stroke(0.08, 0.16, 0.28)
    strokeWidth(18)
    lineCap(cap)
    lineJoin(join)
    if dash:
        lineDash(*dash)
    else:
        lineDash(None)
    drawPath(path)

    stroke(None)
    fill(0.08)
    fontSize(15)
    text(label, (424, y - 6))

lineDash(None)
fill(0.08)
fontSize(20)
text("stroke caps, joins, and dash patterns", (56, 42))
