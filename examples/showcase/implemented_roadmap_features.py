size(720, 440)

fill(0.97)
rect(0, 0, width(), height())

fill(0.08)
font("Helvetica")
fontSize(34)
text("drawbot-skia port showcase", (48, 356))

fontSize(15)
items = [
    "BezierPath methods",
    "FormattedString text",
    "PNG/JPEG/PDF/SVG export",
    "variable fonts and shaping",
    "ImageObject filters",
    "animation formats",
]

for index, item in enumerate(items):
    x = 54 + (index % 3) * 214
    y = 236 - (index // 3) * 96
    fill(0.12, 0.2, 0.32)
    oval(x, y, 46, 46)
    fill(1)
    fontSize(20)
    text(str(index + 1), (x + 17, y + 13))
    fill(0.08)
    fontSize(15)
    textBox(item, (x + 58, y + 2, 132, 44))

path = BezierPath()
path.moveTo((48, 82))
path.curveTo((192, 168), (312, 24), (456, 94))
path.curveTo((530, 132), (622, 126), (672, 84))
stroke(0.9, 0.28, 0.16)
strokeWidth(8)
fill(None)
drawPath(path)

stroke(None)
fill(0.08)
fontSize(14)
text("A repo-specific category for features called out in the upstream roadmap.", (48, 42))
