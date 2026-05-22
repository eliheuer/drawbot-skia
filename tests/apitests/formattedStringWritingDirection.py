size(460, 180)

fill(1)
rect(0, 0, width(), height())

fontPath = "../fonts/IBMPlexSansArabic-Regular.otf"

fill(0.85)
rect(28, 118, 404, 1)
rect(28, 58, 404, 1)

ltr = FormattedString("ABC 123", font=fontPath, fontSize=36, fill=(0.05,))
rtl = FormattedString(font=fontPath, fontSize=36, fill=(1, 0, 0))
rtl.writingDirection("RTL")
rtl += "ABC 123"

text(ltr, (28, 126))
text(rtl, (28, 66))
