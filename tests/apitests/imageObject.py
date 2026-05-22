size(320, 210)

fill(1)
rect(0, 0, width(), height())

im = ImageObject("../images/drawbot.png")
assert im.size() == (512, 512)
assert im.offset() == (0, 0)

copy = im.copy()

with savedState():
    translate(24, 32)
    scale(0.25)
    image(im, (0, 0))

with savedState():
    translate(160, 52)
    scale(0.25)
    image(copy, (0, 0), alpha=0.55)

fill(0)
fontSize(18)
text("ImageObject", (24, 174))
