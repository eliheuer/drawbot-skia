size(700, 440)

copy = (
    "Text measurement APIs expose the geometry behind wrapped text. "
    "This fixture draws a text box, its baselines, and character bounds."
)
box = (60, 122, 288, 166)

fill(0.98)
rect(0, 0, width(), height())

font("Helvetica")
fontSize(16)
lineHeight(22)

overflow = textBox(copy, box)
baselines = textBoxBaselines(copy, box)
bounds = textBoxCharacterBounds(copy, box)
measured = textSize(copy, width=box[2])

stroke(0.66)
strokeWidth(1)
fill(None)
rect(*box)

stroke(0.1, 0.42, 0.78)
strokeWidth(1)
for x, y in baselines:
    line((box[0], y), (box[0] + box[2], y))

stroke(0.95, 0.34, 0.16, 0.36)
for item in bounds[:34]:
    x, y, w, h = item.bounds
    rect(x, y, w, h)

fill(0.08)
stroke(None)
fontSize(30)
text("Text metrics", (60, 344))
fontSize(15)
text(f"textSize width constraint: {int(measured[0])} x {int(measured[1])}", (396, 244))
text(f"baselines: {len(baselines)}", (396, 214))
text(f"character bounds: {len(bounds)}", (396, 184))
text(f"overflow characters: {len(overflow)}", (396, 154))
