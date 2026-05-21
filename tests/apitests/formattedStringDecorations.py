size(460, 200)

fill(1)
rect(0, 0, width(), height())

t = FormattedString(fontSize=44, fill=(0.05,))
t.underline("single")
t += "single "
t.fill(1, 0, 0)
t.underline("thick")
t += "thick "
t.fill(0, 0.2, 1)
t.underline("double")
t += "double"

text(t, (24, 128))

t.clear()
t.fontSize(38)
t.fill(0)
t.underline(None)
t.strikethrough("single")
t += "strike "
t.fill(1, 0, 0)
t.strikethrough("thick")
t += "thick "
t.fill(0, 0.2, 1)
t.strikethrough("double")
t += "double"

text(t, (24, 58))
