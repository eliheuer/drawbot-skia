size(620, 380)

fill(0.98, 0.97, 0.94)
rect(0, 0, width(), height())

fill(0.08)
font("Helvetica")
fontSize(44)
text("DrawBot text", (56, 286))

fontSize(17)
copy = (
    "The text API supports direct drawing, text boxes, alignment, and "
    "FormattedString runs with separate styling."
)
textBox(copy, (56, 148, 236, 104), align="left")

formatted = FormattedString()
formatted.font("Helvetica")
formatted.fontSize(24)
formatted.fill(0.1, 0.22, 0.45)
formatted.append("Formatted")
formatted.fill(0.9, 0.28, 0.16)
formatted.append(" String")
formatted.fontSize(15)
formatted.fill(0.12)
formatted.append("\nwith mixed color and size")

textBox(formatted, (340, 130, 220, 120))

stroke(0.7)
strokeWidth(1)
fill(None)
rect(56, 148, 236, 104)
rect(340, 130, 220, 120)
