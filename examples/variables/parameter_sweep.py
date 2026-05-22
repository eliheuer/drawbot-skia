size(640, 400)

radius_values = [18, 30, 42, 54, 66]
angle = 18

fill(0.97)
rect(0, 0, width(), height())

for index, radius in enumerate(radius_values):
    x = 96 + index * 112
    y = 196
    save()
    translate(x, y)
    rotate(angle * index)
    fill(0.1, 0.22 + index * 0.08, 0.68 - index * 0.08)
    rect(-radius, -radius, radius * 2, radius * 2)
    restore()
    fill(0.08)
    fontSize(13)
    text(f"r={radius}", (x - 20, 104))

fill(0.08)
fontSize(22)
text("Parameter sweep with ordinary Python lists", (56, 48))
