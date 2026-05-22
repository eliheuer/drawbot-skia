size(520, 190)

fill(1)
rect(0, 0, width(), height())

tabStops = ((120, "left"), (220, "center"), (330, "right"), (430, "."))
tabs(*tabStops)
fontSize(18)
lineHeight(28)

stroke(0.85)
for x, alignment in tabStops:
    line((x, 28), (x, 168))

fill(0)
text("item\tleft\tcenter\tright\t12.30", (28, 148))
text("item\tA\tB\tC\t7.5", (28, 120))

fs = FormattedString(fontSize=18, fill=(0.1, 0.25, 0.65))
fs.tabs(*tabStops)
fs += "styled\tleft\tcenter\tright\t3.14"
text(fs, (28, 78))

tabs(None)
fill(0.65)
text("tabs cleared\tplain", (28, 40))
