import os
import math
from io import BytesIO
import skia


class ImageObject:
    def __init__(self, path=None):
        self._image = None
        self._path = None
        self._offset = (0, 0)
        if path is not None:
            self.open(path)

    def open(self, path):
        self._path = os.fspath(path)
        self._image = skia.Image.open(self._path)

    def size(self):
        image = self._skiaImage()
        return image.width(), image.height()

    def offset(self):
        return self._offset

    def copy(self):
        other = type(self)()
        other._image = self._image
        other._path = self._path
        other._offset = self._offset
        return other

    def clearFilters(self):
        if self._path is not None:
            self.open(self._path)
        self._offset = (0, 0)
        return None

    def gaussianBlur(self, radius=10.0):
        from PIL import Image
        from PIL import ImageFilter

        image = self._pilImage()
        radius = float(radius)
        pad = max(0, int(math.ceil(radius * 3)))
        padded = Image.new(
            "RGBA",
            (image.width + pad * 2, image.height + pad * 2),
            (0, 0, 0, 0),
        )
        padded.alpha_composite(image, (pad, pad))
        blurred = padded.filter(ImageFilter.GaussianBlur(radius))
        self._setPILImage(blurred)
        x, y = self._offset
        self._offset = (x - pad, y - pad)

    def boxBlur(self, radius=10.0):
        from PIL import ImageFilter

        self._filter(ImageFilter.BoxBlur(float(radius)))

    def colorControls(self, saturation=1.0, brightness=0.0, contrast=1.0):
        from PIL import ImageEnhance

        image = self._pilImage()
        image = ImageEnhance.Color(image).enhance(float(saturation))
        image = ImageEnhance.Brightness(image).enhance(1 + float(brightness))
        image = ImageEnhance.Contrast(image).enhance(float(contrast))
        self._setPILImage(image)

    def colorInvert(self):
        from PIL import ImageOps

        image = self._pilImage()
        r, g, b, a = image.split()
        inverted = ImageOps.invert(image.convert("RGB")).convert("RGBA")
        inverted.putalpha(a)
        self._setPILImage(inverted)

    def photoEffectMono(self, extrapolate=False):
        self._monochrome()

    def photoEffectNoir(self, extrapolate=False):
        from PIL import ImageEnhance

        image = self._monochromeImage()
        image = ImageEnhance.Contrast(image).enhance(1.55)
        self._setPILImage(image)

    def sepiaTone(self, intensity=1.0):
        from PIL import Image

        image = self._pilImage()
        a = image.getchannel("A")
        gray = image.convert("L")
        sepia = Image.merge(
            "RGBA",
            (
                gray.point(lambda value: min(255, int(value * 1.12))),
                gray.point(lambda value: min(255, int(value * 0.88))),
                gray.point(lambda value: min(255, int(value * 0.58))),
                a,
            ),
        )
        self._setPILImage(_blendRGBA(image, sepia, intensity))

    def sharpenLuminance(self, sharpness=0.4, radius=1.69):
        from PIL import ImageFilter

        self._filter(
            ImageFilter.UnsharpMask(
                radius=float(radius),
                percent=max(0, int(float(sharpness) * 250)),
            )
        )

    def lockFocus(self):
        raise NotImplementedError("drawing into ImageObject is not supported yet")

    def unlockFocus(self):
        raise NotImplementedError("drawing into ImageObject is not supported yet")

    def _skiaImage(self):
        if self._image is None:
            raise ValueError("empty ImageObject")
        return self._image

    def _pilImage(self):
        from PIL import Image

        data = self._skiaImage().encodeToData(skia.kPNG, 100).bytes()
        return Image.open(BytesIO(data)).convert("RGBA")

    def _setPILImage(self, image):
        data = BytesIO()
        image.save(data, format="PNG")
        self._image = skia.Image.MakeFromEncoded(skia.Data.MakeWithCopy(data.getvalue()))

    def _filter(self, imageFilter):
        self._setPILImage(self._pilImage().filter(imageFilter))

    def _monochrome(self):
        self._setPILImage(self._monochromeImage())

    def _monochromeImage(self):
        image = self._pilImage()
        gray = image.convert("L").convert("RGBA")
        gray.putalpha(image.getchannel("A"))
        return gray


def _blendRGBA(image1, image2, amount):
    from PIL import Image

    amount = max(0, min(1, float(amount)))
    return Image.blend(image1.convert("RGBA"), image2.convert("RGBA"), amount)
