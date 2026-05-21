size(480, 220)
fill(1)
rect(0, 0, width(), height())

t = FormattedString()
t.fontSize(40)
t.fill(0)
t += "Black "
t.fill(1, 0, 0)
t += "Red\n"
t.fontSize(28)
t.lineHeight(34)
t.fill(0, 0, 1)
t += "Blue smaller "
t.fill(0, 0.5, 0)
t += "Green"

text(t, (30, 160))

t2 = FormattedString("Centered", fontSize=30, fill=(0.5,))
text(t2, (360, 60), align="center")
