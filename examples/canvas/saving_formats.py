size(640, 400)

fill(0.97)
rect(0, 0, width(), height())

fill(0.08)
fontSize(34)
text("Saving and export targets", (48, 318))

formats = ["PNG", "JPG", "PDF", "SVG", "MP4", "GIF"]
for index, label in enumerate(formats):
    x = 56 + (index % 3) * 188
    y = 198 - (index // 3) * 88
    fill(0.88, 0.93, 0.95)
    stroke(0.68)
    strokeWidth(1)
    rect(x, y, 138, 58)
    stroke(None)
    fill(0.12, 0.2, 0.32)
    fontSize(25)
    text(label, (x + 28, y + 17))

fill(0.08)
fontSize(15)
text("The runner saves this source as JPG for the visual docs.", (48, 54))
