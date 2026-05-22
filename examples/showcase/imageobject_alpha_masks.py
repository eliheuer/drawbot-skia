size(720, 420)

fill(0.96)
rect(0, 0, width(), height())

source = ImageObject()
source.linearGradient((180, 180), (0, 0), (180, 180), (0.95, 0.34, 0.12, 1), (1, 0.9, 0.12, 1))

mask = ImageObject()
mask.radialGradient((180, 180), (90, 90), 0, 92, (1, 1, 1, 1), (1, 1, 1, 0))

blurred = source.copy()
blurred.maskedVariableBlur(radius=16, mask=mask)

alpha = mask.copy()
alpha.maskToAlpha()

image(source, (70, 142))
image(alpha, (270, 142))
image(blurred, (470, 142))

fill(0.08)
fontSize(17)
text("source", (70, 104))
text("alpha-scaled mask", (270, 104))
text("masked variable blur", (470, 104))

fontSize(14)
text("Showcase: alpha-aware ImageObject mask behavior added in this fork.", (70, 52))
