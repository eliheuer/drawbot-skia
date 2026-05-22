size(520, 300)

fill(1)
rect(0, 0, width(), height())

source = ImageObject("../images/drawbot.png")
filters = [
    ("invert", "colorInvert"),
    ("mono", "photoEffectMono"),
    ("noir", "photoEffectNoir"),
    ("sepia", "sepiaTone"),
    ("blur", "boxBlur"),
    ("sharpen", "sharpenLuminance"),
]

fontSize(12)
for index, (label, methodName) in enumerate(filters):
    im = source.copy()
    method = getattr(im, methodName)
    if methodName == "boxBlur":
        method(radius=4)
    else:
        method()
    x = 28 + (index % 3) * 162
    y = 138 - (index // 3) * 118
    fill(0.78)
    rect(x - 6, y - 6, 142, 118)
    with savedState():
        translate(x, y)
        scale(0.22)
        image(im, (0, 0))
    fill(0)
    text(label, (x, y + 116))
