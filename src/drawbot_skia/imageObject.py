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

    def constantColorGenerator(self, size, color=(1.0, 0.0, 0.0, 1.0)):
        from PIL import Image

        self._setPILImage(Image.new("RGBA", _normalizeSize(size), _colorToRGBABytes(color)))
        self._path = None
        self._offset = (0, 0)

    def checkerboardGenerator(
        self,
        size,
        center=(150.0, 150.0),
        color0=(1.0, 1.0, 1.0, 1.0),
        color1=(0.0, 0.0, 0.0, 1.0),
        width=80.0,
        sharpness=1.0,
    ):
        from PIL import Image

        widthPx, heightPx = _normalizeSize(size)
        cell = max(1, int(round(float(width))))
        c0 = _colorToRGBABytes(color0)
        c1 = _colorToRGBABytes(color1)
        image = Image.new("RGBA", (widthPx, heightPx))
        pixels = image.load()
        centerX, centerY = center
        for y in range(heightPx):
            for x in range(widthPx):
                index = (math.floor((x - centerX) / cell) + math.floor((y - centerY) / cell)) & 1
                pixels[x, y] = c1 if index else c0
        self._setPILImage(image)
        self._path = None
        self._offset = (0, 0)

    def stripesGenerator(
        self,
        size,
        center=(150.0, 150.0),
        color0=(1.0, 1.0, 1.0, 1.0),
        color1=(0.0, 0.0, 0.0, 1.0),
        width=80.0,
        sharpness=1.0,
    ):
        from PIL import Image

        widthPx, heightPx = _normalizeSize(size)
        stripeWidth = max(1, int(round(float(width))))
        c0 = _colorToRGBABytes(color0)
        c1 = _colorToRGBABytes(color1)
        image = Image.new("RGBA", (widthPx, heightPx))
        pixels = image.load()
        centerX, centerY = center
        for y in range(heightPx):
            for x in range(widthPx):
                pixels[x, y] = c1 if math.floor((x - centerX) / stripeWidth) & 1 else c0
        self._setPILImage(image)
        self._path = None
        self._offset = (0, 0)

    def randomGenerator(self, size):
        from PIL import Image

        width, height = _normalizeSize(size)
        self._setPILImage(Image.frombytes("RGBA", (width, height), os.urandom(width * height * 4)))
        self._path = None
        self._offset = (0, 0)

    def linearGradient(
        self,
        size,
        point0=(0.0, 0.0),
        point1=(200.0, 200.0),
        color0=(1.0, 1.0, 1.0, 1.0),
        color1=(0.0, 0.0, 0.0, 1.0),
    ):
        self._setPILImage(_linearGradientImage(size, point0, point1, color0, color1))
        self._path = None
        self._offset = (0, 0)

    def smoothLinearGradient(
        self,
        size,
        point0=(0.0, 0.0),
        point1=(200.0, 200.0),
        color0=(1.0, 1.0, 1.0, 1.0),
        color1=(0.0, 0.0, 0.0, 1.0),
    ):
        self.linearGradient(size, point0, point1, color0, color1)

    def radialGradient(
        self,
        size,
        center=(150.0, 150.0),
        radius0=5.0,
        radius1=100.0,
        color0=(1.0, 1.0, 1.0, 1.0),
        color1=(0.0, 0.0, 0.0, 1.0),
    ):
        self._setPILImage(_radialGradientImage(size, center, radius0, radius1, color0, color1))
        self._path = None
        self._offset = (0, 0)

    def gaussianGradient(
        self,
        size,
        center=(150.0, 150.0),
        color0=(1.0, 1.0, 1.0, 1.0),
        color1=(0.0, 0.0, 0.0, 0.0),
        radius=300.0,
    ):
        self._setPILImage(_gaussianGradientImage(size, center, color0, color1, radius))
        self._path = None
        self._offset = (0, 0)

    def roundedRectangleGenerator(
        self,
        size,
        extent=(0.0, 0.0, 100.0, 100.0),
        radius=10.0,
        color=(1.0, 1.0, 1.0, 1.0),
    ):
        from PIL import Image
        from PIL import ImageDraw

        image = Image.new("RGBA", _normalizeSize(size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        x, y, width, height = extent
        draw.rounded_rectangle((x, y, x + width, y + height), radius=float(radius), fill=_colorToRGBABytes(color))
        self._setPILImage(image)
        self._path = None
        self._offset = (0, 0)

    def roundedRectangleStrokeGenerator(
        self,
        size,
        extent=(0.0, 0.0, 100.0, 100.0),
        radius=10.0,
        color=(1.0, 1.0, 1.0, 1.0),
        width=10.0,
    ):
        from PIL import Image
        from PIL import ImageDraw

        image = Image.new("RGBA", _normalizeSize(size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        x, y, rectWidth, rectHeight = extent
        draw.rounded_rectangle(
            (x, y, x + rectWidth, y + rectHeight),
            radius=float(radius),
            outline=_colorToRGBABytes(color),
            width=max(1, int(round(float(width)))),
        )
        self._setPILImage(image)
        self._path = None
        self._offset = (0, 0)

    def blurredRectangleGenerator(
        self,
        size,
        extent=(0.0, 0.0, 100.0, 100.0),
        sigma=10.0,
        color=(1.0, 1.0, 1.0, 1.0),
    ):
        from PIL import Image
        from PIL import ImageDraw
        from PIL import ImageFilter

        image = Image.new("RGBA", _normalizeSize(size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        x, y, width, height = extent
        draw.rectangle((x, y, x + width, y + height), fill=_colorToRGBABytes(color))
        self._setPILImage(image.filter(ImageFilter.GaussianBlur(float(sigma))))
        self._path = None
        self._offset = (0, 0)

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

    def colorClamp(
        self,
        minComponents=(0.0, 0.0, 0.0, 0.0),
        maxComponents=(1.0, 1.0, 1.0, 1.0),
    ):
        mins = _colorToRGBABytes(minComponents)
        maxes = _colorToRGBABytes(maxComponents)
        channels = []
        for channel, low, high in zip(self._pilImage().split(), mins, maxes):
            channels.append(channel.point(lambda value, low=low, high=high: max(low, min(high, value))))
        self._setPILImage(_mergeRGBA(*channels))

    def colorMatrix(
        self,
        RVector=(1.0, 0.0, 0.0, 0.0),
        GVector=(0.0, 1.0, 0.0, 0.0),
        BVector=(0.0, 0.0, 1.0, 0.0),
        AVector=(0.0, 0.0, 0.0, 1.0),
        biasVector=(0.0, 0.0, 0.0, 0.0),
    ):
        image = self._pilImage()
        vectors = (RVector, GVector, BVector, AVector)
        data = []
        for pixel in _iterRGBAPixels(image):
            values = []
            for vector, bias in zip(vectors, biasVector):
                values.append(
                    _clampByte(
                        sum(component * coefficient for component, coefficient in zip(pixel, vector))
                        + float(bias) * 255
                    )
                )
            data.append(tuple(values))
        result = _newRGBAWithData(image.size, data)
        self._setPILImage(result)

    def colorPolynomial(
        self,
        redCoefficients=(0.0, 1.0, 0.0, 0.0),
        greenCoefficients=(0.0, 1.0, 0.0, 0.0),
        blueCoefficients=(0.0, 1.0, 0.0, 0.0),
        alphaCoefficients=(0.0, 1.0, 0.0, 0.0),
    ):
        coefficients = (
            redCoefficients,
            greenCoefficients,
            blueCoefficients,
            alphaCoefficients,
        )
        channels = []
        for channel, channelCoefficients in zip(self._pilImage().split(), coefficients):
            channels.append(channel.point(lambda value, coeffs=channelCoefficients: _polynomialByte(value, coeffs)))
        self._setPILImage(_mergeRGBA(*channels))

    def colorCrossPolynomial(
        self,
        redCoefficients=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        greenCoefficients=(0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        blueCoefficients=(0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ):
        image = self._pilImage()
        data = []
        for r, g, b, a in _iterRGBAPixels(image):
            values = []
            rn, gn, bn = r / 255, g / 255, b / 255
            terms = (rn, gn, bn, rn * rn, gn * gn, bn * bn, rn * gn, gn * bn, bn * rn, 1)
            for coefficients in (redCoefficients, greenCoefficients, blueCoefficients):
                values.append(_clampByte(sum(c * t for c, t in zip(coefficients, terms)) * 255))
            data.append((*values, a))
        self._setPILImage(_newRGBAWithData(image.size, data))

    def colorThreshold(self, threshold=0.5):
        image = self._pilImage()
        limit = _clampByte(float(threshold) * 255)
        gray = image.convert("L").point(lambda value: 255 if value >= limit else 0)
        self._setPILImage(_mergeRGBA(gray, gray, gray, image.getchannel("A")))

    def colorThresholdOtsu(self):
        image = self._pilImage()
        graySource = image.convert("L")
        threshold = _otsuThreshold(graySource.histogram())
        gray = graySource.point(lambda value: 255 if value >= threshold else 0)
        self._setPILImage(_mergeRGBA(gray, gray, gray, image.getchannel("A")))

    def colorAbsoluteDifference(self, image2):
        from PIL import ImageChops

        image = self._pilImage()
        other = _imageObjectToPIL(image2).resize(image.size)
        self._setPILImage(ImageChops.difference(image, other))

    def mix(self, backgroundImage, amount=1.0):
        background = _imageObjectToPIL(backgroundImage).resize(self.size())
        self._setPILImage(_blendRGBA(background, self._pilImage(), amount))

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

    def comicEffect(self):
        from PIL import ImageFilter

        image = self._pilImage()
        edges = image.filter(ImageFilter.FIND_EDGES).convert("L")
        posterized = image.convert("RGB").point(lambda value: _clampByte(round(value / 64) * 64)).convert("RGBA")
        posterized.putalpha(image.getchannel("A"))
        posterized = posterized.filter(ImageFilter.SMOOTH_MORE)
        edgeMask = edges.point(lambda value: 255 if value > 30 else 0)
        self._setPILImage(_blendRGBA(posterized, _mergeRGBA(edgeMask, edgeMask, edgeMask, image.getchannel("A")), 0.35))

    def XRay(self):
        self.colorInvert()
        self.photoEffectMono()

    def thermal(self):
        self.falseColor((0, 0, 0.3, 1), (1, 0.2, 0, 1))

    def dither(self, intensity=0.1):
        image = self._pilImage()
        dithered = image.convert("RGB").convert("P", dither=1).convert("RGBA")
        dithered.putalpha(image.getchannel("A"))
        self._setPILImage(_blendRGBA(image, dithered, intensity))

    def sampleNearest(self):
        from PIL import Image

        image = self._pilImage()
        self._setPILImage(image.resize(image.size, Image.Resampling.NEAREST))

    def morphologyMaximum(self, radius=0.0):
        from PIL import ImageFilter

        radius = max(1, int(round(float(radius))))
        self._filter(ImageFilter.MaxFilter(radius * 2 + 1))

    def morphologyMinimum(self, radius=0.0):
        from PIL import ImageFilter

        radius = max(1, int(round(float(radius))))
        self._filter(ImageFilter.MinFilter(radius * 2 + 1))

    def morphologyGradient(self, radius=5.0):
        from PIL import ImageChops
        from PIL import ImageFilter

        image = self._pilImage()
        radius = max(1, int(round(float(radius))))
        size = radius * 2 + 1
        maximum = image.filter(ImageFilter.MaxFilter(size))
        minimum = image.filter(ImageFilter.MinFilter(size))
        self._setPILImage(ImageChops.difference(maximum, minimum))

    def morphologyRectangleMaximum(self, width=5.0, height=5.0):
        from PIL import ImageFilter

        size = max(1, int(round(max(float(width), float(height)))))
        if size % 2 == 0:
            size += 1
        self._filter(ImageFilter.MaxFilter(size))

    def morphologyRectangleMinimum(self, width=5.0, height=5.0):
        from PIL import ImageFilter

        size = max(1, int(round(max(float(width), float(height)))))
        if size % 2 == 0:
            size += 1
        self._filter(ImageFilter.MinFilter(size))

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

    def additionCompositing(self, backgroundImage):
        from PIL import ImageChops

        self._composite(backgroundImage, ImageChops.add)

    def maximumCompositing(self, backgroundImage):
        from PIL import ImageChops

        self._composite(backgroundImage, ImageChops.lighter)

    def minimumCompositing(self, backgroundImage):
        from PIL import ImageChops

        self._composite(backgroundImage, ImageChops.darker)

    def multiplyCompositing(self, backgroundImage):
        self.multiplyBlendMode(backgroundImage)

    def multiplyBlendMode(self, backgroundImage):
        from PIL import ImageChops

        self._composite(backgroundImage, ImageChops.multiply)

    def screenBlendMode(self, backgroundImage):
        from PIL import ImageChops

        self._composite(backgroundImage, ImageChops.screen)

    def overlayBlendMode(self, backgroundImage):
        self._composite(backgroundImage, _overlayBlend)

    def hardLightBlendMode(self, backgroundImage):
        self._composite(backgroundImage, lambda source, background: _overlayBlend(background, source))

    def softLightBlendMode(self, backgroundImage):
        self._composite(backgroundImage, _softLightBlend)

    def darkenBlendMode(self, backgroundImage):
        from PIL import ImageChops

        self._composite(backgroundImage, ImageChops.darker)

    def lightenBlendMode(self, backgroundImage):
        from PIL import ImageChops

        self._composite(backgroundImage, ImageChops.lighter)

    def differenceBlendMode(self, backgroundImage):
        from PIL import ImageChops

        self._composite(backgroundImage, ImageChops.difference)

    def exclusionBlendMode(self, backgroundImage):
        self._composite(backgroundImage, _exclusionBlend)

    def colorBurnBlendMode(self, backgroundImage):
        self._composite(backgroundImage, _colorBurnBlend)

    def colorDodgeBlendMode(self, backgroundImage):
        self._composite(backgroundImage, _colorDodgeBlend)

    def divideBlendMode(self, backgroundImage):
        self._composite(backgroundImage, _divideBlend)

    def linearBurnBlendMode(self, backgroundImage):
        self._composite(
            backgroundImage,
            lambda source, background: _channelBlend(
                source,
                background,
                lambda s, b: _clampByte(s + b - 255),
            ),
        )

    def linearDodgeBlendMode(self, backgroundImage):
        self._composite(
            backgroundImage,
            lambda source, background: _channelBlend(
                source,
                background,
                lambda s, b: _clampByte(s + b),
            ),
        )

    def linearLightBlendMode(self, backgroundImage):
        self._composite(backgroundImage, _linearLightBlend)

    def pinLightBlendMode(self, backgroundImage):
        self._composite(backgroundImage, _pinLightBlend)

    def subtractBlendMode(self, backgroundImage):
        self._composite(
            backgroundImage,
            lambda source, background: _channelBlend(
                source,
                background,
                lambda s, b: _clampByte(b - s),
            ),
        )

    def vividLightBlendMode(self, backgroundImage):
        self._composite(backgroundImage, _vividLightBlend)

    def hueBlendMode(self, backgroundImage):
        self._composite(backgroundImage, lambda source, background: _hslBlend(source, background, "hue"))

    def saturationBlendMode(self, backgroundImage):
        self._composite(backgroundImage, lambda source, background: _hslBlend(source, background, "saturation"))

    def colorBlendMode(self, backgroundImage):
        self._composite(backgroundImage, lambda source, background: _hslBlend(source, background, "color"))

    def luminosityBlendMode(self, backgroundImage):
        self._composite(backgroundImage, lambda source, background: _hslBlend(source, background, "luminosity"))

    def sourceOverCompositing(self, backgroundImage):
        from PIL import Image

        source = self._pilImage()
        background = _imageObjectToPIL(backgroundImage).resize(source.size)
        self._setPILImage(Image.alpha_composite(background, source))

    def sourceInCompositing(self, backgroundImage):
        source = self._pilImage()
        background = _imageObjectToPIL(backgroundImage).resize(source.size)
        source.putalpha(background.getchannel("A"))
        self._setPILImage(source)

    def sourceOutCompositing(self, backgroundImage):
        from PIL import ImageChops

        source = self._pilImage()
        background = _imageObjectToPIL(backgroundImage).resize(source.size)
        source.putalpha(ImageChops.invert(background.getchannel("A")))
        self._setPILImage(source)

    def sourceAtopCompositing(self, backgroundImage):
        from PIL import Image

        source = self._pilImage()
        background = _imageObjectToPIL(backgroundImage).resize(source.size)
        source.putalpha(background.getchannel("A"))
        self._setPILImage(Image.alpha_composite(background, source))

    def blendWithAlphaMask(self, backgroundImage, maskImage):
        from PIL import Image

        source = self._pilImage()
        background = _imageObjectToPIL(backgroundImage).resize(source.size)
        mask = _imageObjectToPIL(maskImage).resize(source.size).getchannel("A")
        self._setPILImage(Image.composite(source, background, mask))

    def blendWithMask(self, backgroundImage, maskImage):
        from PIL import Image

        source = self._pilImage()
        background = _imageObjectToPIL(backgroundImage).resize(source.size)
        mask = _imageObjectToPIL(maskImage).resize(source.size).convert("L")
        self._setPILImage(Image.composite(source, background, mask))

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

    def _composite(self, backgroundImage, blendFunction):
        from PIL import Image

        source = self._pilImage()
        background = _imageObjectToPIL(backgroundImage).resize(source.size)
        blended = blendFunction(source.convert("RGBA"), background.convert("RGBA"))
        alpha = source.getchannel("A")
        self._setPILImage(Image.composite(blended, background, alpha))

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


def _normalizeSize(size):
    width, height = size
    return max(1, int(round(width))), max(1, int(round(height)))


def _mixColor(color0, color1, amount):
    amount = max(0, min(1, float(amount)))
    c0 = _colorToRGBABytes(color0)
    c1 = _colorToRGBABytes(color1)
    return tuple(_clampByte(a + (b - a) * amount) for a, b in zip(c0, c1))


def _linearGradientImage(size, point0, point1, color0, color1):
    from PIL import Image

    width, height = _normalizeSize(size)
    x0, y0 = point0
    x1, y1 = point1
    dx = x1 - x0
    dy = y1 - y0
    lengthSquared = dx * dx + dy * dy or 1
    image = Image.new("RGBA", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            amount = ((x - x0) * dx + (y - y0) * dy) / lengthSquared
            pixels[x, y] = _mixColor(color0, color1, amount)
    return image


def _radialGradientImage(size, center, radius0, radius1, color0, color1):
    from PIL import Image

    width, height = _normalizeSize(size)
    cx, cy = center
    radius0 = float(radius0)
    radius1 = float(radius1)
    radiusDelta = radius1 - radius0 or 1
    image = Image.new("RGBA", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            amount = (math.hypot(x - cx, y - cy) - radius0) / radiusDelta
            pixels[x, y] = _mixColor(color0, color1, amount)
    return image


def _gaussianGradientImage(size, center, color0, color1, radius):
    from PIL import Image

    width, height = _normalizeSize(size)
    cx, cy = center
    radius = max(1, float(radius))
    image = Image.new("RGBA", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            distance = math.hypot(x - cx, y - cy)
            amount = 1 - math.exp(-((distance ** 2) / (2 * radius * radius)))
            pixels[x, y] = _mixColor(color0, color1, amount)
    return image


def _lighterOrDarker(image1, image2, darker=False):
    from PIL import ImageChops

    if darker:
        return ImageChops.darker(image1, image2)
    return ImageChops.lighter(image1, image2)


def _screenBlend(image1, image2, amount):
    from PIL import ImageChops

    screened = ImageChops.screen(image1.convert("RGBA"), image2.convert("RGBA"))
    return _blendRGBA(image1, screened, amount)


def _newRGBAWithData(size, data):
    from PIL import Image

    image = Image.new("RGBA", size)
    image.putdata(data)
    return image


def _polynomialByte(value, coefficients):
    value = value / 255
    result = 0
    for power, coefficient in enumerate(coefficients):
        result += coefficient * (value ** power)
    return _clampByte(result * 255)


def _otsuThreshold(histogram):
    total = sum(histogram)
    sumTotal = sum(index * count for index, count in enumerate(histogram))
    sumBackground = 0
    weightBackground = 0
    bestThreshold = 0
    bestVariance = -1
    for threshold, count in enumerate(histogram):
        weightBackground += count
        if weightBackground == 0:
            continue
        weightForeground = total - weightBackground
        if weightForeground == 0:
            break
        sumBackground += threshold * count
        meanBackground = sumBackground / weightBackground
        meanForeground = (sumTotal - sumBackground) / weightForeground
        variance = weightBackground * weightForeground * ((meanBackground - meanForeground) ** 2)
        if variance > bestVariance:
            bestVariance = variance
            bestThreshold = threshold
    return bestThreshold


def _imageObjectToPIL(image):
    if isinstance(image, ImageObject):
        return image._pilImage()
    return ImageObject(image)._pilImage()


def _overlayBlend(source, background):
    return _channelBlend(source, background, _overlayChannel)


def _softLightBlend(source, background):
    return _channelBlend(source, background, _softLightChannel)


def _exclusionBlend(source, background):
    return _channelBlend(
        source,
        background,
        lambda s, b: _clampByte(s + b - (2 * s * b / 255)),
    )


def _colorBurnBlend(source, background):
    return _channelBlend(
        source,
        background,
        lambda s, b: 0 if s == 0 else _clampByte(255 - min(255, (255 - b) * 255 / s)),
    )


def _colorDodgeBlend(source, background):
    return _channelBlend(
        source,
        background,
        lambda s, b: 255 if s == 255 else _clampByte(min(255, b * 255 / (255 - s))),
    )


def _divideBlend(source, background):
    return _channelBlend(
        source,
        background,
        lambda s, b: 255 if s == 0 else _clampByte(min(255, b * 255 / s)),
    )


def _linearLightBlend(source, background):
    return _channelBlend(
        source,
        background,
        lambda s, b: _clampByte(b + 2 * s - 255),
    )


def _pinLightBlend(source, background):
    return _channelBlend(
        source,
        background,
        lambda s, b: min(b, 2 * s) if s < 128 else max(b, 2 * (s - 128)),
    )


def _vividLightBlend(source, background):
    return _channelBlend(
        source,
        background,
        lambda s, b: _colorBurnChannel(2 * s, b)
        if s < 128
        else _colorDodgeChannel(2 * (s - 128), b),
    )


def _colorBurnChannel(source, background):
    if source <= 0:
        return 0
    return _clampByte(255 - min(255, (255 - background) * 255 / source))


def _colorDodgeChannel(source, background):
    if source >= 255:
        return 255
    return _clampByte(min(255, background * 255 / (255 - source)))


def _channelBlend(source, background, blend):
    from PIL import Image

    source = source.convert("RGBA")
    background = background.convert("RGBA")
    data = []
    for sourcePixel, backgroundPixel in zip(_iterRGBAPixels(source), _iterRGBAPixels(background)):
        data.append(
            (
                blend(sourcePixel[0], backgroundPixel[0]),
                blend(sourcePixel[1], backgroundPixel[1]),
                blend(sourcePixel[2], backgroundPixel[2]),
                sourcePixel[3],
            )
        )
    result = Image.new("RGBA", source.size)
    result.putdata(data)
    return result


def _overlayChannel(source, background):
    if background < 128:
        return _clampByte(2 * source * background / 255)
    return _clampByte(255 - 2 * (255 - source) * (255 - background) / 255)


def _softLightChannel(source, background):
    source /= 255
    background /= 255
    if source < 0.5:
        value = background - (1 - 2 * source) * background * (1 - background)
    else:
        value = background + (2 * source - 1) * (_softLightD(background) - background)
    return _clampByte(value * 255)


def _softLightD(value):
    if value <= 0.25:
        return ((16 * value - 12) * value + 4) * value
    return math.sqrt(value)


def _hslBlend(source, background, mode):
    from PIL import Image
    import colorsys

    source = source.convert("RGBA")
    background = background.convert("RGBA")
    result = Image.new("RGBA", source.size)
    data = []
    for sourcePixel, backgroundPixel in zip(_iterRGBAPixels(source), _iterRGBAPixels(background)):
        sh, sl, ss = colorsys.rgb_to_hls(
            sourcePixel[0] / 255, sourcePixel[1] / 255, sourcePixel[2] / 255
        )
        bh, bl, bs = colorsys.rgb_to_hls(
            backgroundPixel[0] / 255,
            backgroundPixel[1] / 255,
            backgroundPixel[2] / 255,
        )
        if mode == "hue":
            h, l, s = sh, bl, bs
        elif mode == "saturation":
            h, l, s = bh, bl, ss
        elif mode == "color":
            h, l, s = sh, bl, ss
        else:
            h, l, s = bh, sl, bs
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        data.append((_clampByte(r * 255), _clampByte(g * 255), _clampByte(b * 255), sourcePixel[3]))
    result.putdata(data)
    return result


def _iterRGBAPixels(image):
    data = image.tobytes()
    for index in range(0, len(data), 4):
        yield data[index], data[index + 1], data[index + 2], data[index + 3]
