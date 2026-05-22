size(680, 440)

fill(0.98)
rect(0, 0, width(), height())

fill(0.08)
font("Helvetica")
fontSize(38)
text("DrawBot API overview", (48, 356))

sections = [
    ("Shapes", "rect / oval / line / BezierPath"),
    ("Color", "fill / stroke / gradient / opacity"),
    ("Canvas", "size / width / height / transforms"),
    ("Text", "font / fontSize / text / textBox"),
    ("Images", "image / imageSize / ImageObject"),
    ("Export", "saveImage through the runner"),
]

for index, (title, body) in enumerate(sections):
    x = 48 + (index % 2) * 310
    y = 250 - (index // 2) * 84
    fill(0.9, 0.94, 0.96)
    stroke(0.75)
    strokeWidth(1)
    rect(x, y, 264, 58)
    stroke(None)
    fill(0.08)
    fontSize(17)
    text(title, (x + 16, y + 34))
    fontSize(12)
    fill(0.32)
    text(body, (x + 16, y + 16))
