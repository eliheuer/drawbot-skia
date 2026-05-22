size(760, 430)

arabic_font = "../../tests/fonts/IBMPlexSansArabic-Regular.otf"
latin_font = "../../tests/fonts/MutatorSans.ttf"

fill(0.97)
rect(0, 0, width(), height())

fill(0.08)
font("Helvetica")
fontSize(31)
text("Text shaping and variable fonts", (54, 344))

font(arabic_font)
fontSize(54)
fill(0.12, 0.2, 0.34)
text("مرحبا بالعالم", (54, 246))

font(latin_font)
fontSize(72)
fontVariations(wght=920, wdth=780)
fill(0.95, 0.34, 0.16)
text("Variable", (54, 142))

font("Helvetica")
fontSize(16)
fill(0.08)
text("Showcase: HarfBuzz shaping plus local variable-font axis support.", (54, 64))
