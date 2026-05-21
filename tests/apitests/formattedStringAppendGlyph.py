size(420, 170)

fill(1)
rect(0, 0, width(), height())

t = FormattedString(fontSize=72, fill=(0.05,))
t.appendGlyph("A", "ampersand")
t.fill(1, 0, 0)
t.appendGlyph(t.listFontGlyphNames().index("B"))

text(t, (36, 76))

fontSize(13)
fill(0.35)
text("A and ampersand by glyph name, B by glyph index", (36, 34))
