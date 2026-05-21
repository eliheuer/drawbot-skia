size(360, 170)

fill(1)
rect(0, 0, width(), height())

t = FormattedString(fontSize=32, cmykFill=(1, 0, 1, 0), align="center")
t += "CMYK"
t.fill(0)
t.fontSize(18)
t += " centered"

w, h = t.size()

fill(None)
stroke(0.75)
rect(180 - w / 2, 76, w, h)

text(t, (180, 96))

t.clear()
t.align("right")
t.cmykFill(0, 1, 1, 0)
t.fontSize(26)
t += "right"

text(t, (330, 38))
