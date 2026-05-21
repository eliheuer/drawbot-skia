size(360, 190)

fill(1)
rect(0, 0, width(), height())

t = FormattedString(fontSize=48)
assert t.fontContainsCharacters("DrawBot")
assert not t.fontContainsCharacters("\u0378")
assert t.fontContainsGlyph("A")
assert t.fontAscender() > 0
assert t.fontDescender() < 0
assert t.fontLineHeight() > 0

x = 40
baseline = 76
ascender = t.fontAscender()
descender = t.fontDescender()
xHeight = t.fontXHeight()
capHeight = t.fontCapHeight()

stroke(0.85)
line((x, baseline), (320, baseline))
stroke(1, 0, 0)
line((x, baseline + ascender), (320, baseline + ascender))
stroke(0, 0, 1)
line((x, baseline + descender), (320, baseline + descender))
stroke(0, 0.6, 0)
line((x, baseline + xHeight), (320, baseline + xHeight))
stroke(1, 0.5, 0)
line((x, baseline + capHeight), (320, baseline + capHeight))

fill(0)
stroke(None)
text("Hg", (x, baseline))

fontSize(11)
text("ascender", (x, baseline + ascender + 4))
text("descender", (x, baseline + descender - 12))
