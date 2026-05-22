size(420, 240)

fill(1)
rect(0, 0, width(), height())

fontSize(20)
lineHeight(24)

box1 = (40, 130, 92, 76)
box2 = (170, 130, 92, 76)
box3 = (300, 82, 92, 124)

fill(None)
stroke(0.7)
rect(*box1)
rect(*box2)
rect(*box3)

stroke(None)
fill(0.7)
text("off", (40, 212))
text("on", (170, 212))
text("formatted", (300, 212))

fill(0)
hyphenation(False)
textBox("supercalifragilistic", box1)

hyphenation(True)
textBox("supercalifragilistic", box2)

t = FormattedString(fontSize=20, lineHeight=24, fill=(0.1, 0.25, 0.65))
t.hyphenation(True)
t += "supercalifragilistic"
overflow = textBox(t, box3)
assert isinstance(overflow, FormattedString)
