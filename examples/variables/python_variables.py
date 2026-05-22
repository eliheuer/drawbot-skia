size(520, 360)

columns = 7
rows = 4
margin = 52
gap = 12
tile = (width() - margin * 2 - gap * (columns - 1)) / columns

fill(0.98)
rect(0, 0, width(), height())

for row in range(rows):
    for column in range(columns):
        x = margin + column * (tile + gap)
        y = 96 + row * (tile + gap)
        t = (row * columns + column) / (rows * columns - 1)
        fill(0.1 + t * 0.75, 0.35, 0.8 - t * 0.55)
        oval(x, y, tile, tile)

fill(0.08)
fontSize(20)
text("Python variables driving a grid", (52, 48))
