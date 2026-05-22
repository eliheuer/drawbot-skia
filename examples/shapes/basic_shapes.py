size(520, 360)

fill(0.96)
rect(0, 0, width(), height())

fill(0.08, 0.18, 0.32)
stroke(None)
rect(52, 92, 120, 170)

fill(0.95, 0.34, 0.2, 0.85)
oval(132, 152, 160, 160)

stroke(0.1, 0.1, 0.1)
strokeWidth(10)
line((330, 104), (462, 250))

fill(0.1, 0.62, 0.48)
stroke(0.02, 0.22, 0.18)
strokeWidth(5)
polygon((342, 92), (466, 104), (444, 214), (370, 270), close=True)

fontSize(20)
fill(0.1)
stroke(None)
text("rect, oval, line, polygon", (52, 42))
