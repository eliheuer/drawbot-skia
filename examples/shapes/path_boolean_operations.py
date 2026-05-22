size(760, 420)

fill(0.97)
rect(0, 0, width(), height())


def shape_a():
    path = BezierPath()
    path.oval(0, 0, 96, 96)
    return path


def shape_b():
    path = BezierPath()
    path.rect(44, 18, 96, 72)
    return path


operations = [
    ("union", lambda a, b: a.union(b)),
    ("intersection", lambda a, b: a.intersection(b)),
    ("difference", lambda a, b: a.difference(b)),
    ("xor", lambda a, b: a.xor(b)),
]

for index, (label, operation) in enumerate(operations):
    x = 62 + index * 174
    y = 170

    a = shape_a()
    b = shape_b()
    result = operation(a, b)

    save()
    translate(x, y)
    fill(0.9, 0.92, 0.94)
    stroke(None)
    drawPath(a)
    fill(0.86, 0.88, 0.9)
    drawPath(b)
    fill(0.9, 0.34, 0.16, 0.88)
    stroke(0.08, 0.16, 0.28)
    strokeWidth(3)
    drawPath(result)
    restore()

    fill(0.08)
    stroke(None)
    fontSize(15)
    text(label, (x, y - 38))

fill(0.08)
fontSize(28)
text("BezierPath boolean operations", (58, 344))
fontSize(14)
text("Each result is drawn over the two source shapes.", (58, 56))
