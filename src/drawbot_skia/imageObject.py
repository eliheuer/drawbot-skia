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

    def crop(
        self,
        rectangle=(
            -8.988465674311579e307,
            -8.988465674311579e307,
            1.7976931348623157e308,
            1.7976931348623157e308,
        ),
    ):
        x, y, width, height = rectangle
        image = self._pilImage()
        left = max(0, int(round(x)))
        top = max(0, int(round(y)))
        right = min(image.width, int(round(x + width)))
        bottom = min(image.height, int(round(y + height)))
        self._setPILImage(image.crop((left, top, right, bottom)))
        offsetX, offsetY = self._offset
        self._offset = (offsetX + left, offsetY + top)

    def lanczosScaleTransform(self, scale=1.0, aspectRatio=1.0):
        from PIL import Image

        image = self._pilImage()
        scale = float(scale)
        aspectRatio = float(aspectRatio)
        width = max(1, int(round(image.width * scale * aspectRatio)))
        height = max(1, int(round(image.height * scale)))
        self._setPILImage(image.resize((width, height), Image.Resampling.LANCZOS))

    def gammaAdjust(self, power=1.0):
        power = float(power)
        if power <= 0:
            return
        image = self._pilImage()
        a = image.getchannel("A")
        adjusted = image.convert("RGB").point(
            lambda value: round(((value / 255) ** power) * 255)
        ).convert("RGBA")
        adjusted.putalpha(a)
        self._setPILImage(adjusted)

    def exposureAdjust(self, EV=0.0):
        from PIL import ImageEnhance

        image = self._pilImage()
        self._setPILImage(ImageEnhance.Brightness(image).enhance(2 ** float(EV)))

    def hueAdjust(self, angle=0.0):
        from PIL import Image

        image = self._pilImage()
        a = image.getchannel("A")
        hueShift = int(round((float(angle) % 360) / 360 * 255))
        h, s, v = image.convert("HSV").split()
        h = h.point(lambda value: (value + hueShift) % 256)
        adjusted = Image.merge("HSV", (h, s, v)).convert("RGBA")
        adjusted.putalpha(a)
        self._setPILImage(adjusted)

    def vibrance(self, amount=0.0):
        from PIL import ImageEnhance

        image = self._pilImage()
        self._setPILImage(ImageEnhance.Color(image).enhance(1 + float(amount)))

    def temperatureAndTint(self, neutral=(6500.0, 0.0), targetNeutral=(6500.0, 0.0)):
        image = self._pilImage()
        neutralTemperature, neutralTint = neutral
        targetTemperature, targetTint = targetNeutral
        temperatureDelta = (float(targetTemperature) - float(neutralTemperature)) / 6500
        tintDelta = (float(targetTint) - float(neutralTint)) / 150
        r, g, b, a = image.split()
        r = r.point(lambda value: _clampByte(value * (1 + temperatureDelta * 0.2)))
        b = b.point(lambda value: _clampByte(value * (1 - temperatureDelta * 0.2)))
        g = g.point(lambda value: _clampByte(value * (1 + tintDelta * 0.2)))
        self._setPILImage(_mergeRGBA(r, g, b, a))

    def whitePointAdjust(self, color=(1.0, 1.0, 1.0, 1.0)):
        image = self._pilImage()
        cr, cg, cb, ca = _colorToRGBABytes(color)
        r, g, b, a = image.split()
        r = r.point(lambda value: _clampByte(value * cr / 255))
        g = g.point(lambda value: _clampByte(value * cg / 255))
        b = b.point(lambda value: _clampByte(value * cb / 255))
        a = a.point(lambda value: _clampByte(value * ca / 255))
        self._setPILImage(_mergeRGBA(r, g, b, a))

    def colorMonochrome(self, color=(0.6, 0.45, 0.3, 1.0), intensity=1.0):
        from PIL import Image

        image = self._pilImage()
        gray = image.convert("L")
        cr, cg, cb, ca = _colorToRGBABytes(color)
        tinted = Image.merge(
            "RGBA",
            (
                gray.point(lambda value: _clampByte(value * cr / 255)),
                gray.point(lambda value: _clampByte(value * cg / 255)),
                gray.point(lambda value: _clampByte(value * cb / 255)),
                image.getchannel("A").point(lambda value: _clampByte(value * ca / 255)),
            ),
        )
        self._setPILImage(_blendRGBA(image, tinted, intensity))

    def falseColor(self, color0=(0.3, 0.0, 0.0, 1.0), color1=(1.0, 0.9, 0.8, 1.0)):
        from PIL import Image

        image = self._pilImage()
        gray = image.convert("L")
        c0 = _colorToRGBABytes(color0)
        c1 = _colorToRGBABytes(color1)
        channels = []
        for low, high in zip(c0, c1):
            channels.append(
                gray.point(
                    lambda value, low=low, high=high: _clampByte(
                        low + (high - low) * value / 255
                    )
                )
            )
        channels[3] = image.getchannel("A")
        self._setPILImage(Image.merge("RGBA", tuple(channels)))

    def colorPosterize(self, levels=6.0):
        levels = max(2, int(round(float(levels))))
        step = 255 / (levels - 1)
        image = self._pilImage()
        a = image.getchannel("A")
        posterized = image.convert("RGB").point(
            lambda value: _clampByte(round(value / step) * step)
        ).convert("RGBA")
        posterized.putalpha(a)
        self._setPILImage(posterized)

    def minimumComponent(self):
        from PIL import Image

        image = self._pilImage()
        r, g, b, a = image.split()
        minimum = Image.merge("RGB", (r, g, b)).convert("L", matrix=(1, 0, 0, 0))
        minimum = Image.eval(minimum, lambda _: 0)
        for channel in (r, g, b):
            minimum = _lighterOrDarker(minimum, channel, darker=True)
        self._setPILImage(_mergeRGBA(minimum, minimum, minimum, a))

    def maximumComponent(self):
        from PIL import Image

        image = self._pilImage()
        r, g, b, a = image.split()
        maximum = Image.eval(r, lambda _: 0)
        for channel in (r, g, b):
            maximum = _lighterOrDarker(maximum, channel, darker=False)
        self._setPILImage(_mergeRGBA(maximum, maximum, maximum, a))

    def maskToAlpha(self):
        image = self._pilImage()
        alpha = image.convert("L")
        white = alpha.point(lambda value: 255)
        self._setPILImage(_mergeRGBA(white, white, white, alpha))

    def unsharpMask(self, radius=2.5, intensity=0.5):
        from PIL import ImageFilter

        self._filter(
            ImageFilter.UnsharpMask(
                radius=float(radius),
                percent=max(0, int(float(intensity) * 250)),
            )
        )

    def noiseReduction(self, noiseLevel=0.02, sharpness=0.4):
        from PIL import ImageFilter

        image = self._pilImage()
        radius = max(1, int(round(float(noiseLevel) * 50)))
        image = image.filter(ImageFilter.MedianFilter(size=radius * 2 + 1))
        image = image.filter(
            ImageFilter.UnsharpMask(percent=max(0, int(float(sharpness) * 250)))
        )
        self._setPILImage(image)

    def edges(self, intensity=1.0):
        from PIL import ImageFilter

        image = self._pilImage()
        edge = image.filter(ImageFilter.FIND_EDGES)
        self._setPILImage(_blendRGBA(image, edge, intensity))

    def edgeWork(self, radius=3.0):
        from PIL import ImageFilter

        self._setPILImage(self._pilImage().filter(ImageFilter.FIND_EDGES))

    def pixellate(self, center=(150.0, 150.0), scale=8.0):
        from PIL import Image

        image = self._pilImage()
        scale = max(1, int(round(float(scale))))
        small = image.resize(
            (max(1, image.width // scale), max(1, image.height // scale)),
            Image.Resampling.BOX,
        )
        self._setPILImage(small.resize(image.size, Image.Resampling.NEAREST))

    def motionBlur(self, radius=20.0, angle=0.0):
        from PIL import Image
        from PIL import ImageFilter

        radius = max(1, int(round(float(radius))))
        size = radius * 2 + 1
        kernel = Image.new("L", (size, size), 0)
        pixels = kernel.load()
        center = radius
        radians = math.radians(float(angle))
        dx = math.cos(radians)
        dy = math.sin(radians)
        for index in range(size):
            x = int(round(center + (index - center) * dx))
            y = int(round(center + (index - center) * dy))
            if 0 <= x < size and 0 <= y < size:
                pixels[x, y] = 255
        values = [value / 255 for value in kernel.tobytes()]
        total = sum(values) or 1
        self._filter(ImageFilter.Kernel((size, size), [value / total for value in values]))

    def zoomBlur(self, center=(150.0, 150.0), amount=20.0):
        from PIL import Image

        image = self._pilImage()
        amount = max(1, int(round(float(amount))))
        accumulator = Image.new("RGBA", image.size, (0, 0, 0, 0))
        samples = 8
        for sample in range(samples):
            scale = 1 + (amount / 100) * (sample / (samples - 1))
            resized = image.resize(
                (
                    max(1, int(round(image.width * scale))),
                    max(1, int(round(image.height * scale))),
                ),
                Image.Resampling.BICUBIC,
            )
            left = (resized.width - image.width) // 2
            top = (resized.height - image.height) // 2
            accumulator = _blendRGBA(
                accumulator,
                resized.crop((left, top, left + image.width, top + image.height)),
                1 / (sample + 1),
            )
        self._setPILImage(accumulator)

    def vignette(self, intensity=0.0, radius=1.0):
        self.vignetteEffect(intensity=intensity, radius=max(self.size()) * float(radius))

    def vignetteEffect(
        self, center=(150.0, 150.0), radius=150.0, intensity=1.0, falloff=0.5
    ):
        from PIL import Image

        image = self._pilImage()
        cx, cy = center
        radius = max(1, float(radius))
        falloff = max(0.0001, float(falloff))
        mask = Image.new("L", image.size, 0)
        pixels = mask.load()
        for y in range(image.height):
            for x in range(image.width):
                distance = math.hypot(x - cx, y - cy)
                amount = max(0, min(1, (distance - radius * (1 - falloff)) / (radius * falloff)))
                pixels[x, y] = _clampByte(amount * 255 * float(intensity))
        dark = Image.new("RGBA", image.size, (0, 0, 0, 255))
        self._setPILImage(Image.composite(dark, image, mask))

    def bloom(self, radius=10.0, intensity=0.5):
        from PIL import ImageFilter

        image = self._pilImage()
        blurred = image.filter(ImageFilter.GaussianBlur(float(radius)))
        self._setPILImage(_screenBlend(image, blurred, intensity))

    def gloom(self, radius=10.0, intensity=0.5):
        from PIL import ImageFilter

        image = self._pilImage()
        blurred = image.filter(ImageFilter.GaussianBlur(float(radius)))
        self._setPILImage(_blendRGBA(image, blurred, intensity))

    def photoEffectMono(self, extrapolate=False):
        self._monochrome()

    def photoEffectNoir(self, extrapolate=False):
        from PIL import ImageEnhance

        image = self._monochromeImage()
        image = ImageEnhance.Contrast(image).enhance(1.55)
        self._setPILImage(image)

    def photoEffectTonal(self, extrapolate=False):
        self._monochrome()

    def photoEffectFade(self, extrapolate=False):
        from PIL import ImageEnhance

        image = self._pilImage()
        image = ImageEnhance.Color(image).enhance(0.65)
        image = ImageEnhance.Contrast(image).enhance(0.85)
        self._setPILImage(image)

    def photoEffectInstant(self, extrapolate=False):
        self.sepiaTone(0.45)
        from PIL import ImageEnhance

        self._setPILImage(ImageEnhance.Color(self._pilImage()).enhance(1.15))

    def photoEffectProcess(self, extrapolate=False):
        from PIL import ImageEnhance

        image = self._pilImage()
        image = ImageEnhance.Color(image).enhance(1.35)
        image = ImageEnhance.Contrast(image).enhance(1.1)
        self._setPILImage(image)

    def photoEffectTransfer(self, extrapolate=False):
        self.sepiaTone(0.25)
        from PIL import ImageEnhance

        self._setPILImage(ImageEnhance.Contrast(self._pilImage()).enhance(0.9))

    def photoEffectChrome(self, extrapolate=False):
        from PIL import ImageEnhance

        image = self._pilImage()
        image = ImageEnhance.Color(image).enhance(1.4)
        image = ImageEnhance.Contrast(image).enhance(1.25)
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


def _mergeRGBA(r, g, b, a):
    from PIL import Image

    return Image.merge("RGBA", (r, g, b, a))


def _clampByte(value):
    return max(0, min(255, int(round(value))))


def _colorToRGBABytes(color):
    values = tuple(color)
    if len(values) == 1:
        values = (values[0], values[0], values[0], 1)
    elif len(values) == 2:
        values = (values[0], values[0], values[0], values[1])
    elif len(values) == 3:
        values = (*values, 1)
    return tuple(_clampByte(value * 255) for value in values[:4])


def _lighterOrDarker(image1, image2, darker=False):
    from PIL import ImageChops

    if darker:
        return ImageChops.darker(image1, image2)
    return ImageChops.lighter(image1, image2)


def _screenBlend(image1, image2, amount):
    from PIL import ImageChops

    screened = ImageChops.screen(image1.convert("RGBA"), image2.convert("RGBA"))
    return _blendRGBA(image1, screened, amount)
