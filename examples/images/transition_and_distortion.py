size(760, 430)

source = ImageObject()
source.checkerboardGenerator(
    (180, 180),
    color0=(0.06, 0.18, 0.34, 1),
    color1=(0.92, 0.94, 0.86, 1),
    width=24,
)

target = ImageObject()
target.radialGradient((180, 180), (90, 90), 0, 100, (0.95, 0.34, 0.16, 1), (0.1, 0.55, 0.42, 1))

transition = source.copy()
transition.copyMachineTransition(
    target,
    extent=(0, 0, 180, 180),
    color=(0.6, 1, 0.82, 1),
    time=0.56,
    angle=0.35,
    width=52,
    opacity=1.1,
)

distorted = target.copy()
distorted.twirlDistortion(center=(90, 90), radius=92, angle=3.2)

fill(0.96)
rect(0, 0, width(), height())

image(source, (64, 140))
image(transition, (292, 140))
image(distorted, (520, 140))

fill(0.08)
fontSize(28)
text("ImageObject transitions and distortions", (64, 344))
fontSize(15)
text("source", (64, 104))
text("copyMachineTransition", (292, 104))
text("twirlDistortion", (520, 104))
