size(680, 420)

font_path = "../../tests/fonts/MutatorSans.ttf"

fill(0.98)
rect(0, 0, width(), height())

fill(0.08)
font(font_path)
fontSize(40)
text("Variable font settings", (54, 334))

for index, value in enumerate([0, 250, 500, 750, 1000]):
    y = 260 - index * 46
    font(font_path)
    fontSize(34)
    fontVariations(wght=value, wdth=500)
    fill(0.08 + index * 0.08, 0.18, 0.34)
    text("MutatorSans", (54, y))
    font("Helvetica")
    fontSize(13)
    fill(0.34)
    text(f"wght={value}", (388, y + 9))

fontVariations(resetVariations=True)
fill(0.08)
font("Helvetica")
fontSize(14)
text("Uses the local test variable font as a deterministic fixture.", (54, 42))
