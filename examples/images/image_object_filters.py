size(620, 380)

fill(0.95)
rect(0, 0, width(), height())

source = ImageObject()
source.checkerboardGenerator(
    size=(180, 180),
    color0=(0.04, 0.18, 0.34, 1),
    color1=(0.92, 0.94, 0.86, 1),
    width=28,
    sharpness=1,
)

filtered = source.copy()
filtered.kaleidoscope(count=8, center=(90, 90), angle=0)
filtered.bloom(radius=8, intensity=0.65)

image(source, (72, 126))
image(filtered, (368, 126))

fill(0.08)
fontSize(18)
text("ImageObject generator", (72, 82))
text("filtered copy", (368, 82))
