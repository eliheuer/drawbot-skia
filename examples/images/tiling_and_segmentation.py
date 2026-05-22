size(820, 460)

source = ImageObject()
source.checkerboardGenerator(
    (190, 190),
    color0=(0.08, 0.18, 0.34, 1),
    color1=(0.94, 0.92, 0.78, 1),
    width=26,
)

tile = source.copy()
tile.triangleTile(center=(95, 95), angle=0.35, width=64)

segmentation = source.copy()
segmentation.personSegmentation(qualityLevel=0.85)

saliency = source.copy()
saliency.saliencyMapFilter()

fill(0.96)
rect(0, 0, width(), height())

image(source, (56, 146))
image(tile, (252, 146))
image(segmentation, (448, 146))
image(saliency, (644, 146))

fill(0.08)
fontSize(29)
text("Tiling and segmentation filters", (56, 370))
fontSize(14)
text("source", (56, 112))
text("triangleTile", (252, 112))
text("personSegmentation", (448, 112))
text("saliencyMapFilter", (644, 112))
