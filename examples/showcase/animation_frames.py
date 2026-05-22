size(520, 360)

for frame in range(4):
    if frame:
        newPage(520, 360)
    frameDuration(0.18)
    fill(0.96)
    rect(0, 0, width(), height())
    fill(0.08)
    fontSize(28)
    text("Animation frame output", (48, 292))
    x = 80 + frame * 96
    y = 144
    fill(0.12, 0.2, 0.34)
    rect(72, 132, 376, 38)
    fill(0.95, 0.34, 0.16)
    oval(x, y, 52, 52)
    fill(0.08)
    fontSize(16)
    text(f"frame {frame + 1} / 4, duration 0.18s", (48, 58))
