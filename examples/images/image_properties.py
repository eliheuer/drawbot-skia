size(620, 380)

sample = ImageObject()
sample.linearGradient((180, 180), (0, 0), (180, 180), (0.08, 0.18, 0.34, 1), (0.95, 0.34, 0.16, 1))

sample_width, sample_height = imageSize(sample)
sample_color = imagePixelColor(sample, (135, 45))

fill(0.96)
rect(0, 0, width(), height())
image(sample, (72, 118))

fill(0.08)
fontSize(26)
text("Image properties", (312, 254))

fontSize(17)
text(f"imageSize: {sample_width} x {sample_height}", (312, 214))
text(
    "imagePixelColor: "
    + ", ".join(str(round(channel, 2)) for channel in sample_color),
    (312, 184),
)

fill(*sample_color)
stroke(0.08)
strokeWidth(2)
oval(312, 128, 48, 48)

fill(0.08)
stroke(None)
fontSize(14)
text("A generated ImageObject can be measured, sampled, and drawn.", (72, 62))
