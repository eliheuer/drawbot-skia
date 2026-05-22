size(620, 380)

fill(0.96)
rect(0, 0, width(), height())

fill(0.12, 0.2, 0.34)
rect(70, 114, 150, 150)

blendMode("multiply")
fill(0.95, 0.35, 0.16, 0.82)
oval(150, 150, 156, 156)
blendMode("normal")

shadow((14, -14), 18, (0, 0, 0, 0.26))
fill(0.08, 0.58, 0.42)
rect(392, 120, 130, 130)
shadow(None)

opacity(0.42)
fill(0.1, 0.16, 0.7)
oval(358, 178, 112, 112)
opacity(1)

fill(0.08)
fontSize(18)
text("blendMode('multiply')", (70, 78))
text("shadow() and opacity()", (358, 78))
