size(430, 260)

fill(1)
rect(0, 0, width(), height())

x, y, w, h = 36, 32, 320, 190

fill(0.96)
stroke(0.75)
rect(x, y, w, h)

stroke(1, 0, 0)
line((x + 42, y), (x + 42, y + h))
stroke(1, 0.75, 0)
line((x + 86, y), (x + 86, y + h))
stroke(0, 0, 1)
line((x + w - 40, y), (x + w - 40, y + h))

txt = FormattedString(fontSize=15, lineHeight=20, fill=(0.05,))
txt += "This first paragraph uses the full box width and wraps normally."
txt += "\n"
txt.fontSize(13)
txt.lineHeight(18)
txt.indent(42)
txt.firstLineIndent(44)
txt.tailIndent(-40)
txt.paragraphTopSpacing(7)
txt.paragraphBottomSpacing(9)
txt.fill(0.1, 0.25, 0.65)
txt += "The second paragraph has a wider first line indent, a left indent, and a negative tail indent."
txt += "\n"
txt.fontSize(15)
txt.lineHeight(20)
txt.indent(None)
txt.firstLineIndent(None)
txt.tailIndent(None)
txt.paragraphTopSpacing(None)
txt.paragraphBottomSpacing(None)
txt.fill(0.05)
txt += "The final paragraph resets those values."

overflow = textBox(txt, (x, y, w, h))
assert not overflow
