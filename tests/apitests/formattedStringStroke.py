size(420, 160)

fill(1)
rect(0, 0, width(), height())

t = FormattedString(fontSize=56, fill=(1, 0.9, 0.2))
t.stroke(0)
t.strokeWidth(2)
t += "Stroke"
t.append(" CMYK", cmykFill=(1, 0, 1, 0), cmykStroke=(0, 1, 1, 0), strokeWidth=1.5)

text(t, (24, 92))

t.clear()
t.stroke(None)
t.fill(0.2)
t.fontSize(24)
t += "plain"

text(t, (24, 42))
