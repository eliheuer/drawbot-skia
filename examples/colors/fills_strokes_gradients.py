size(560, 360)

linearGradient(
    (0, 0),
    (width(), height()),
    [(0.92, 0.96, 1), (1, 0.98, 0.86), (0.98, 0.9, 0.92)],
    [0, 0.55, 1],
)
rect(0, 0, width(), height())

stroke(0.05)
strokeWidth(4)
fill(0.9, 0.18, 0.12, 0.9)
rect(64, 100, 120, 160)

cmykFill(0.85, 0.05, 0.35, 0.02, 0.9)
stroke(0.04, 0.22, 0.18)
oval(220, 100, 160, 160)

fill(None)
stroke(0.1, 0.1, 0.7, 0.85)
strokeWidth(18)
line((420, 118), (500, 242))

stroke(None)
fill(0.08)
fontSize(18)
text("RGB fill", (72, 70))
text("CMYK fill", (244, 70))
text("alpha stroke", (404, 70))
