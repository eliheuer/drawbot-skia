size(420, 280)
fill(1)
rect(0, 0, width(), height())

box = (40, 120, 160, 90)
overflowBox = (240, 70, 140, 140)

fill(None)
stroke(0.7)
rect(*box)
rect(*overflowBox)

t = FormattedString(fontSize=22, lineHeight=28)
t.fill(0)
t += "Formatted "
t.fill(1, 0, 0)
t += "text wraps "
t.fill(0, 0.2, 1)
t += "with styles into a rectangle and returns styled overflow."

stroke(None)
overflow = textBox(t, box)

assert isinstance(overflow, FormattedString)
assert str(overflow)

textBox(overflow, overflowBox, align="center")
