size(640, 420)

fill(0.98)
rect(0, 0, width(), height())

fill(0.08)
font("Helvetica")
fontSize(36)
text("Text properties", (56, 342))

fontSize(19)
lineHeight(24)
tracking(1.5)
hyphenation(True)
textBox(
    "Aligned text boxes use width, height, line height, tracking, and hyphenation settings.",
    (56, 206, 222, 92),
    align="left",
)

stroke(0.75)
strokeWidth(1)
fill(None)
rect(56, 206, 222, 92)

fill(0.12, 0.2, 0.34)
fontSize(28)
tracking(4)
underline(True)
text("tracking + underline", (332, 258))
underline(False)

fill(0.95, 0.34, 0.16)
fontSize(22)
baselineShift(8)
text("raised baseline", (332, 198))
baselineShift(0)

fill(0.08)
fontSize(15)
tracking(0)
text("font, fontSize, lineHeight, tracking, baselineShift, underline", (56, 54))
