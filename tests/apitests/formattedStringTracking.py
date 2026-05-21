size(420, 170)

fill(1)
rect(0, 0, width(), height())

baseline = 86
stroke(0.85)
line((20, baseline), (400, baseline))

t = FormattedString(fontSize=44, fill=(0.05,))
t += "A"
t.tracking(14)
t += "spaced"
t.tracking(0)
t.baselineShift(18)
t.fill(1, 0, 0)
t += "up"
t.baselineShift(-14)
t.fill(0, 0.2, 1)
t += "down"

text(t, (28, baseline))

tracked = FormattedString("TRACK", fontSize=24, tracking=8, fill=(0.2,))
text(tracked, (28, 34))
