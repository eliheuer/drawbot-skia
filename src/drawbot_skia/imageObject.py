import os
import math
from io import BytesIO
import skia

from .errors import DrawbotError


class ImageObject:
    def __init__(self, path=None, _drawing=None):
        self._image = None
        self._path = None
        self._offset = (0, 0)
        self._focusState = None
        self._drawing = _drawing
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
        other._drawing = self._drawing
        return other

    def clearFilters(self):
        if self._path is not None:
            self.open(self._path)
        self._offset = (0, 0)
        return None

    def __enter__(self):
        self.lockFocus()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.unlockFocus()
        return False

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
        alpha = image.getchannel("A")
        adjusted = image.convert("RGB")
        adjusted = ImageEnhance.Color(adjusted).enhance(float(saturation))
        adjusted = ImageEnhance.Brightness(adjusted).enhance(1 + float(brightness))
        adjusted = ImageEnhance.Contrast(adjusted).enhance(float(contrast)).convert("RGBA")
        adjusted.putalpha(alpha)
        self._setPILImage(adjusted)

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
        sharpness = max(0, min(1, float(sharpness)))
        transition = (1 - sharpness) * 0.5
        for y in range(heightPx):
            for x in range(widthPx):
                xPhase = (x - centerX) / cell
                yPhase = (y - centerY) / cell
                index = (math.floor(xPhase) + math.floor(yPhase)) & 1
                color = c1 if index else c0
                if transition:
                    distance = min(xPhase % 1, 1 - (xPhase % 1), yPhase % 1, 1 - (yPhase % 1))
                    if distance < transition:
                        color = _mixRGBABytes(color, c0 if index else c1, 0.5 * (1 - distance / transition))
                pixels[x, y] = color
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
        sharpness = max(0, min(1, float(sharpness)))
        transition = (1 - sharpness) * 0.5
        for y in range(heightPx):
            for x in range(widthPx):
                phase = (x - centerX) / stripeWidth
                index = math.floor(phase) & 1
                color = c1 if index else c0
                if transition:
                    fraction = phase % 1
                    distance = min(fraction, 1 - fraction)
                    if distance < transition:
                        color = _mixRGBABytes(color, c0 if index else c1, 0.5 * (1 - distance / transition))
                pixels[x, y] = color
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

    def QRCodeGenerator(self, size, message, correctionLevel="M"):
        self._setPILImage(_qrCodeImage(size, message, correctionLevel))
        self._path = None
        self._offset = (0, 0)

    def aztecCodeGenerator(self, size, message, layers, compactStyle, correctionLevel=23.0):
        self._setPILImage(_aztecCodeImage(size, message, correctionLevel, layers, compactStyle))
        self._path = None
        self._offset = (0, 0)

    def PDF417BarcodeGenerator(
        self,
        size,
        message,
        minWidth,
        maxWidth,
        minHeight,
        maxHeight,
        dataColumns,
        rows,
        preferredAspectRatio,
        compactionMode,
        compactStyle,
        correctionLevel,
        alwaysSpecifyCompaction,
    ):
        self._setPILImage(
            _pdf417BarcodeImage(
                size,
                message,
                minWidth,
                maxWidth,
                minHeight,
                maxHeight,
                dataColumns,
                rows,
                preferredAspectRatio,
                compactionMode,
                compactStyle,
                correctionLevel,
                alwaysSpecifyCompaction,
            )
        )
        self._path = None
        self._offset = (0, 0)

    def code128BarcodeGenerator(self, size, message, quietSpace=10.0, barcodeHeight=32.0):
        self._setPILImage(_code128BarcodeImage(size, message, quietSpace, barcodeHeight))
        self._path = None
        self._offset = (0, 0)

    def lenticularHaloGenerator(
        self,
        size,
        center=(150.0, 150.0),
        color=(1.0, 0.9, 0.8, 1.0),
        haloRadius=70.0,
        haloWidth=87.0,
        haloOverlap=0.77,
        striationStrength=0.5,
        striationContrast=1.0,
        time=0.0,
    ):
        haloOverlap = max(0, float(haloOverlap))
        self._setPILImage(
            _radialLightImage(
                size,
                center,
                color,
                haloRadius,
                float(haloWidth) * (1 + haloOverlap),
                rays=True,
                rayRadius=max(1, float(haloRadius) / max(1, float(haloWidth)) * 4),
                rayStrength=striationStrength,
                rayContrast=striationContrast,
                rayTime=time,
            )
        )
        self._path = None
        self._offset = (0, 0)

    def starShineGenerator(
        self,
        size,
        center=(150.0, 150.0),
        color=(1.0, 0.8, 0.6, 1.0),
        radius=50.0,
        crossScale=15.0,
        crossAngle=0.6,
        crossOpacity=-2.0,
        crossWidth=2.5,
        epsilon=-2.0,
    ):
        self._setPILImage(_starImage(size, center, color, radius, crossScale, crossAngle, crossOpacity, crossWidth, epsilon))
        self._path = None
        self._offset = (0, 0)

    def sunbeamsGenerator(
        self,
        size,
        center=(150.0, 150.0),
        color=(1.0, 0.5, 0.0, 1.0),
        sunRadius=40.0,
        maxStriationRadius=2.58,
        striationStrength=0.5,
        striationContrast=1.375,
        time=0.0,
    ):
        self._setPILImage(
            _radialLightImage(
                size,
                center,
                color,
                sunRadius,
                max(size),
                rays=True,
                rayRadius=maxStriationRadius,
                rayStrength=striationStrength,
                rayContrast=striationContrast,
                rayTime=time,
            )
        )
        self._path = None
        self._offset = (0, 0)

    def meshGenerator(self, size, mesh, width=1.5, color=(1.0, 1.0, 1.0, 1.0)):
        self._setPILImage(_meshImage(size, mesh, width, color))
        self._path = None
        self._offset = (0, 0)

    def clamp(self, extent=(0.0, 0.0, 640.0, 80.0)):
        self.crop(extent)

    def affineClamp(self, transform=(0.4, 0.0, 0.0, 0.4, 0.0, 0.0)):
        self._affineTransform(transform)

    def affineTile(self, transform=(0.4, 0.0, 0.0, 0.4, 0.0, 0.0)):
        self._setPILImage(_affineTileImage(self._pilImage(), transform))

    def straightenFilter(self, angle=0.0):
        from PIL import Image

        self._setPILImage(
            self._pilImage().rotate(
                math.degrees(float(angle)),
                expand=True,
                resample=Image.Resampling.BICUBIC,
            )
        )

    def stretchCrop(self, size=(1280.0, 720.0), cropAmount=0.25, centerStretchAmount=0.25):
        self._setPILImage(_stretchCropImage(self._pilImage(), size, cropAmount, centerStretchAmount))
        self._offset = (0, 0)

    def perspectiveTransform(
        self,
        topLeft=(118.0, 484.0),
        topRight=(646.0, 507.0),
        bottomRight=(548.0, 140.0),
        bottomLeft=(155.0, 153.0),
    ):
        self._setPILImage(_quadTransformImage(self._pilImage(), topLeft, topRight, bottomRight, bottomLeft))

    def perspectiveTransformWithExtent(
        self,
        extent=(0.0, 0.0, 300.0, 300.0),
        topLeft=(118.0, 484.0),
        topRight=(646.0, 507.0),
        bottomRight=(548.0, 140.0),
        bottomLeft=(155.0, 153.0),
    ):
        self.perspectiveTransform(topLeft, topRight, bottomRight, bottomLeft)
        self.crop(extent)

    def perspectiveCorrection(
        self,
        topLeft=(118.0, 484.0),
        topRight=(646.0, 507.0),
        bottomRight=(548.0, 140.0),
        bottomLeft=(155.0, 153.0),
        crop=True,
    ):
        image = self._pilImage()
        if crop:
            self._setPILImage(_quadTransformImage(image, topLeft, topRight, bottomRight, bottomLeft))
            self._offset = (0, 0)
        else:
            corrected, offset = _quadTransformImage(
                image,
                topLeft,
                topRight,
                bottomRight,
                bottomLeft,
                resizeToSource=False,
            )
            self._setPILImage(corrected)
            offsetX, offsetY = self._offset
            self._offset = (offsetX + offset[0], offsetY + offset[1])

    def perspectiveTile(
        self,
        topLeft=(118.0, 484.0),
        topRight=(646.0, 507.0),
        bottomRight=(548.0, 140.0),
        bottomLeft=(155.0, 153.0),
    ):
        self.perspectiveTransform(topLeft, topRight, bottomRight, bottomLeft)
        self._setPILImage(_tileImage(self._pilImage(), rotations=2, reflect=True))

    def perspectiveRotate(self, focalLength=28.0, pitch=0.0, yaw=0.0, roll=0.0):
        self._setPILImage(_perspectiveRotateImage(self._pilImage(), focalLength, pitch, yaw, roll))

    def bumpDistortion(self, center=(150.0, 150.0), radius=300.0, scale=0.5):
        self._setPILImage(_radialDistortImage(self._pilImage(), center, radius, scale, "bump"))

    def bumpDistortionLinear(self, center=(150.0, 150.0), radius=300.0, angle=0.0, scale=0.5):
        self._setPILImage(_linearBumpImage(self._pilImage(), center, radius, angle, scale))

    def circleSplashDistortion(self, center=(150.0, 150.0), radius=150.0):
        self._setPILImage(_radialDistortImage(self._pilImage(), center, radius, 0.6, "splash"))

    def circularWrap(self, center=(150.0, 150.0), radius=150.0, angle=0.0):
        self._setPILImage(_twirlImage(self._pilImage(), center, radius, angle))

    def displacementDistortion(self, displacementImage, scale=50.0):
        self._setPILImage(_displacementImage(self._pilImage(), _imageObjectToPIL(displacementImage), scale))

    def glassDistortion(self, texture, center=(150.0, 150.0), scale=200.0):
        self._setPILImage(_glassDistortionImage(self._pilImage(), _imageObjectToPIL(texture), center, scale))

    def glassLozenge(self, point0=(150.0, 150.0), point1=(350.0, 150.0), radius=100.0, refraction=1.7):
        self._setPILImage(_lozengeDistortImage(self._pilImage(), point0, point1, radius, refraction))

    def holeDistortion(self, center=(150.0, 150.0), radius=150.0):
        self._setPILImage(_radialDistortImage(self._pilImage(), center, radius, -1, "pinch"))

    def pinchDistortion(self, center=(150.0, 150.0), radius=300.0, scale=0.5):
        self._setPILImage(_radialDistortImage(self._pilImage(), center, radius, scale, "pinch"))

    def torusLensDistortion(self, center=(150.0, 150.0), radius=160.0, width=80.0, refraction=1.7):
        self._setPILImage(_torusDistortImage(self._pilImage(), center, radius, width, refraction))

    def twirlDistortion(self, center=(150.0, 150.0), radius=300.0, angle=math.pi):
        self._setPILImage(_twirlImage(self._pilImage(), center, radius, angle))

    def vortexDistortion(self, center=(150.0, 150.0), radius=300.0, angle=56.548667764616276):
        self._setPILImage(_twirlImage(self._pilImage(), center, radius, angle))

    def keystoneCorrectionCombined(
        self,
        topLeft,
        topRight,
        bottomRight,
        bottomLeft,
        focalLength=28.0,
    ):
        self._setPILImage(
            _keystoneCombinedImage(
                self._pilImage(), focalLength, topLeft, topRight, bottomRight, bottomLeft
            )
        )

    def keystoneCorrectionHorizontal(
        self,
        topLeft,
        topRight,
        bottomRight,
        bottomLeft,
        focalLength=28.0,
    ):
        self._setPILImage(
            _keystoneCombinedImage(
                self._pilImage(), focalLength, topLeft, topRight, bottomRight, bottomLeft
            )
        )

    def keystoneCorrectionVertical(
        self,
        topLeft,
        topRight,
        bottomRight,
        bottomLeft,
        focalLength=28.0,
    ):
        self._setPILImage(
            _keystoneCombinedImage(
                self._pilImage(), focalLength, topLeft, topRight, bottomRight, bottomLeft
            )
        )

    def droste(
        self,
        insetPoint0=(200.0, 200.0),
        insetPoint1=(400.0, 400.0),
        strands=1.0,
        periodicity=1.0,
        rotation=0.0,
        zoom=1.0,
    ):
        self._setPILImage(_drosteImage(self._pilImage(), insetPoint0, insetPoint1, strands, periodicity, rotation, zoom))

    def lightTunnel(self, center=(150.0, 150.0), rotation=0.0, radius=100.0):
        self._setPILImage(_lightTunnelImage(self._pilImage(), center, rotation, radius))

    def ninePartStretched(self, breakpoint0=(50.0, 50.0), breakpoint1=(150.0, 150.0), growAmount=(100.0, 100.0)):
        self._setPILImage(_ninePartImage(self._pilImage(), breakpoint0, breakpoint1, growAmount, tiled=False))
        self._offset = (0, 0)

    def ninePartTiled(self, breakpoint0=(50.0, 50.0), breakpoint1=(150.0, 150.0), growAmount=(100.0, 100.0), flipYTiles=True):
        self._setPILImage(_ninePartImage(self._pilImage(), breakpoint0, breakpoint1, growAmount, tiled=True, flipYTiles=flipYTiles))
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
        alpha = image.getchannel("A")
        adjusted = ImageEnhance.Brightness(image.convert("RGB")).enhance(2 ** float(EV)).convert("RGBA")
        adjusted.putalpha(alpha)
        self._setPILImage(adjusted)

    def hueAdjust(self, angle=0.0):
        from PIL import Image

        image = self._pilImage()
        angle = float(angle) % math.tau
        if angle == 0:
            return
        a = image.getchannel("A")
        hueShift = int(round(angle / math.tau * 255))
        h, s, v = image.convert("HSV").split()
        h = h.point(lambda value: (value + hueShift) % 256)
        adjusted = Image.merge("HSV", (h, s, v)).convert("RGBA")
        adjusted.putalpha(a)
        self._setPILImage(adjusted)

    def vibrance(self, amount=0.0):
        self._setPILImage(_vibranceImage(self._pilImage(), amount))

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
        cr, cg, cb, _ca = _colorToRGBABytes(color)
        r, g, b, a = image.split()
        r = r.point(lambda value: _clampByte(value * cr / 255))
        g = g.point(lambda value: _clampByte(value * cg / 255))
        b = b.point(lambda value: _clampByte(value * cb / 255))
        self._setPILImage(_mergeRGBA(r, g, b, a))

    def colorMonochrome(self, color=(0.6, 0.45, 0.3, 1.0), intensity=1.0):
        from PIL import Image

        image = self._pilImage()
        gray = image.convert("L")
        cr, cg, cb, _ca = _colorToRGBABytes(color)
        tinted = Image.merge(
            "RGBA",
            (
                gray.point(lambda value: _clampByte(value * cr / 255)),
                gray.point(lambda value: _clampByte(value * cg / 255)),
                gray.point(lambda value: _clampByte(value * cb / 255)),
                image.getchannel("A"),
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

    def colorMap(self, gradientImage):
        gradient = _imageObjectToPIL(gradientImage).resize((256, 1))
        gradientPixels = list(_getImageData(gradient))
        image = self._pilImage()
        gray = image.convert("L")
        data = []
        for value, alpha in zip(_getImageData(gray), _getImageData(image.getchannel("A"))):
            r, g, b, _ = gradientPixels[value]
            data.append((r, g, b, alpha))
        self._setPILImage(_newRGBAWithData(image.size, data))

    def convertRGBtoLab(self, normalize=False):
        image = self._pilImage()
        data = []
        for r, g, b, a in _getImageData(image):
            data.append((*_labToBytes(*_rgbBytesToLab(r, g, b), normalize=normalize), a))
        self._setPILImage(_newRGBAWithData(image.size, data))

    def convertLabToRGB(self, normalize=False):
        image = self._pilImage()
        data = []
        for l, aa, bb, alpha in _getImageData(image):
            data.append((*_labBytesToRGB(l, aa, bb, normalize=normalize), alpha))
        self._setPILImage(_newRGBAWithData(image.size, data))

    def labDeltaE(self, image2):
        other = _imageObjectToPIL(image2).resize(self.size())
        data = []
        for color1, color2 in zip(_getImageData(self._pilImage()), _getImageData(other)):
            lab1 = _rgbBytesToLab(*color1[:3])
            lab2 = _rgbBytesToLab(*color2[:3])
            delta = math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))
            value = _clampByte(delta)
            data.append((value, value, value, color1[3]))
        self._setPILImage(_newRGBAWithData(self.size(), data))

    def KMeans(
        self,
        means,
        extent=(0.0, 0.0, 640.0, 80.0),
        count=8.0,
        passes=5.0,
        perceptual=False,
    ):
        from PIL import Image

        if (
            isinstance(means, (int, float))
            and extent == (0.0, 0.0, 640.0, 80.0)
            and count == 8.0
        ):
            count = means
            means = None
        image = _cropExtent(self._pilImage(), extent)
        colors = max(1, int(round(float(count))))
        centers = _kMeansSeedColors(means) if means is not None else []
        if len(centers) < colors:
            quantized = image.convert("RGB").quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
            palette = quantized.getpalette() or []
            colorCounts = quantized.getcolors(image.width * image.height) or []
            for _pixelCount, pixelIndex in sorted(colorCounts, key=lambda item: item[0], reverse=True):
                offset = pixelIndex * 3
                color = tuple(palette[offset:offset + 3])
                if len(color) == 3:
                    centers.append(tuple(float(value) for value in color))
        pixels = list(_getImageData(image))
        while len(centers) < colors:
            centers.append(tuple(float(value) for value in pixels[len(centers) % len(pixels)][:3]) if pixels else (0.0, 0.0, 0.0))
        centers = centers[:colors]
        iterations = max(0, int(round(float(passes))))
        assignments = [0] * len(pixels)
        if pixels:
            pixelLabs = [_rgbBytesToLab(*pixel[:3]) for pixel in pixels] if perceptual else None

            def assignPixels():
                centerLabs = [_rgbBytesToLab(*(_clampByte(c) for c in center)) for center in centers] if perceptual else None
                groups = [[] for _ in centers]
                for index, pixel in enumerate(pixels):
                    if perceptual:
                        pixelLab = pixelLabs[index]
                        distances = [
                            sum((a - b) ** 2 for a, b in zip(pixelLab, centerLab))
                            for centerLab in centerLabs
                        ]
                    else:
                        distances = [
                            sum((pixel[channel] - center[channel]) ** 2 for channel in range(3))
                            for center in centers
                        ]
                    cluster = min(range(len(centers)), key=distances.__getitem__)
                    assignments[index] = cluster
                    groups[cluster].append(pixel)
                return groups

            for _ in range(iterations):
                groups = assignPixels()
                for index, group in enumerate(groups):
                    if group:
                        centers[index] = tuple(sum(pixel[channel] for pixel in group) / len(group) for channel in range(3))
            assignPixels()
        else:
            assignments = []
        total = image.width * image.height or 1
        clusterCounts = [assignments.count(index) for index in range(colors)]
        data = [
            (
                *(_clampByte(value) for value in center),
                _clampByte(clusterCounts[index] / total * 255),
            )
            for index, center in sorted(enumerate(centers), key=lambda item: clusterCounts[item[0]], reverse=True)
        ]
        self._setPILImage(_newRGBAWithData((colors, 1), data))
        self._offset = (0, 0)

    def paletteCentroid(self, paletteImage, perceptual=False):
        palette = _paletteColors(_imageObjectToPIL(paletteImage))
        self._setPILImage(_paletteCentroidImage(self._pilImage(), palette, perceptual))
        self._offset = (0, 0)

    def palettize(self, paletteImage, perceptual=False):
        image = self._pilImage()
        palette = _paletteColors(_imageObjectToPIL(paletteImage))
        self._setPILImage(_palettizedImage(image, palette, perceptual))

    def spotColor(
        self,
        centerColor1=(0.0784, 0.0627, 0.0706, 1.0),
        replacementColor1=(0.4392, 0.1922, 0.1961, 1.0),
        closeness1=0.22,
        contrast1=0.98,
        centerColor2=(0.5255, 0.3059, 0.3451, 1.0),
        replacementColor2=(0.9137, 0.5608, 0.5059, 1.0),
        closeness2=0.15,
        contrast2=0.98,
        centerColor3=(0.9216, 0.4549, 0.3333, 1.0),
        replacementColor3=(0.9098, 0.7529, 0.6078, 1.0),
        closeness3=0.5,
        contrast3=0.99,
    ):
        replacements = [
            (_colorToRGBABytes(centerColor1), _colorToRGBABytes(replacementColor1), float(closeness1), float(contrast1)),
            (_colorToRGBABytes(centerColor2), _colorToRGBABytes(replacementColor2), float(closeness2), float(contrast2)),
            (_colorToRGBABytes(centerColor3), _colorToRGBABytes(replacementColor3), float(closeness3), float(contrast3)),
        ]
        data = []
        for pixel in _getImageData(self._pilImage()):
            replacement = pixel
            for center, color, closeness, contrast in replacements:
                amount = _spotColorAmount(pixel[:3], center[:3], closeness, contrast)
                if amount:
                    replacement = (
                        _clampByte(pixel[0] + (color[0] - pixel[0]) * amount),
                        _clampByte(pixel[1] + (color[1] - pixel[1]) * amount),
                        _clampByte(pixel[2] + (color[2] - pixel[2]) * amount),
                        pixel[3],
                    )
                    break
            data.append(replacement)
        self._setPILImage(_newRGBAWithData(self.size(), data))

    def areaAverage(self, extent=(0.0, 0.0, 640.0, 80.0)):
        cropped = _cropExtent(self._pilImage(), extent)
        self._setPILImage(_solidFromColor(cropped.resize((1, 1)).getpixel((0, 0))))
        self._offset = (0, 0)

    def areaMaximum(self, extent=(0.0, 0.0, 640.0, 80.0)):
        cropped = _cropExtent(self._pilImage(), extent)
        channels = cropped.split()
        self._setPILImage(_solidFromColor(tuple(channel.getextrema()[1] for channel in channels)))
        self._offset = (0, 0)

    def areaMinimum(self, extent=(0.0, 0.0, 640.0, 80.0)):
        cropped = _cropExtent(self._pilImage(), extent)
        channels = cropped.split()
        self._setPILImage(_solidFromColor(tuple(channel.getextrema()[0] for channel in channels)))
        self._offset = (0, 0)

    def areaMaximumAlpha(self, extent=(0.0, 0.0, 640.0, 80.0)):
        cropped = _cropExtent(self._pilImage(), extent)
        alpha = cropped.getchannel("A").getextrema()[1]
        self._setPILImage(_solidFromColor((alpha, alpha, alpha, 255)))
        self._offset = (0, 0)

    def areaMinimumAlpha(self, extent=(0.0, 0.0, 640.0, 80.0)):
        cropped = _cropExtent(self._pilImage(), extent)
        alpha = cropped.getchannel("A").getextrema()[0]
        self._setPILImage(_solidFromColor((alpha, alpha, alpha, 255)))
        self._offset = (0, 0)

    def areaMinMax(self, extent=(0.0, 0.0, 640.0, 80.0)):
        cropped = _cropExtent(self._pilImage(), extent)
        extrema = cropped.convert("L").getextrema()
        self._setPILImage(_solidFromColor((extrema[0], extrema[1], 0, 255), size=(2, 1)))
        self._offset = (0, 0)

    def areaMinMaxRed(self, extent=(0.0, 0.0, 640.0, 80.0)):
        cropped = _cropExtent(self._pilImage(), extent)
        extrema = cropped.getchannel("R").getextrema()
        self._setPILImage(_solidFromColor((extrema[0], extrema[1], 0, 255), size=(2, 1)))
        self._offset = (0, 0)

    def rowAverage(self, extent=(0.0, 0.0, 640.0, 80.0)):
        cropped = _cropExtent(self._pilImage(), extent)
        self._setPILImage(cropped.resize((1, cropped.height)))
        self._offset = (0, 0)

    def columnAverage(self, extent=(0.0, 0.0, 640.0, 80.0)):
        cropped = _cropExtent(self._pilImage(), extent)
        self._setPILImage(cropped.resize((cropped.width, 1)))
        self._offset = (0, 0)

    def areaHistogram(self, extent=(0.0, 0.0, 640.0, 80.0), scale=1.0, count=64.0):
        from PIL import Image

        cropped = _cropExtent(self._pilImage(), extent).convert("L")
        bins = max(1, int(round(float(count))))
        histogram = cropped.histogram()
        grouped = []
        step = 256 / bins
        for index in range(bins):
            start = int(round(index * step))
            end = int(round((index + 1) * step))
            grouped.append(sum(histogram[start:end]))
        maximum = max(grouped) or 1
        data = [_clampByte(value / maximum * 255 * float(scale)) for value in grouped]
        image = Image.new("RGBA", (bins, 1))
        image.putdata([(value, value, value, 255) for value in data])
        self._setPILImage(image)
        self._offset = (0, 0)

    def areaLogarithmicHistogram(
        self,
        extent=(0.0, 0.0, 640.0, 80.0),
        scale=1.0,
        count=64.0,
        minimumStop=-10.0,
        maximumStop=4.0,
    ):
        from PIL import Image

        cropped = _cropExtent(self._pilImage(), extent).convert("L")
        bins = max(1, int(round(float(count))))
        histogram = cropped.histogram()
        grouped = []
        step = 256 / bins
        for index in range(bins):
            start = int(round(index * step))
            end = int(round((index + 1) * step))
            grouped.append(sum(histogram[start:end]))
        total = max(1, sum(grouped))
        minimumStop = float(minimumStop)
        maximumStop = float(maximumStop)
        stopRange = maximumStop - minimumStop or 1
        data = []
        for value in grouped:
            normalized = max(value / total, 1e-12)
            logarithmic = (math.log10(normalized) - minimumStop) / stopRange
            data.append(_clampByte(logarithmic * 255 * float(scale)))
        image = Image.new("RGBA", (bins, 1))
        image.putdata([(value, value, value, 255) for value in data])
        self._setPILImage(image)
        self._offset = (0, 0)

    def histogramDisplayFilter(self, height=100.0, highLimit=1.0, lowLimit=0.0):
        from PIL import Image
        from PIL import ImageDraw

        histogram = self._pilImage().convert("L").histogram()
        width = 256
        height = max(1, int(round(float(height))))
        highLimit = max(float(highLimit), 0.0001)
        lowLimit = float(lowLimit)
        maximum = max(histogram) or 1
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for x, value in enumerate(histogram):
            normalized = (value / maximum - lowLimit) / (highLimit - lowLimit or 1)
            barHeight = max(0, min(height, int(round(normalized * height))))
            draw.line((x, height, x, height - barHeight), fill=(255, 255, 255, 255))
        self._setPILImage(image)
        self._offset = (0, 0)

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

        image = self._pilImage()
        percent = max(0, int(float(intensity) * 250))
        if not percent:
            return
        sharpened = image.convert("RGB").filter(
            ImageFilter.UnsharpMask(radius=max(0, float(radius)), percent=percent)
        ).convert("RGBA")
        sharpened.putalpha(image.getchannel("A"))
        self._setPILImage(sharpened)

    def noiseReduction(self, noiseLevel=0.02, sharpness=0.4):
        from PIL import ImageFilter

        image = self._pilImage()
        alpha = image.getchannel("A")
        adjusted = image.convert("RGB")
        radius = max(0, int(round(float(noiseLevel) * 50)))
        if radius:
            adjusted = adjusted.filter(ImageFilter.MedianFilter(size=radius * 2 + 1))
        sharpness = max(0, float(sharpness))
        if sharpness:
            adjusted = adjusted.filter(ImageFilter.UnsharpMask(percent=int(sharpness * 250)))
        adjusted = adjusted.convert("RGBA")
        adjusted.putalpha(alpha)
        self._setPILImage(adjusted)

    def edges(self, intensity=1.0):
        from PIL import ImageFilter

        image = self._pilImage()
        edge = image.filter(ImageFilter.FIND_EDGES).convert("RGBA")
        edge.putalpha(image.getchannel("A"))
        self._setPILImage(_blendRGBA(image, edge, intensity))

    def cannyEdgeDetector(
        self,
        gaussianSigma=1.6,
        perceptual=False,
        thresholdHigh=0.05,
        thresholdLow=0.02,
        hysteresisPasses=1.0,
    ):
        image = self._pilImage()
        edge = _cannyEdgeImage(
            image,
            gaussianSigma,
            perceptual,
            thresholdHigh,
            thresholdLow,
            hysteresisPasses,
        )
        self._setPILImage(_mergeRGBA(edge, edge, edge, image.getchannel("A")))

    def sobelGradients(self):
        from PIL import ImageFilter

        image = self._pilImage()
        edge = image.convert("L").filter(ImageFilter.FIND_EDGES)
        self._setPILImage(_mergeRGBA(edge, edge, edge, image.getchannel("A")))

    def edgeWork(self, radius=3.0):
        from PIL import ImageFilter

        image = self._pilImage()
        edges = image.convert("L").filter(ImageFilter.FIND_EDGES)
        filterRadius = max(0, int(round(float(radius))))
        if filterRadius:
            edges = edges.filter(ImageFilter.MaxFilter(filterRadius * 2 + 1))
        self._setPILImage(_mergeRGBA(edges, edges, edges, image.getchannel("A")))

    def comicEffect(self):
        self._setPILImage(_comicEffectImage(self._pilImage()))

    def XRay(self):
        self._setPILImage(_xrayImage(self._pilImage()))

    def thermal(self):
        self._setPILImage(_thermalImage(self._pilImage()))

    def dither(self, intensity=0.1):
        self._setPILImage(_ditherImage(self._pilImage(), intensity))

    def sampleNearest(self):
        from PIL import Image

        image = self._pilImage()
        self._setPILImage(image.resize(image.size, Image.Resampling.NEAREST))

    def SRGBToneCurveToLinear(self):
        image = self._pilImage()
        a = image.getchannel("A")
        converted = image.convert("RGB").point(_srgbToLinearByte).convert("RGBA")
        converted.putalpha(a)
        self._setPILImage(converted)

    def linearToSRGBToneCurve(self):
        image = self._pilImage()
        a = image.getchannel("A")
        converted = image.convert("RGB").point(_linearToSRGBByte).convert("RGBA")
        converted.putalpha(a)
        self._setPILImage(converted)

    def bokehBlur(self, radius=20.0, ringAmount=0.0, ringSize=0.1, softness=1.0):
        self._setPILImage(_bokehBlurImage(self._pilImage(), radius, ringAmount, ringSize, softness))

    def discBlur(self, radius=8.0):
        self._setPILImage(_discBlurImage(self._pilImage(), radius))

    def depthOfField(
        self,
        point0=(0.0, 300.0),
        point1=(300.0, 300.0),
        saturation=1.5,
        unsharpMaskRadius=2.5,
        unsharpMaskIntensity=0.5,
        radius=6.0,
    ):
        self._setPILImage(
            _depthOfFieldImage(
                self._pilImage(),
                point0,
                point1,
                saturation,
                unsharpMaskRadius,
                unsharpMaskIntensity,
                radius,
            )
        )

    def documentEnhancer(self, amount=1.0):
        from PIL import ImageEnhance
        from PIL import ImageFilter

        amount = max(0, float(amount))
        image = self._pilImage()
        alpha = image.getchannel("A")
        enhanced = ImageEnhance.Contrast(image.convert("RGB")).enhance(1 + amount * 0.25)
        enhanced = ImageEnhance.Sharpness(enhanced).enhance(1 + amount)
        enhanced = enhanced.filter(ImageFilter.SMOOTH_MORE).convert("RGBA")
        enhanced.putalpha(alpha)
        self._setPILImage(_blendRGBA(image, enhanced, min(1, amount)))

    def depthToDisparity(self):
        self._setPILImage(_reciprocalLuminanceImage(self._pilImage()))

    def disparityToDepth(self):
        self._setPILImage(_reciprocalLuminanceImage(self._pilImage()))

    def gaborGradients(self):
        self._setPILImage(_gaborGradientsImage(self._pilImage()))

    def guidedFilter(self, guideImage, radius=1.0, epsilon=0.0001):
        guide = _imageObjectToPIL(guideImage)
        self._setPILImage(_guidedFilterImage(self._pilImage(), guide, radius, epsilon))

    def personSegmentation(self, qualityLevel=0.0):
        from PIL import ImageFilter
        from PIL import ImageOps

        image = self._pilImage()
        qualityLevel = max(0, min(1, float(qualityLevel)))
        luminance = image.convert("L")
        mask = ImageOps.autocontrast(luminance)
        threshold = 32 + (1 - qualityLevel) * 64
        mask = mask.point(lambda value: 255 if value > threshold else 0)
        blurRadius = (1 - qualityLevel) * 2
        if blurRadius:
            mask = mask.filter(ImageFilter.GaussianBlur(blurRadius))
        self._setPILImage(_mergeRGBA(mask, mask, mask, image.getchannel("A")))

    def saliencyMapFilter(self):
        from PIL import ImageChops
        from PIL import ImageFilter
        from PIL import ImageOps

        image = self._pilImage()
        luminance = image.convert("L")
        localAverage = luminance.filter(ImageFilter.GaussianBlur(max(1, min(image.size) / 6)))
        saliency = ImageChops.difference(luminance, localAverage)
        saliency = ImageOps.autocontrast(saliency)
        self._setPILImage(_mergeRGBA(saliency, saliency, saliency, image.getchannel("A")))

    def shadedMaterial(self, shadingImage, scale=10.0):
        self._setPILImage(_shadedMaterialImage(self._pilImage(), _imageObjectToPIL(shadingImage), scale))

    def spotLight(
        self,
        lightPosition=(400.0, 600.0, 150.0),
        lightPointsAt=(200.0, 200.0, 0.0),
        brightness=3.0,
        concentration=0.1,
        color=(1.0, 1.0, 1.0, 1.0),
    ):
        self._setPILImage(_spotLightImage(self._pilImage(), lightPosition, lightPointsAt, brightness, concentration, color))

    def highlightShadowAdjust(self, radius=0.0, shadowAmount=0.0, highlightAmount=1.0):
        from PIL import ImageFilter

        image = self._pilImage()
        luminance = image.convert("L")
        radius = max(0, float(radius))
        if radius:
            luminance = luminance.filter(ImageFilter.GaussianBlur(radius))
        luminancePixels = luminance.load()
        sourcePixels = image.load()
        shadowAmount = float(shadowAmount)
        highlightAmount = float(highlightAmount)
        result = image.copy()
        resultPixels = result.load()
        for y in range(image.height):
            for x in range(image.width):
                lightness = luminancePixels[x, y] / 255
                shadowLift = (1 - lightness) * shadowAmount * 80
                highlightScale = 1 + (highlightAmount - 1) * lightness
                red, green, blue, alpha = sourcePixels[x, y]
                resultPixels[x, y] = (
                    _clampByte(red * highlightScale + shadowLift),
                    _clampByte(green * highlightScale + shadowLift),
                    _clampByte(blue * highlightScale + shadowLift),
                    alpha,
                )
        self._setPILImage(result)

    def heightFieldFromMask(self, radius=10.0):
        from PIL import ImageFilter

        image = self._pilImage()
        luminance = image.convert("L")
        alpha = image.getchannel("A")
        data = [
            _clampByte(value * mask / 255)
            for value, mask in zip(_getImageData(luminance), _getImageData(alpha))
        ]
        height = _newLWithData(image.size, data).filter(ImageFilter.GaussianBlur(float(radius)))
        self._setPILImage(_mergeRGBA(height, height, height, image.getchannel("A")))

    def lineOverlay(
        self,
        NRNoiseLevel=0.07,
        NRSharpness=0.71,
        edgeIntensity=1.0,
        threshold=0.1,
        contrast=50.0,
    ):
        from PIL import ImageEnhance
        from PIL import ImageFilter

        image = self._pilImage()
        source = image.convert("RGB")
        noiseRadius = max(0, int(round(float(NRNoiseLevel) * 20)))
        if noiseRadius:
            source = source.filter(ImageFilter.MedianFilter(noiseRadius * 2 + 1))
        sharpness = max(0, float(NRSharpness))
        if sharpness:
            source = source.filter(ImageFilter.UnsharpMask(percent=int(sharpness * 250)))
        edges = source.filter(ImageFilter.FIND_EDGES).convert("L")
        contrast = max(0, float(contrast))
        if contrast:
            edges = ImageEnhance.Contrast(edges).enhance(1 + contrast / 50)
        limit = _clampByte(float(threshold) * 255)
        edges = edges.point(lambda value: 255 if value > limit else 0)
        overlay = _mergeRGBA(edges, edges, edges, image.getchannel("A"))
        self._setPILImage(_blendRGBA(image, overlay, edgeIntensity))

    def dotScreen(self, center=(150.0, 150.0), angle=0.0, width=6.0, sharpness=0.7):
        self._setPILImage(_screenImage(self._pilImage(), center, angle, width, sharpness, "dot"))

    def lineScreen(self, center=(150.0, 150.0), angle=0.0, width=6.0, sharpness=0.7):
        self._setPILImage(_screenImage(self._pilImage(), center, angle, width, sharpness, "line"))

    def circularScreen(self, center=(150.0, 150.0), width=6.0, sharpness=0.7):
        self._setPILImage(_screenImage(self._pilImage(), center, 0, width, sharpness, "circular"))

    def hatchedScreen(self, center=(150.0, 150.0), angle=0.0, width=6.0, sharpness=0.7):
        image = _screenImage(self._pilImage(), center, angle, width, sharpness, "line")
        cross = _screenImage(self._pilImage(), center, angle + math.pi / 2, width, sharpness, "line")
        self._setPILImage(_blendRGBA(image, cross, 0.5))

    def CMYKHalftone(
        self,
        center=(150.0, 150.0),
        width=6.0,
        angle=0.0,
        sharpness=0.7,
        GCR=1.0,
        UCR=0.5,
    ):
        self._setPILImage(_cmykHalftoneImage(self._pilImage(), center, angle, width, sharpness, GCR, UCR))

    def kaleidoscope(self, count=6.0, center=(150.0, 150.0), angle=0.0):
        self._setPILImage(
            _tileImage(
                self._pilImage(),
                rotations=max(1, int(round(float(count)))),
                reflect=True,
                angle=angle,
                center=center,
            )
        )

    def triangleKaleidoscope(self, point=(150.0, 150.0), size=700.0, rotation=5.924285296593801, decay=0.85):
        self._setPILImage(_triangleKaleidoscopeImage(self._pilImage(), point, size, rotation, decay))

    def fourfoldReflectedTile(self, center=(150.0, 150.0), angle=0.0, width=100.0, acuteAngle=math.pi / 2):
        image = _fourfoldTileSource(self._pilImage(), center, width, angle, acuteAngle)
        self._setPILImage(_tileImage(image, rotations=4, reflect=True, angle=angle, center=center))

    def fourfoldRotatedTile(self, center=(150.0, 150.0), angle=0.0, width=100.0):
        image = _offsetTileImage(self._pilImage(), width, angle)
        self._setPILImage(_tileImage(image, rotations=4, reflect=False, angle=angle, center=center))

    def fourfoldTranslatedTile(self, center=(150.0, 150.0), angle=0.0, width=100.0, acuteAngle=math.pi / 2):
        self._setPILImage(_fourfoldTileSource(self._pilImage(), center, width, angle, acuteAngle))

    def glideReflectedTile(self, center=(150.0, 150.0), angle=0.0, width=100.0):
        tiled = _offsetTileImage(self._pilImage(), width, angle)
        self._setPILImage(_blendRGBA(tiled, _tileImage(tiled, rotations=2, reflect=True, center=center), 0.5))

    def eightfoldReflectedTile(self, center=(150.0, 150.0), angle=0.0, width=100.0):
        image = _offsetTileImage(self._pilImage(), width, angle)
        self._setPILImage(_tileImage(image, rotations=8, reflect=True, angle=angle, center=center))

    def sixfoldReflectedTile(self, center=(150.0, 150.0), angle=0.0, width=100.0):
        image = _offsetTileImage(self._pilImage(), width, angle)
        self._setPILImage(_tileImage(image, rotations=6, reflect=True, angle=angle, center=center))

    def sixfoldRotatedTile(self, center=(150.0, 150.0), angle=0.0, width=100.0):
        image = _offsetTileImage(self._pilImage(), width, angle)
        self._setPILImage(_tileImage(image, rotations=6, reflect=False, angle=angle, center=center))

    def twelvefoldReflectedTile(self, center=(150.0, 150.0), angle=0.0, width=100.0):
        image = _offsetTileImage(self._pilImage(), width, angle)
        self._setPILImage(_tileImage(image, rotations=12, reflect=True, angle=angle, center=center))

    def triangleTile(self, center=(150.0, 150.0), angle=0.0, width=100.0):
        image = _offsetTileImage(self._pilImage(), width, angle)
        self._setPILImage(_tileImage(image, rotations=3, reflect=False, angle=angle, center=center))

    def parallelogramTile(self, center=(150.0, 150.0), angle=0.0, acuteAngle=math.pi / 2, width=100.0):
        image = _skewTileImage(self._pilImage(), angle, acuteAngle, width)
        self._setPILImage(_tileImage(image, rotations=2, reflect=True, center=center))

    def opTile(self, center=(150.0, 150.0), scale=2.8, angle=0.0, width=65.0):
        image = _offsetTileImage(self._pilImage(), width, angle)
        self._setPILImage(
            _tileImage(
                image,
                rotations=max(1, int(round(float(scale)))),
                reflect=True,
                angle=angle,
                center=center,
            )
        )

    def crystallize(self, radius=20.0, center=(150.0, 150.0)):
        self.pixellate(center=center, scale=radius)

    def hexagonalPixellate(self, center=(150.0, 150.0), scale=8.0):
        self.pixellate(center=center, scale=scale)

    def pointillize(self, radius=20.0, center=(150.0, 150.0)):
        from PIL import Image
        from PIL import ImageDraw
        from PIL import ImageStat

        image = self._pilImage()
        radius = max(1, int(round(float(radius))))
        result = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(result)
        centerX, centerY = (float(value) for value in center)
        minBlockX = math.floor((0 - centerX) / radius)
        maxBlockX = math.floor((image.width - 1 - centerX) / radius)
        minBlockY = math.floor((0 - centerY) / radius)
        maxBlockY = math.floor((image.height - 1 - centerY) / radius)
        for blockY in range(minBlockY, maxBlockY + 1):
            for blockX in range(minBlockX, maxBlockX + 1):
                left = max(0, int(math.floor(centerX + blockX * radius)))
                top = max(0, int(math.floor(centerY + blockY * radius)))
                right = min(image.width, int(math.floor(centerX + (blockX + 1) * radius)))
                bottom = min(image.height, int(math.floor(centerY + (blockY + 1) * radius)))
                if right <= left:
                    right = min(image.width, left + 1)
                if bottom <= top:
                    bottom = min(image.height, top + 1)
                color = tuple(_clampByte(value) for value in ImageStat.Stat(image.crop((left, top, right, bottom))).mean)
                cx = centerX + blockX * radius + radius / 2
                cy = centerY + blockY * radius + radius / 2
                draw.ellipse((cx - radius / 2, cy - radius / 2, cx + radius / 2, cy + radius / 2), fill=color)
        self._setPILImage(result)

    def morphologyMaximum(self, radius=0.0):
        from PIL import ImageFilter

        radius = max(0, int(round(float(radius))))
        if not radius:
            return
        self._filter(ImageFilter.MaxFilter(radius * 2 + 1))

    def morphologyMinimum(self, radius=0.0):
        from PIL import ImageFilter

        radius = max(0, int(round(float(radius))))
        if not radius:
            return
        self._filter(ImageFilter.MinFilter(radius * 2 + 1))

    def morphologyGradient(self, radius=5.0):
        from PIL import ImageChops
        from PIL import ImageFilter

        image = self._pilImage()
        radius = max(0, int(round(float(radius))))
        size = radius * 2 + 1
        maximum = image.filter(ImageFilter.MaxFilter(size))
        minimum = image.filter(ImageFilter.MinFilter(size))
        self._setPILImage(ImageChops.difference(maximum, minimum))

    def morphologyRectangleMaximum(self, width=5.0, height=5.0):
        self._setPILImage(_morphologyRectangleImage(self._pilImage(), width, height, darker=False))

    def morphologyRectangleMinimum(self, width=5.0, height=5.0):
        self._setPILImage(_morphologyRectangleImage(self._pilImage(), width, height, darker=True))

    def pixellate(self, center=(150.0, 150.0), scale=8.0):
        self._setPILImage(_pixellateImage(self._pilImage(), center, scale))

    def motionBlur(self, radius=20.0, angle=0.0):
        self._setPILImage(_motionBlurImage(self._pilImage(), radius, angle))

    def zoomBlur(self, center=(150.0, 150.0), amount=20.0):
        from PIL import Image

        image = self._pilImage()
        cx, cy = center
        amount = max(0, int(round(float(amount))))
        if not amount:
            return
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
            left = int(round(cx * scale - cx))
            top = int(round(cy * scale - cy))
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
        result = Image.composite(dark, image, mask)
        result.putalpha(image.getchannel("A"))
        self._setPILImage(result)

    def bloom(self, radius=10.0, intensity=0.5):
        from PIL import ImageFilter

        image = self._pilImage()
        blurred = image.filter(ImageFilter.GaussianBlur(float(radius)))
        result = _screenBlend(image, blurred, intensity)
        result.putalpha(image.getchannel("A"))
        self._setPILImage(result)

    def gloom(self, radius=10.0, intensity=0.5):
        from PIL import ImageFilter

        image = self._pilImage()
        blurred = image.filter(ImageFilter.GaussianBlur(float(radius)))
        result = _blendRGBA(image, blurred, intensity)
        result.putalpha(image.getchannel("A"))
        self._setPILImage(result)

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

    def dissolveTransition(self, targetImage, time=0.0):
        target = _imageObjectToPIL(targetImage).resize(self.size())
        self._setPILImage(_blendRGBA(self._pilImage(), target, time))

    def swipeTransition(
        self,
        targetImage,
        extent=(0.0, 0.0, 300.0, 300.0),
        color=(1.0, 1.0, 1.0, 1.0),
        time=0.0,
        angle=0.0,
        width=300.0,
        opacity=0.0,
    ):
        if float(time) <= 0:
            return
        if float(time) >= 1:
            self._setPILImage(_imageObjectToPIL(targetImage).resize(self.size()))
            return
        target = _imageObjectToPIL(targetImage).resize(self.size())
        mask = _linearTransitionMask(self.size(), time, angle, width, extent)
        result = _blendWithMask(self._pilImage(), target, mask)
        if opacity:
            band = _linearTransitionBandMask(self.size(), time, angle, width, extent)
            colorImage = _solidFromColor(_colorToRGBABytes(color), self.size())
            result = _blendWithMask(result, colorImage, band.point(lambda value: _clampByte(value * float(opacity))))
        self._setPILImage(result)

    def barsSwipeTransition(
        self,
        targetImage,
        angle=math.pi,
        width=30.0,
        barOffset=10.0,
        time=0.0,
    ):
        if float(time) <= 0:
            return
        if float(time) >= 1:
            self._setPILImage(_imageObjectToPIL(targetImage).resize(self.size()))
            return
        target = _imageObjectToPIL(targetImage).resize(self.size())
        mask = _barsTransitionMask(self.size(), time, angle, width, barOffset)
        self._setPILImage(_blendWithMask(self._pilImage(), target, mask))

    def copyMachineTransition(
        self,
        targetImage,
        extent=(0.0, 0.0, 300.0, 300.0),
        color=(0.6, 1.0, 0.8, 1.0),
        time=0.0,
        angle=0.0,
        width=200.0,
        opacity=1.3,
    ):
        self.swipeTransition(targetImage, extent=extent, color=color, time=time, angle=angle, width=width, opacity=opacity)

    def flashTransition(
        self,
        targetImage,
        center=(150.0, 150.0),
        extent=(0.0, 0.0, 300.0, 300.0),
        color=(1.0, 0.8, 0.6, 1.0),
        time=0.0,
        maxStriationRadius=2.58,
        striationStrength=0.5,
        striationContrast=1.375,
        fadeThreshold=0.85,
    ):
        size = self.size()
        time = max(0, min(1, float(time)))
        target = _imageObjectToPIL(targetImage).resize(size)
        transitionMask = _extentMask(size, extent, _clampByte(time * 255))
        base = _blendWithMask(self._pilImage(), target, transitionMask)
        flash = _radialLightImage(
            size,
            center,
            color,
            math.hypot(*size) * time,
            max(size),
            rays=True,
            rayRadius=maxStriationRadius,
            rayStrength=striationStrength,
            rayContrast=striationContrast,
            extent=extent,
        )
        fadeThreshold = max(0, min(1, float(fadeThreshold)))
        if fadeThreshold <= 0:
            flashAmount = 1 - time
        elif time <= fadeThreshold:
            flashAmount = time / fadeThreshold
        else:
            flashAmount = (1 - time) / max(1e-9, 1 - fadeThreshold)
        self._setPILImage(_screenBlend(base, flash, max(0, min(1, flashAmount))))

    def modTransition(
        self,
        targetImage,
        center=(150.0, 150.0),
        time=0.0,
        angle=2.0,
        radius=150.0,
        compression=300.0,
    ):
        if float(time) <= 0:
            return
        if float(time) >= 1:
            self._setPILImage(_imageObjectToPIL(targetImage).resize(self.size()))
            return
        target = _imageObjectToPIL(targetImage).resize(self.size())
        mask = _modTransitionMask(self.size(), center, time, angle, radius, compression)
        self._setPILImage(_blendWithMask(self._pilImage(), target, mask))

    def rippleTransition(
        self,
        targetImage,
        shadingImage,
        center=(150.0, 150.0),
        extent=(0.0, 0.0, 300.0, 300.0),
        time=0.0,
        width=100.0,
        scale=50.0,
    ):
        if float(time) <= 0:
            return
        if float(time) >= 1:
            self._setPILImage(_imageObjectToPIL(targetImage).resize(self.size()))
            return
        target = _imageObjectToPIL(targetImage).resize(self.size())
        shading = _imageObjectToPIL(shadingImage).resize(self.size())
        target = _rippleDistortImage(target, shading, center, width, scale, time)
        mask = _radialTransitionMask(
            self.size(),
            center,
            max(1, float(width)) * (1 + float(time) * 3),
            extent,
        )
        self._setPILImage(_blendWithMask(self._pilImage(), target, mask))

    def disintegrateWithMaskTransition(
        self,
        targetImage,
        maskImage,
        time=0.0,
        shadowRadius=8.0,
        shadowDensity=0.65,
        shadowOffset=(0.0, -10.0),
    ):
        if float(time) <= 0:
            return
        if float(time) >= 1:
            self._setPILImage(_imageObjectToPIL(targetImage).resize(self.size()))
            return
        target = _imageObjectToPIL(targetImage).resize(self.size())
        maskSource = _imageObjectToPIL(maskImage).resize(self.size()).convert("L")
        mask, shadow = _disintegrateMasks(
            maskSource,
            time,
            shadowRadius,
            shadowDensity,
            shadowOffset,
        )
        result = self._pilImage()
        if shadow is not None:
            result = _blendWithMask(result, _solidFromColor((0, 0, 0, 255), self.size()), shadow)
        self._setPILImage(_blendWithMask(result, target, mask))

    def accordionFoldTransition(
        self,
        targetImage,
        bottomHeight=0.0,
        numberOfFolds=3.0,
        foldShadowAmount=0.1,
        time=0.0,
    ):
        if float(time) <= 0:
            return
        if float(time) >= 1:
            self._setPILImage(_imageObjectToPIL(targetImage).resize(self.size()))
            return
        target = _imageObjectToPIL(targetImage).resize(self.size())
        self._setPILImage(
            _accordionFoldTransitionImage(
                self._pilImage(),
                target,
                bottomHeight,
                numberOfFolds,
                foldShadowAmount,
                time,
            )
        )

    def pageCurlTransition(
        self,
        targetImage,
        backsideImage,
        shadingImage,
        extent=(0.0, 0.0, 300.0, 300.0),
        time=0.0,
        angle=0.0,
        radius=100.0,
    ):
        if float(time) <= 0:
            return
        if float(time) >= 1:
            self._setPILImage(_imageObjectToPIL(targetImage).resize(self.size()))
            return
        target = _imageObjectToPIL(targetImage).resize(self.size())
        backside = _imageObjectToPIL(backsideImage).resize(self.size())
        shading = _imageObjectToPIL(shadingImage).resize(self.size())
        self._setPILImage(
            _pageCurlTransitionImage(
                self._pilImage(),
                target,
                backside,
                shading,
                extent,
                time,
                angle,
                radius,
            )
        )

    def pageCurlWithShadowTransition(
        self,
        targetImage,
        backsideImage,
        extent=(0.0, 0.0, 0.0, 0.0),
        time=0.0,
        angle=0.0,
        radius=100.0,
        shadowSize=0.5,
        shadowAmount=0.7,
        shadowExtent=(0.0, 0.0, 0.0, 0.0),
    ):
        if float(time) <= 0:
            return
        if float(time) >= 1:
            self._setPILImage(_imageObjectToPIL(targetImage).resize(self.size()))
            return
        target = _imageObjectToPIL(targetImage).resize(self.size())
        backside = _imageObjectToPIL(backsideImage).resize(self.size())
        self._setPILImage(
            _pageCurlTransitionImage(
                self._pilImage(),
                target,
                backside,
                None,
                extent,
                time,
                angle,
                radius,
                shadowSize,
                shadowAmount,
                shadowExtent,
            )
        )

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

    def blendWithRedMask(self, backgroundImage, maskImage):
        from PIL import Image

        source = self._pilImage()
        background = _imageObjectToPIL(backgroundImage).resize(source.size)
        mask = _imageObjectToPIL(maskImage).resize(source.size).getchannel("R")
        self._setPILImage(Image.composite(source, background, mask))

    def blendWithBlueMask(self, backgroundImage, maskImage):
        from PIL import Image

        source = self._pilImage()
        background = _imageObjectToPIL(backgroundImage).resize(source.size)
        mask = _imageObjectToPIL(maskImage).resize(source.size).getchannel("B")
        self._setPILImage(Image.composite(source, background, mask))

    def maskedVariableBlur(self, mask, radius=5.0):
        self._setPILImage(_maskedVariableBlurImage(self._pilImage(), _imageObjectToPIL(mask), radius))

    def edgePreserveUpsampleFilter(self, smallImage, spatialSigma=3.0, lumaSigma=0.15):
        self._setPILImage(
            _edgePreserveUpsampleImage(
                self._pilImage(),
                _imageObjectToPIL(smallImage),
                spatialSigma,
                lumaSigma,
            )
        )

    def photoEffectMono(self, extrapolate=False):
        image = self._monochromeImage()
        if extrapolate:
            from PIL import ImageEnhance

            image = ImageEnhance.Contrast(image).enhance(1.08)
        self._setPILImage(image)

    def photoEffectNoir(self, extrapolate=False):
        from PIL import ImageEnhance

        image = self._monochromeImage()
        image = ImageEnhance.Contrast(image).enhance(1.55 * _photoEffectAmount(extrapolate))
        self._setPILImage(image)

    def photoEffectTonal(self, extrapolate=False):
        image = self._monochromeImage()
        if extrapolate:
            from PIL import ImageEnhance

            image = ImageEnhance.Contrast(image).enhance(1.05)
        self._setPILImage(image)

    def photoEffectFade(self, extrapolate=False):
        from PIL import ImageEnhance

        image = self._pilImage()
        amount = _photoEffectAmount(extrapolate)
        image = ImageEnhance.Color(image).enhance(max(0, 1 - (1 - 0.65) * amount))
        image = ImageEnhance.Contrast(image).enhance(max(0, 1 - (1 - 0.85) * amount))
        self._setPILImage(image)

    def photoEffectInstant(self, extrapolate=False):
        from PIL import ImageEnhance

        amount = _photoEffectAmount(extrapolate)
        self.sepiaTone(0.45 * amount)
        self._setPILImage(ImageEnhance.Color(self._pilImage()).enhance(1 + (1.15 - 1) * amount))

    def photoEffectProcess(self, extrapolate=False):
        from PIL import ImageEnhance

        image = self._pilImage()
        amount = _photoEffectAmount(extrapolate)
        image = ImageEnhance.Color(image).enhance(1 + (1.35 - 1) * amount)
        image = ImageEnhance.Contrast(image).enhance(1 + (1.1 - 1) * amount)
        self._setPILImage(image)

    def photoEffectTransfer(self, extrapolate=False):
        from PIL import ImageEnhance

        amount = _photoEffectAmount(extrapolate)
        self.sepiaTone(0.25 * amount)
        self._setPILImage(ImageEnhance.Contrast(self._pilImage()).enhance(max(0, 1 - (1 - 0.9) * amount)))

    def photoEffectChrome(self, extrapolate=False):
        from PIL import ImageEnhance

        image = self._pilImage()
        amount = _photoEffectAmount(extrapolate)
        image = ImageEnhance.Color(image).enhance(1 + (1.4 - 1) * amount)
        image = ImageEnhance.Contrast(image).enhance(1 + (1.25 - 1) * amount)
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
        from PIL import Image
        from PIL import ImageFilter

        image = self._pilImage()
        percent = max(0, int(float(sharpness) * 250))
        if not percent:
            return
        y, cb, cr = image.convert("RGB").convert("YCbCr").split()
        y = y.filter(ImageFilter.UnsharpMask(radius=max(0, float(radius)), percent=percent))
        sharpened = Image.merge("YCbCr", (y, cb, cr)).convert("RGBA")
        sharpened.putalpha(image.getchannel("A"))
        self._setPILImage(sharpened)

    def lockFocus(self):
        if self._focusState is not None:
            raise DrawbotError("ImageObject focus is already locked")

        drawing = self._drawing
        if drawing is None:
            from . import drawbot

            drawing = drawbot._db
        self._focusState = (
            drawing,
            drawing._stack,
            drawing._gstate,
            drawing._path,
            drawing._colorSpace,
            drawing._document,
            drawing._skia_canvas,
        )
        drawing.newDrawing()

    def unlockFocus(self):
        if self._focusState is None:
            raise DrawbotError("ImageObject focus is not locked")
        from .document import _pictureToSkiaImage

        drawing, stack, gstate, path, colorSpace, document, skiaCanvas = self._focusState
        self._focusState = None
        try:
            if drawing._document.isDrawing:
                drawing._document.endPage()
                drawing._canvas = None
            if drawing._document._pictures:
                self._image = _pictureToSkiaImage(drawing._document._pictures[-1])
                self._path = None
                self._offset = (0, 0)
        finally:
            drawing._stack = stack
            drawing._gstate = gstate
            drawing._path = path
            drawing._colorSpace = colorSpace
            drawing._document = document
            drawing._skia_canvas = skiaCanvas

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

    def _affineTransform(self, transform):
        from PIL import Image

        xx, xy, yx, yy, dx, dy = transform
        image = self._pilImage()
        self._setPILImage(
            image.transform(
                image.size,
                Image.Transform.AFFINE,
                (xx, yx, dx, xy, yy, dy),
                resample=Image.Resampling.BICUBIC,
            )
        )

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


_BAYER4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def _ditherImage(image, intensity):
    intensity = max(0, min(1, float(intensity)))
    source = image.convert("RGBA")
    if intensity == 0:
        return source

    data = []
    for index, (r, g, b, a) in enumerate(_getImageData(source)):
        x = index % source.width
        y = index // source.width
        threshold = ((_BAYER4[y % 4][x % 4] + 0.5) / 16 - 0.5) * 255 * intensity
        data.append(
            (
                _clampByte(r + threshold),
                _clampByte(g + threshold),
                _clampByte(b + threshold),
                a,
            )
        )
    return _newRGBAWithData(source.size, data)


def _vibranceImage(image, amount):
    amount = float(amount)
    source = image.convert("RGBA")
    if amount == 0:
        return source

    data = []
    for r, g, b, a in _getImageData(source):
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        saturation = (max(r, g, b) - min(r, g, b)) / 255
        if amount > 0:
            factor = 1 + amount * (1 - saturation)
        else:
            factor = max(0, 1 + amount * saturation)
        data.append(
            (
                _clampByte(luminance + (r - luminance) * factor),
                _clampByte(luminance + (g - luminance) * factor),
                _clampByte(luminance + (b - luminance) * factor),
                a,
            )
        )
    return _newRGBAWithData(source.size, data)


def _reciprocalLuminanceImage(image):
    from PIL import Image

    luminance = image.convert("L")
    alpha = image.getchannel("A")
    values = [pixel for pixel in _getImageData(luminance) if pixel > 0]
    if not values:
        result = Image.new("RGBA", image.size, (255, 255, 255, 255))
        result.putalpha(alpha)
        return result
    reciprocals = [1 / pixel for pixel in values]
    minReciprocal = min(reciprocals)
    maxReciprocal = max(reciprocals)
    scale = (
        255 / (maxReciprocal - minReciprocal)
        if maxReciprocal != minReciprocal
        else 0
    )
    data = []
    for value, a in zip(_getImageData(luminance), _getImageData(alpha)):
        if value <= 0:
            mapped = 255
        elif scale:
            mapped = _clampByte((1 / value - minReciprocal) * scale)
        else:
            mapped = value
        data.append((mapped, mapped, mapped, a))
    return _newRGBAWithData(image.size, data)


def _gaborGradientsImage(image):
    gray = image.convert("L")
    alpha = image.getchannel("A")
    width, height = image.size
    source = list(_getImageData(gray))
    kernels = _gaborKernels(size=7, sigma=2.0, wavelength=4.0)
    responses = []
    for y in range(height):
        for x in range(width):
            energy = 0
            for kernel, kernelRadius in kernels:
                response = 0
                for ky, kernelRow in enumerate(kernel):
                    sampleY = max(0, min(height - 1, y + ky - kernelRadius))
                    rowOffset = sampleY * width
                    for kx, weight in enumerate(kernelRow):
                        sampleX = max(
                            0,
                            min(width - 1, x + kx - kernelRadius),
                        )
                        response += source[rowOffset + sampleX] * weight
                energy += response * response
            responses.append(math.sqrt(energy))
    maxResponse = max(responses) if responses else 0
    if not maxResponse:
        result = Image.new("RGBA", image.size, (0, 0, 0, 255))
        result.putalpha(alpha)
        return result
    data = []
    for response, a in zip(responses, _getImageData(alpha)):
        value = _clampByte(response / maxResponse * 255)
        data.append((value, value, value, a))
    return _newRGBAWithData(image.size, data)


def _comicEffectImage(image):
    from PIL import ImageFilter

    source = image.convert("RGBA")
    alpha = source.getchannel("A")
    posterized = source.convert("RGB").point(
        lambda value: _clampByte(round(value / 64) * 64)
    ).convert("RGBA")
    posterized.putalpha(alpha)
    edges = source.filter(ImageFilter.FIND_EDGES).convert("L")
    luminance = source.convert("L")
    posterizedPixels = list(_getImageData(posterized))
    edgePixels = list(_getImageData(edges))
    luminancePixels = list(_getImageData(luminance))
    alphaPixels = list(_getImageData(alpha))
    data = []
    cellSize = 4
    center = (cellSize - 1) / 2
    for index, (r, g, b, _a) in enumerate(posterizedPixels):
        if edgePixels[index] > 30:
            data.append((0, 0, 0, alphaPixels[index]))
            continue
        x = index % source.width
        y = index // source.width
        localX = x % cellSize
        localY = y % cellSize
        distance = math.hypot(localX - center, localY - center)
        radius = 0.45 + (1 - luminancePixels[index] / 255) * 1.25
        if distance <= radius:
            r = _clampByte(r * 0.58)
            g = _clampByte(g * 0.58)
            b = _clampByte(b * 0.58)
        data.append((r, g, b, alphaPixels[index]))
    return _newRGBAWithData(source.size, data)


def _gaborKernels(size=7, sigma=2.0, wavelength=4.0):
    radius = size // 2
    kernels = []
    for theta in (0, math.pi / 4, math.pi / 2, 3 * math.pi / 4):
        cosTheta = math.cos(theta)
        sinTheta = math.sin(theta)
        kernel = []
        total = 0
        for y in range(-radius, radius + 1):
            row = []
            for x in range(-radius, radius + 1):
                rotatedX = x * cosTheta + y * sinTheta
                rotatedY = -x * sinTheta + y * cosTheta
                gaussian = math.exp(
                    -(rotatedX * rotatedX + rotatedY * rotatedY) / (2 * sigma * sigma)
                )
                value = gaussian * math.cos(2 * math.pi * rotatedX / wavelength)
                row.append(value)
                total += value
            kernel.append(row)
        mean = total / (size * size)
        normalized = []
        weightSum = 0
        for row in kernel:
            normalizedRow = []
            for value in row:
                centered = value - mean
                normalizedRow.append(centered)
                weightSum += abs(centered)
            normalized.append(normalizedRow)
        if weightSum:
            normalized = [[value / weightSum for value in row] for row in normalized]
        kernels.append((normalized, radius))
    return kernels


def _thermalImage(image):
    return _luminanceRampImage(
        image,
        (
            (0.00, (0, 0, 0, 255)),
            (0.18, (44, 0, 80, 255)),
            (0.36, (0, 64, 192, 255)),
            (0.55, (0, 220, 220, 255)),
            (0.72, (255, 230, 0, 255)),
            (0.88, (255, 64, 0, 255)),
            (1.00, (255, 255, 255, 255)),
        ),
    )


def _xrayImage(image):
    return _luminanceRampImage(
        image,
        (
            (0.00, (235, 250, 255, 255)),
            (0.25, (138, 205, 235, 255)),
            (0.50, (42, 96, 158, 255)),
            (0.75, (10, 32, 78, 255)),
            (1.00, (0, 0, 10, 255)),
        ),
    )


def _luminanceRampImage(image, stops):
    gray = image.convert("L")
    alpha = image.getchannel("A")
    data = []
    for value, a in zip(_getImageData(gray), _getImageData(alpha)):
        position = value / 255
        for index, (stopPosition, color) in enumerate(stops[1:], start=1):
            if position <= stopPosition:
                previousPosition, previousColor = stops[index - 1]
                span = stopPosition - previousPosition
                amount = 0 if span == 0 else (position - previousPosition) / span
                r, g, b, _ = _mixRGBABytes(previousColor, color, amount)
                data.append((r, g, b, a))
                break
        else:
            r, g, b, _ = stops[-1][1]
            data.append((r, g, b, a))
    return _newRGBAWithData(image.size, data)


def _photoEffectAmount(extrapolate):
    return 1.25 if extrapolate else 1.0


def _mergeRGBA(r, g, b, a):
    from PIL import Image

    return Image.merge("RGBA", (r, g, b, a))


def _morphologyRectangleImage(image, width, height, darker):
    from PIL import Image

    source = image.convert("RGBA")
    kernelWidth = max(1, int(round(float(width))))
    kernelHeight = max(1, int(round(float(height))))
    if kernelWidth % 2 == 0:
        kernelWidth += 1
    if kernelHeight % 2 == 0:
        kernelHeight += 1
    if kernelWidth == 1 and kernelHeight == 1:
        return source

    result = Image.new("RGBA", source.size)
    sourcePixels = source.load()
    resultPixels = result.load()
    radiusX = kernelWidth // 2
    radiusY = kernelHeight // 2
    for y in range(source.height):
        top = max(0, y - radiusY)
        bottom = min(source.height, y + radiusY + 1)
        for x in range(source.width):
            left = max(0, x - radiusX)
            right = min(source.width, x + radiusX + 1)
            values = [255, 255, 255, 255] if darker else [0, 0, 0, 0]
            for sampleY in range(top, bottom):
                for sampleX in range(left, right):
                    pixel = sourcePixels[sampleX, sampleY]
                    if darker:
                        values = [min(values[i], pixel[i]) for i in range(4)]
                    else:
                        values = [max(values[i], pixel[i]) for i in range(4)]
            resultPixels[x, y] = tuple(values)
    return result


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


def _stretchCropImage(image, size, cropAmount, centerStretchAmount):
    targetWidth, targetHeight = _normalizeSize(size)
    source = image.convert("RGBA")
    cropAmount = max(0, min(1, float(cropAmount)))
    sourceRatio = source.width / source.height
    targetRatio = targetWidth / targetHeight
    left = 0
    top = 0
    right = source.width
    bottom = source.height
    if sourceRatio > targetRatio:
        fittedWidth = source.height * targetRatio
        cropWidth = source.width + (fittedWidth - source.width) * cropAmount
        left = (source.width - cropWidth) / 2
        right = left + cropWidth
    elif sourceRatio < targetRatio:
        fittedHeight = source.width / targetRatio
        cropHeight = source.height + (fittedHeight - source.height) * cropAmount
        top = (source.height - cropHeight) / 2
        bottom = top + cropHeight
    cropped = source.crop((int(round(left)), int(round(top)), int(round(right)), int(round(bottom))))
    return _centerStretchResize(cropped, targetWidth, targetHeight, centerStretchAmount)


def _centerStretchResize(image, targetWidth, targetHeight, amount):
    from PIL import Image

    amount = max(0, min(1, float(amount)))
    if amount >= 0.999:
        return image.resize((targetWidth, targetHeight), Image.Resampling.BICUBIC)
    resized = image.convert("RGBA")
    if resized.width != targetWidth:
        resized = _centerStretchAxis(resized, targetWidth, amount, axis=0)
    if resized.height != targetHeight:
        resized = _centerStretchAxis(resized, targetHeight, amount, axis=1)
    return resized


def _centerStretchAxis(image, targetLength, amount, axis):
    from PIL import Image

    sourceWidth, sourceHeight = image.size
    sourceLength = sourceWidth if axis == 0 else sourceHeight
    targetLength = max(1, int(round(targetLength)))
    if sourceLength == targetLength:
        return image.copy()
    centerSourceLength = max(1, int(round(sourceLength * amount)))
    sideSourceLength = max(0, (sourceLength - centerSourceLength) // 2)
    centerSourceStart = sideSourceLength
    centerSourceEnd = sourceLength - sideSourceLength
    centerTargetLength = max(1, targetLength - 2 * sideSourceLength)
    if centerTargetLength < 1 or 2 * sideSourceLength >= targetLength:
        sideSourceLength = max(0, (targetLength - 1) // 2)
        centerSourceStart = min(sideSourceLength, sourceLength - 1)
        centerSourceEnd = max(centerSourceStart + 1, sourceLength - sideSourceLength)
        centerTargetLength = max(1, targetLength - 2 * sideSourceLength)
    resultSize = (targetLength, sourceHeight) if axis == 0 else (sourceWidth, targetLength)
    result = Image.new("RGBA", resultSize)
    if axis == 0:
        if sideSourceLength:
            result.paste(image.crop((0, 0, sideSourceLength, sourceHeight)), (0, 0))
            right = image.crop((sourceLength - sideSourceLength, 0, sourceLength, sourceHeight))
            result.paste(right, (targetLength - sideSourceLength, 0))
        center = image.crop((centerSourceStart, 0, centerSourceEnd, sourceHeight))
        center = center.resize((centerTargetLength, sourceHeight), Image.Resampling.BICUBIC)
        result.paste(center, (sideSourceLength, 0))
    else:
        if sideSourceLength:
            result.paste(image.crop((0, 0, sourceWidth, sideSourceLength)), (0, 0))
            bottom = image.crop((0, sourceLength - sideSourceLength, sourceWidth, sourceLength))
            result.paste(bottom, (0, targetLength - sideSourceLength))
        center = image.crop((0, centerSourceStart, sourceWidth, centerSourceEnd))
        center = center.resize((sourceWidth, centerTargetLength), Image.Resampling.BICUBIC)
        result.paste(center, (0, sideSourceLength))
    return result


def _mixColor(color0, color1, amount):
    amount = max(0, min(1, float(amount)))
    c0 = _colorToRGBABytes(color0)
    c1 = _colorToRGBABytes(color1)
    return tuple(_clampByte(a + (b - a) * amount) for a, b in zip(c0, c1))


def _mixRGBABytes(color0, color1, amount):
    amount = max(0, min(1, float(amount)))
    return tuple(_clampByte(a + (b - a) * amount) for a, b in zip(color0, color1))


def _rgbBytesToLab(r, g, b):
    x, y, z = _rgbBytesToXYZ(r, g, b)
    x /= 0.95047
    z /= 1.08883
    fx = _labPivotXYZ(x)
    fy = _labPivotXYZ(y)
    fz = _labPivotXYZ(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _rgbBytesToXYZ(r, g, b):
    r, g, b = (_srgbToLinear(component / 255) for component in (r, g, b))
    return (
        r * 0.4124564 + g * 0.3575761 + b * 0.1804375,
        r * 0.2126729 + g * 0.7151522 + b * 0.0721750,
        r * 0.0193339 + g * 0.1191920 + b * 0.9503041,
    )


def _labToBytes(l, a, b, normalize=False):
    # In this byte-backed image pipeline, normalized Lab channels are encoded
    # into 8-bit RGBA just like the existing packed Lab representation.
    return _labToPackedBytes(l, a, b)


def _labToPackedBytes(l, a, b):
    return _clampByte(l * 255 / 100), _clampByte(a + 128), _clampByte(b + 128)


def _labBytesToRGB(l, a, b, normalize=False):
    return _packedLabBytesToRGB(l, a, b)


def _packedLabBytesToRGB(l, a, b):
    l = l * 100 / 255
    a = a - 128
    b = b - 128
    fy = (l + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200
    x = 0.95047 * _labPivotInv(fx)
    y = _labPivotInv(fy)
    z = 1.08883 * _labPivotInv(fz)
    return _xyzToRGBBytes(x, y, z)


def _paletteColors(paletteImage):
    colors = []
    seen = set()
    for r, g, b, a in _getImageData(paletteImage.convert("RGBA")):
        if a == 0:
            continue
        color = (r, g, b)
        if color not in seen:
            colors.append(color)
            seen.add(color)
    return colors or [(0, 0, 0)]


def _kMeansSeedColors(means):
    if isinstance(means, ImageObject) or isinstance(means, (str, os.PathLike)):
        return [
            tuple(float(value) for value in color)
            for color in _paletteColors(_imageObjectToPIL(means))
        ]
    colors = []
    for color in means:
        colors.append(tuple(float(value) for value in _colorToRGBABytes(color)[:3]))
    return colors


def _palettizedImage(image, palette, perceptual=False):
    data = []
    paletteWithLab = [(color, _rgbBytesToLab(*color)) for color in palette] if perceptual else None
    for r, g, b, a in _getImageData(image.convert("RGBA")):
        color = _nearestPaletteColor((r, g, b), palette, paletteWithLab)
        data.append((*color, a))
    return _newRGBAWithData(image.size, data)


def _paletteCentroidImage(image, palette, perceptual=False):
    assignments = [
        {
            "count": 0,
            "r": 0,
            "g": 0,
            "b": 0,
            "a": 0,
        }
        for _ in palette
    ]
    paletteWithLab = [(color, _rgbBytesToLab(*color)) for color in palette] if perceptual else None
    for r, g, b, a in _getImageData(image.convert("RGBA")):
        index = _nearestPaletteIndex((r, g, b), palette, paletteWithLab)
        bucket = assignments[index]
        bucket["count"] += 1
        bucket["r"] += r
        bucket["g"] += g
        bucket["b"] += b
        bucket["a"] += a
    total = image.width * image.height or 1
    data = []
    for color, bucket in zip(palette, assignments):
        if bucket["count"]:
            count = bucket["count"]
            data.append(
                (
                    _clampByte(bucket["r"] / count),
                    _clampByte(bucket["g"] / count),
                    _clampByte(bucket["b"] / count),
                    _clampByte(count / total * 255),
                )
            )
        else:
            data.append((*color, 0))
    return _newRGBAWithData((len(palette), 1), data)


def _nearestPaletteColor(color, palette, paletteWithLab=None):
    return palette[_nearestPaletteIndex(color, palette, paletteWithLab)]


def _nearestPaletteIndex(color, palette, paletteWithLab=None):
    if paletteWithLab is not None:
        lab = _rgbBytesToLab(*color)
        return min(
            range(len(paletteWithLab)),
            key=lambda index: _distanceSquared(lab, paletteWithLab[index][1]),
        )
    return min(
        range(len(palette)),
        key=lambda index: _distanceSquared(color, palette[index]),
    )


def _distanceSquared(color1, color2):
    return sum((a - b) ** 2 for a, b in zip(color1, color2))


def _spotColorAmount(pixel, center, closeness, contrast):
    closeness = max(0, float(closeness))
    if closeness == 0:
        return 0
    contrast = max(0, min(1, float(contrast)))
    distance = math.sqrt(_distanceSquared(pixel, center)) / (255 * math.sqrt(3))
    if distance > closeness:
        return 0
    transitionWidth = closeness * (1 - contrast)
    if transitionWidth <= 1e-9:
        return 1
    solidRadius = closeness - transitionWidth
    if distance <= solidRadius:
        return 1
    amount = (closeness - distance) / transitionWidth
    return max(0, min(1, amount))


def _xyzToRGBBytes(x, y, z):
    r = x * 3.2404542 + y * -1.5371385 + z * -0.4985314
    g = x * -0.9692660 + y * 1.8760108 + z * 0.0415560
    b = x * 0.0556434 + y * -0.2040259 + z * 1.0572252
    return tuple(_linearToSrgbByte(component) for component in (r, g, b))


def _srgbToLinear(value):
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _linearToSrgbByte(value):
    value = max(0, min(1, value))
    if value <= 0.0031308:
        srgb = value * 12.92
    else:
        srgb = 1.055 * (value ** (1 / 2.4)) - 0.055
    return _clampByte(srgb * 255)


def _labPivotXYZ(value):
    epsilon = 216 / 24389
    kappa = 24389 / 27
    if value > epsilon:
        return value ** (1 / 3)
    return (kappa * value + 16) / 116


def _labPivotInv(value):
    epsilon = 216 / 24389
    kappa = 24389 / 27
    value3 = value ** 3
    if value3 > epsilon:
        return value3
    return (116 * value - 16) / kappa


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


def _pseudoBarcodeImage(size, message, kind):
    from PIL import Image
    from PIL import ImageDraw

    width, height = _normalizeSize(size)
    image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    seed = f"{kind}:{message}".encode("utf-8")
    bits = []
    state = sum(seed) or 1
    for byte in seed:
        state = (state * 1103515245 + byte + 12345) & 0x7FFFFFFF
        bits.extend((state >> shift) & 1 for shift in range(16))
    if kind in {"qr", "aztec"}:
        cells = 29 if kind == "qr" else 31
        cellSize = max(1, min(width, height) // cells)
        left = (width - cellSize * cells) // 2
        top = (height - cellSize * cells) // 2
        for y in range(cells):
            for x in range(cells):
                finder = (
                    (x < 7 and y < 7)
                    or (x >= cells - 7 and y < 7)
                    or (x < 7 and y >= cells - 7)
                    or (kind == "aztec" and abs(x - cells // 2) <= 4 and abs(y - cells // 2) <= 4)
                )
                if finder or bits[(x + y * cells) % len(bits)]:
                    draw.rectangle(
                        (left + x * cellSize, top + y * cellSize, left + (x + 1) * cellSize - 1, top + (y + 1) * cellSize - 1),
                        fill=(0, 0, 0, 255),
                    )
    else:
        barCount = 80 if kind == "code128" else 36
        x = 0
        for index in range(barCount):
            barWidth = 1 + bits[index % len(bits)] * 2
            if index % 2 == 0:
                draw.rectangle((x, 0, min(width, x + barWidth), height), fill=(0, 0, 0, 255))
            x += max(1, width // barCount) * barWidth
            if x >= width:
                break
    return image


def _aztecCodeImage(size, message, correctionLevel=23.0, layers=0.0, compactStyle=False):
    from PIL import Image
    from aztec_code_generator import AztecCode

    width, height = _normalizeSize(size)
    ecPercent = max(5, min(95, int(round(float(correctionLevel)))))
    layerCount = max(0, int(round(float(layers))))
    compact = bool(compactStyle)
    if layerCount:
        matrixSize = (11 if compact else 15) + layerCount * 4
        code = AztecCode(str(message), size=matrixSize, compact=compact, ec_percent=ecPercent)
    else:
        code = AztecCode(str(message), ec_percent=ecPercent)
    barcode = code.image(module_size=1, border=0).convert("RGBA")
    targetSize = max(1, min(width, height))
    barcode = barcode.resize((targetSize, targetSize), Image.Resampling.NEAREST)
    image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    image.alpha_composite(barcode, ((width - targetSize) // 2, (height - targetSize) // 2))
    return image


def _pdf417BarcodeImage(
    size,
    message,
    minWidth=0.0,
    maxWidth=0.0,
    minHeight=0.0,
    maxHeight=0.0,
    dataColumns=0.0,
    rows=0.0,
    preferredAspectRatio=0.0,
    compactionMode=0.0,
    compactStyle=False,
    correctionLevel=0.0,
    alwaysSpecifyCompaction=False,
):
    from PIL import Image
    import pdf417gen

    width, height = _normalizeSize(size)
    securityLevel = max(0, min(8, int(round(float(correctionLevel)))))
    columns = _pdf417Columns(dataColumns, rows, message, securityLevel)
    for candidateColumns in range(columns, 0, -1):
        try:
            codes = _pdf417Encode(
                message,
                candidateColumns,
                securityLevel,
                compactionMode,
                alwaysSpecifyCompaction,
            )
            break
        except ValueError:
            if candidateColumns == 1:
                raise
    if compactStyle:
        codes = _pdf417CompactRows(codes)
    barcode = pdf417gen.render_image(codes, scale=1, ratio=3, padding=0).convert("RGBA")
    targetWidth, targetHeight = _pdf417TargetSize(width, height, minWidth, maxWidth, minHeight, maxHeight, preferredAspectRatio)
    barcode = barcode.resize((targetWidth, targetHeight), Image.Resampling.NEAREST)
    image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    image.alpha_composite(barcode, ((width - targetWidth) // 2, (height - targetHeight) // 2))
    return image


def _pdf417Columns(dataColumns, rows, message, securityLevel=2):
    if dataColumns:
        return max(1, min(30, int(round(float(dataColumns)))))
    if rows:
        rowCount = max(1, int(round(float(rows))))
        # PDF417 stores one length descriptor plus data and ECC codewords. This
        # estimate lets the DrawBot rows argument influence layout without
        # reimplementing pdf417gen's high-level compaction planner.
        estimatedCodewords = len(str(message).encode("utf-8")) + 1 + (2 << securityLevel)
        return max(1, min(30, int(math.ceil(estimatedCodewords / rowCount))))
    return 6


def _pdf417Encode(message, columns, securityLevel, compactionMode=0.0, alwaysSpecifyCompaction=False):
    import pdf417gen

    mode = int(round(float(compactionMode or 0)))
    if mode == 0 and not alwaysSpecifyCompaction:
        return pdf417gen.encode(str(message), columns=columns, security_level=securityLevel)

    data = str(message).encode("utf-8")
    dataWords = _pdf417ForcedDataWords(data, mode, alwaysSpecifyCompaction)
    return _pdf417EncodeDataWords(dataWords, columns, securityLevel)


def _pdf417ForcedDataWords(data, compactionMode, alwaysSpecifyCompaction):
    from pdf417gen.compaction import BYTE_LATCH, BYTE_LATCH_ALT, NUMERIC_LATCH, TEXT_LATCH
    from pdf417gen.compaction.byte import compact_bytes
    from pdf417gen.compaction.numeric import compact_numbers
    from pdf417gen.compaction.text import compact_text

    if compactionMode == 0:
        from pdf417gen.compaction import compact

        return list(compact(data))
    if compactionMode == 1:
        words = list(compact_text(data))
        return ([TEXT_LATCH] if alwaysSpecifyCompaction else []) + words
    if compactionMode == 2:
        latch = BYTE_LATCH_ALT if len(data) % 6 == 0 else BYTE_LATCH
        return [latch] + list(compact_bytes(data))
    if compactionMode == 3:
        return [NUMERIC_LATCH] + list(compact_numbers(data))
    raise ValueError(f"unsupported PDF417 compactionMode: {compactionMode}")


def _pdf417EncodeDataWords(dataWords, columns, securityLevel):
    from pdf417gen.encoding import encode_rows, get_padding, validate_barcode_size
    from pdf417gen.error_correction import compute_error_correction_code_words
    from pdf417gen.util import chunks

    ecCount = 2 ** (securityLevel + 1)
    paddingWords = get_padding(len(dataWords), ecCount, columns)
    lengthDescriptor = len(dataWords) + len(paddingWords) + 1
    codewordCount = lengthDescriptor + ecCount
    rowCount = math.ceil(codewordCount / columns)
    validate_barcode_size(lengthDescriptor, rowCount)
    extendedWords = [lengthDescriptor] + dataWords + paddingWords
    ecWords = compute_error_correction_code_words(extendedWords, securityLevel)
    rows = list(chunks(extendedWords + ecWords, columns))
    return list(encode_rows(rows, columns, securityLevel))


def _pdf417CompactRows(codes):
    return [row[:-2] + row[-1:] for row in codes]


def _pdf417TargetSize(width, height, minWidth, maxWidth, minHeight, maxHeight, preferredAspectRatio):
    targetWidth = width
    targetHeight = height
    minWidth = max(0, int(round(float(minWidth))))
    maxWidth = max(0, int(round(float(maxWidth))))
    minHeight = max(0, int(round(float(minHeight))))
    maxHeight = max(0, int(round(float(maxHeight))))
    if minWidth:
        targetWidth = max(targetWidth, minWidth)
    if maxWidth:
        targetWidth = min(targetWidth, maxWidth)
    if minHeight:
        targetHeight = max(targetHeight, minHeight)
    if maxHeight:
        targetHeight = min(targetHeight, maxHeight)
    if preferredAspectRatio:
        ratio = abs(float(preferredAspectRatio))
        if ratio:
            if targetWidth / targetHeight > ratio:
                targetWidth = int(round(targetHeight * ratio))
            else:
                targetHeight = int(round(targetWidth / ratio))
    return max(1, min(width, targetWidth)), max(1, min(height, targetHeight))


_QR_ECC_FORMAT_BITS = {
    "L": 1,
    "M": 0,
    "Q": 3,
    "H": 2,
}

_QR_RS_BLOCKS = {
    # version, level: (error correction codewords per block, (block count, data codewords)...)
    (1, "L"): (7, ((1, 19),)),
    (1, "M"): (10, ((1, 16),)),
    (1, "Q"): (13, ((1, 13),)),
    (1, "H"): (17, ((1, 9),)),
    (2, "L"): (10, ((1, 34),)),
    (2, "M"): (16, ((1, 28),)),
    (2, "Q"): (22, ((1, 22),)),
    (2, "H"): (28, ((1, 16),)),
    (3, "L"): (15, ((1, 55),)),
    (3, "M"): (26, ((1, 44),)),
    (3, "Q"): (18, ((2, 17),)),
    (3, "H"): (22, ((2, 13),)),
    (4, "L"): (20, ((1, 80),)),
    (4, "M"): (18, ((2, 32),)),
    (4, "Q"): (26, ((2, 24),)),
    (4, "H"): (16, ((4, 9),)),
}

_QR_ALIGNMENT_POSITIONS = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
}


def _qrCodeImage(size, message, correctionLevel="M"):
    from PIL import Image
    from PIL import ImageDraw

    width, height = _normalizeSize(size)
    matrix = _qrMatrix(message, correctionLevel)
    moduleCount = len(matrix)
    quiet = 4
    scale = max(1, min(width, height) // (moduleCount + quiet * 2))
    codeSize = moduleCount * scale
    left = max(0, (width - codeSize) // 2)
    top = max(0, (height - codeSize) // 2)
    image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    for y, row in enumerate(matrix):
        for x, value in enumerate(row):
            if value:
                draw.rectangle(
                    (
                        left + x * scale,
                        top + y * scale,
                        left + (x + 1) * scale - 1,
                        top + (y + 1) * scale - 1,
                    ),
                    fill=(0, 0, 0, 255),
                )
    return image


def _qrMatrix(message, correctionLevel="M"):
    data = str(message).encode("utf-8")
    level = str(correctionLevel or "M").upper()[0]
    if level not in _QR_ECC_FORMAT_BITS:
        level = "M"
    version = _qrVersionForData(len(data), level)
    dataCodewords = _qrDataCodewords(version, level)
    bits = [0, 1, 0, 0]
    countBits = 8 if version <= 9 else 16
    bits.extend(_intBits(len(data), countBits))
    for byte in data:
        bits.extend(_intBits(byte, 8))
    capacityBits = dataCodewords * 8
    bits.extend([0] * min(4, capacityBits - len(bits)))
    while len(bits) % 8:
        bits.append(0)
    codewords = [_bitsToInt(bits[index:index + 8]) for index in range(0, len(bits), 8)]
    pad = 0
    while len(codewords) < dataCodewords:
        codewords.append(0xEC if pad % 2 == 0 else 0x11)
        pad += 1
    allCodewords = _qrInterleavedCodewords(version, level, codewords)
    base, reserved = _qrBaseMatrix(version)
    dataBits = []
    for codeword in allCodewords:
        dataBits.extend(_intBits(codeword, 8))
    bestMatrix = None
    bestPenalty = None
    bestMask = 0
    for mask in range(8):
        matrix = [row[:] for row in base]
        _qrPlaceData(matrix, reserved, dataBits, mask)
        _qrPlaceFormatBits(matrix, level, mask)
        penalty = _qrPenalty(matrix)
        if bestPenalty is None or penalty < bestPenalty:
            bestMatrix = matrix
            bestPenalty = penalty
            bestMask = mask
    _qrPlaceFormatBits(bestMatrix, level, bestMask)
    return bestMatrix


def _qrVersionForData(dataLength, level):
    for version in sorted({version for version, blockLevel in _QR_RS_BLOCKS if blockLevel == level}):
        capacityBits = _qrDataCodewords(version, level) * 8
        countBits = 8 if version <= 9 else 16
        requiredBits = 4 + countBits + dataLength * 8
        if requiredBits <= capacityBits:
            return version
    raise ValueError("QRCodeGenerator message is too long for the built-in QR encoder")


def _qrDataCodewords(version, level):
    return sum(count * dataCount for count, dataCount in _QR_RS_BLOCKS[(version, level)][1])


def _qrInterleavedCodewords(version, level, dataCodewords):
    eccCount, blockGroups = _QR_RS_BLOCKS[(version, level)]
    blocks = []
    index = 0
    for count, dataCount in blockGroups:
        for _ in range(count):
            dataBlock = dataCodewords[index:index + dataCount]
            index += dataCount
            blocks.append((dataBlock, _qrReedSolomonRemainder(dataBlock, eccCount)))
    result = []
    maxDataLength = max(len(dataBlock) for dataBlock, _ in blocks)
    for offset in range(maxDataLength):
        for dataBlock, _ in blocks:
            if offset < len(dataBlock):
                result.append(dataBlock[offset])
    for offset in range(eccCount):
        for _, eccBlock in blocks:
            result.append(eccBlock[offset])
    return result


def _qrBaseMatrix(version):
    size = version * 4 + 17
    matrix = [[False] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]

    def setModule(x, y, value=True, reserve=True):
        if 0 <= x < size and 0 <= y < size:
            matrix[y][x] = value
            if reserve:
                reserved[y][x] = True

    def finder(left, top):
        for y in range(-1, 8):
            for x in range(-1, 8):
                xx = left + x
                yy = top + y
                if 0 <= xx < size and 0 <= yy < size:
                    dark = 0 <= x <= 6 and 0 <= y <= 6 and (
                        x in (0, 6)
                        or y in (0, 6)
                        or (2 <= x <= 4 and 2 <= y <= 4)
                    )
                    setModule(xx, yy, dark)

    finder(0, 0)
    finder(size - 7, 0)
    finder(0, size - 7)

    for index in range(8, size - 8):
        setModule(index, 6, index % 2 == 0)
        setModule(6, index, index % 2 == 0)

    positions = _QR_ALIGNMENT_POSITIONS[version]
    for cy in positions:
        for cx in positions:
            if reserved[cy][cx]:
                continue
            for y in range(-2, 3):
                for x in range(-2, 3):
                    setModule(cx + x, cy + y, max(abs(x), abs(y)) != 1)

    for index in range(15):
        if index < 6:
            setModule(8, index, False)
        elif index < 8:
            setModule(8, index + 1, False)
        else:
            setModule(8, size - 15 + index, False)
        if index < 8:
            setModule(size - index - 1, 8, False)
        elif index < 9:
            setModule(15 - index, 8, False)
        else:
            setModule(14 - index, 8, False)
    setModule(8, size - 8, True)
    return matrix, reserved


def _qrPlaceData(matrix, reserved, dataBits, mask):
    size = len(matrix)
    bitIndex = 0
    row = size - 1
    direction = -1
    for col in range(size - 1, 0, -2):
        if col <= 6:
            col -= 1
        while True:
            for xx in (col, col - 1):
                if not reserved[row][xx]:
                    bit = bitIndex < len(dataBits) and dataBits[bitIndex]
                    bitIndex += 1
                    if _qrMask(mask, xx, row):
                        bit = not bit
                    matrix[row][xx] = bool(bit)
            row += direction
            if row < 0 or size <= row:
                row -= direction
                direction = -direction
                break


def _qrPlaceFormatBits(matrix, level, mask):
    size = len(matrix)
    bits = _qrFormatBits(level, mask)
    for index in range(15):
        value = bool((bits >> index) & 1)
        if index < 6:
            matrix[index][8] = value
        elif index < 8:
            matrix[index + 1][8] = value
        else:
            matrix[size - 15 + index][8] = value

    for index in range(15):
        value = bool((bits >> index) & 1)
        if index < 8:
            matrix[8][size - index - 1] = value
        elif index < 9:
            matrix[8][15 - index] = value
        else:
            matrix[8][14 - index] = value
    matrix[size - 8][8] = True


def _qrFormatBits(level, mask):
    value = (_QR_ECC_FORMAT_BITS[level] << 3) | mask
    bits = value << 10
    generator = 0x537
    for shift in range(14, 9, -1):
        if (bits >> shift) & 1:
            bits ^= generator << (shift - 10)
    return ((value << 10) | bits) ^ 0x5412


def _qrMask(mask, x, y):
    if mask == 0:
        return (x + y) % 2 == 0
    if mask == 1:
        return y % 2 == 0
    if mask == 2:
        return x % 3 == 0
    if mask == 3:
        return (x + y) % 3 == 0
    if mask == 4:
        return (x // 3 + y // 2) % 2 == 0
    if mask == 5:
        return ((x * y) % 2) + ((x * y) % 3) == 0
    if mask == 6:
        return (((x * y) % 2) + ((x * y) % 3)) % 2 == 0
    return (((x + y) % 2) + ((x * y) % 3)) % 2 == 0


def _qrPenalty(matrix):
    size = len(matrix)
    penalty = 0
    lines = matrix + [[matrix[y][x] for y in range(size)] for x in range(size)]
    for line in lines:
        runColor = line[0]
        runLength = 1
        for value in line[1:]:
            if value == runColor:
                runLength += 1
            else:
                if runLength >= 5:
                    penalty += 3 + runLength - 5
                runColor = value
                runLength = 1
        if runLength >= 5:
            penalty += 3 + runLength - 5

    for y in range(size - 1):
        for x in range(size - 1):
            value = matrix[y][x]
            if (
                matrix[y][x + 1] == value
                and matrix[y + 1][x] == value
                and matrix[y + 1][x + 1] == value
            ):
                penalty += 3

    pattern = [True, False, True, True, True, False, True, False, False, False, False]
    reversePattern = list(reversed(pattern))
    for line in lines:
        for index in range(size - 10):
            window = line[index:index + 11]
            if window == pattern or window == reversePattern:
                penalty += 40

    dark = sum(sum(1 for value in row if value) for row in matrix)
    percent = dark * 100 / (size * size)
    penalty += int(abs(percent - 50) // 5) * 10
    return penalty


_QR_GF_EXP = [0] * 512
_QR_GF_LOG = [0] * 256
_qrValue = 1
for _qrIndex in range(255):
    _QR_GF_EXP[_qrIndex] = _qrValue
    _QR_GF_LOG[_qrValue] = _qrIndex
    _qrValue <<= 1
    if _qrValue & 0x100:
        _qrValue ^= 0x11D
for _qrIndex in range(255, 512):
    _QR_GF_EXP[_qrIndex] = _QR_GF_EXP[_qrIndex - 255]


def _qrGFMul(a, b):
    if a == 0 or b == 0:
        return 0
    return _QR_GF_EXP[_QR_GF_LOG[a] + _QR_GF_LOG[b]]


def _qrGeneratorPolynomial(degree):
    poly = [1]
    for index in range(degree):
        nextPoly = [0] * (len(poly) + 1)
        for coefficientIndex, coefficient in enumerate(poly):
            nextPoly[coefficientIndex] ^= _qrGFMul(coefficient, 1)
            nextPoly[coefficientIndex + 1] ^= _qrGFMul(coefficient, _QR_GF_EXP[index])
        poly = nextPoly
    return poly


def _qrReedSolomonRemainder(data, degree):
    generator = _qrGeneratorPolynomial(degree)
    result = [0] * degree
    for byte in data:
        factor = byte ^ result.pop(0)
        result.append(0)
        if factor:
            for index in range(degree):
                result[index] ^= _qrGFMul(generator[index + 1], factor)
    return result


def _intBits(value, width):
    return [(value >> shift) & 1 for shift in range(width - 1, -1, -1)]


def _bitsToInt(bits):
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


_CODE128_PATTERNS = [
    "11011001100", "11001101100", "11001100110", "10010011000", "10010001100",
    "10001001100", "10011001000", "10011000100", "10001100100", "11001001000",
    "11001000100", "11000100100", "10110011100", "10011011100", "10011001110",
    "10111001100", "10011101100", "10011100110", "11001110010", "11001011100",
    "11001001110", "11011100100", "11001110100", "11101101110", "11101001100",
    "11100101100", "11100100110", "11101100100", "11100110100", "11100110010",
    "11011011000", "11011000110", "11000110110", "10100011000", "10001011000",
    "10001000110", "10110001000", "10001101000", "10001100010", "11010001000",
    "11000101000", "11000100010", "10110111000", "10110001110", "10001101110",
    "10111011000", "10111000110", "10001110110", "11101110110", "11010001110",
    "11000101110", "11011101000", "11011100010", "11011101110", "11101011000",
    "11101000110", "11100010110", "11101101000", "11101100010", "11100011010",
    "11101111010", "11001000010", "11110001010", "10100110000", "10100001100",
    "10010110000", "10010000110", "10000101100", "10000100110", "10110010000",
    "10110000100", "10011010000", "10011000010", "10000110100", "10000110010",
    "11000010010", "11001010000", "11110111010", "11000010100", "10001111010",
    "10100111100", "10010111100", "10010011110", "10111100100", "10011110100",
    "10011110010", "11110100100", "11110010100", "11110010010", "11011011110",
    "11011110110", "11110110110", "10101111000", "10100011110", "10001011110",
    "10111101000", "10111100010", "11110101000", "11110100010", "10111011110",
    "10111101110", "11101011110", "11110101110", "11010000100", "11010010000",
    "11010011100", "1100011101011",
]


def _code128BarcodeImage(size, message, quietSpace=10.0, barcodeHeight=32.0):
    from PIL import Image
    from PIL import ImageDraw

    width, height = _normalizeSize(size)
    quietSpace = max(0, float(quietSpace))
    barcodeHeight = max(1, min(height, float(barcodeHeight)))
    message = str(message)
    codes = []
    for character in message:
        code = ord(character) - 32
        if not 0 <= code <= 95:
            code = ord("?") - 32
        codes.append(code)
    checksum = 104
    for index, code in enumerate(codes, start=1):
        checksum += index * code
    sequence = [104, *codes, checksum % 103, 106]
    pattern = "".join(_CODE128_PATTERNS[code] for code in sequence)
    image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    availableWidth = max(1, width - quietSpace * 2)
    moduleWidth = availableWidth / len(pattern)
    top = max(0, (height - barcodeHeight) / 2)
    bottom = min(height, top + barcodeHeight)
    for index, bit in enumerate(pattern):
        if bit == "1":
            left = quietSpace + index * moduleWidth
            right = quietSpace + (index + 1) * moduleWidth
            draw.rectangle((left, top, right, bottom), fill=(0, 0, 0, 255))
    return image


def _radialLightImage(
    size,
    center,
    color,
    radius,
    width,
    rays=False,
    rayRadius=2.58,
    rayStrength=0.5,
    rayContrast=1.0,
    rayTime=0.0,
    extent=None,
):
    from PIL import Image

    imageWidth, imageHeight = _normalizeSize(size)
    cx, cy = center
    color = _colorToRGBABytes(color)
    radius = max(1, float(radius))
    width = max(1, float(width))
    rayRadius = max(0.01, float(rayRadius))
    rayStrength = max(0, min(1, float(rayStrength)))
    rayContrast = max(0.01, float(rayContrast))
    rayTime = float(rayTime)
    image = Image.new("RGBA", (imageWidth, imageHeight), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(imageHeight):
        for x in range(imageWidth):
            if not _pointInExtent(x, y, extent, (imageWidth, imageHeight)):
                continue
            distance = math.hypot(x - cx, y - cy)
            amount = max(0, 1 - abs(distance - radius) / width)
            if rays:
                angle = math.atan2(y - cy, x - cx)
                wave = ((math.sin(angle * rayRadius * 12 + rayTime * math.tau) + 1) / 2) ** rayContrast
                amount *= 1 - rayStrength + rayStrength * wave
            alpha = _clampByte(color[3] * amount)
            pixels[x, y] = (
                _clampByte(color[0] * amount),
                _clampByte(color[1] * amount),
                _clampByte(color[2] * amount),
                alpha,
            )
    return image


def _starImage(size, center, color, radius, crossScale, crossAngle, crossOpacity, crossWidth, epsilon):
    from PIL import Image
    from PIL import ImageDraw
    from PIL import ImageFilter

    width, height = _normalizeSize(size)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    cx, cy = center
    color = _colorToRGBABytes(color)
    radius = float(radius)
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)
    length = radius * max(1, float(crossScale))
    crossColor = (*color[:3], _clampByte(color[3] * max(0, 2 ** float(crossOpacity))))
    for angle in (float(crossAngle), float(crossAngle) + math.pi / 2):
        dx = math.cos(angle) * length
        dy = math.sin(angle) * length
        draw.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=crossColor, width=max(1, int(round(float(crossWidth)))))
    blurRadius = max(0, radius / 12 + max(0, -float(epsilon)) * radius / 24)
    return image.filter(ImageFilter.GaussianBlur(blurRadius))


def _meshImage(size, mesh, width, color):
    from PIL import Image
    from PIL import ImageDraw

    imageWidth, imageHeight = _normalizeSize(size)
    image = Image.new("RGBA", (imageWidth, imageHeight), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    color = _colorToRGBABytes(color)
    width = max(1, int(round(float(width))))
    for segment in mesh:
        if len(segment) == 2:
            (x1, y1), (x2, y2) = segment
        else:
            x1, y1, x2, y2 = segment
        draw.line((x1, y1, x2, y2), fill=color, width=width)
    return image


def _screenImage(image, center, angle, width, sharpness, mode):
    from PIL import Image

    width = max(1, float(width))
    sharpness = max(0, min(1, float(sharpness)))
    centerX, centerY = center
    angle = float(angle)
    cosAngle = math.cos(angle)
    sinAngle = math.sin(angle)
    gray = image.convert("L")
    alpha = image.getchannel("A")
    result = Image.new("RGBA", image.size)
    pixels = result.load()
    grayPixels = gray.load()
    alphaPixels = alpha.load()
    transition = max(1, 128 * (1 - sharpness))
    for y in range(image.height):
        for x in range(image.width):
            tx = x - centerX
            ty = y - centerY
            if mode == "circular":
                phase = math.hypot(tx, ty) / width
                pattern = (math.sin(phase * math.tau) + 1) * 127.5
            elif mode == "line":
                phase = (tx * cosAngle + ty * sinAngle) / width
                pattern = (math.sin(phase * math.tau) + 1) * 127.5
            else:
                rx = tx * cosAngle + ty * sinAngle
                ry = -tx * sinAngle + ty * cosAngle
                cx = (rx / width) - round(rx / width)
                cy = (ry / width) - round(ry / width)
                distance = min(1, math.hypot(cx, cy) * 2)
                pattern = (1 - distance) * 255
            threshold = 255 - grayPixels[x, y]
            value = _clampByte(255 if pattern >= threshold else 255 - min(255, transition))
            pixels[x, y] = (value, value, value, alphaPixels[x, y])
    return result


def _cmykHalftoneImage(image, center, angle, width, sharpness, GCR, UCR):
    from PIL import Image

    source = image.convert("RGBA")
    width = max(1, float(width))
    sharpness = max(0, min(1, float(sharpness)))
    gcr = max(0, min(1, float(GCR)))
    ucr = max(0, min(1, float(UCR)))
    centerX, centerY = center
    alpha = source.getchannel("A")
    result = Image.new("RGBA", source.size)
    sourcePixels = source.load()
    alphaPixels = alpha.load()
    pixels = result.load()
    channelAngles = (
        float(angle) + math.radians(15),
        float(angle) + math.radians(75),
        float(angle),
        float(angle) + math.radians(45),
    )
    transition = max(0.001, 0.5 * (1 - sharpness))
    for y in range(source.height):
        for x in range(source.width):
            r, g, b, _a = sourcePixels[x, y]
            c = 1 - r / 255
            m = 1 - g / 255
            yellow = 1 - b / 255
            gray = min(c, m, yellow)
            black = gray * gcr
            removal = gray * gcr * ucr
            c = max(0, c - removal)
            m = max(0, m - removal)
            yellow = max(0, yellow - removal)
            cInk = _dotScreenInk(x, y, centerX, centerY, width, channelAngles[0], c, transition)
            mInk = _dotScreenInk(x, y, centerX, centerY, width, channelAngles[1], m, transition)
            yInk = _dotScreenInk(x, y, centerX, centerY, width, channelAngles[2], yellow, transition)
            kInk = _dotScreenInk(x, y, centerX, centerY, width, channelAngles[3], black, transition)
            pixels[x, y] = (
                _clampByte(255 * (1 - min(1, cInk + kInk))),
                _clampByte(255 * (1 - min(1, mInk + kInk))),
                _clampByte(255 * (1 - min(1, yInk + kInk))),
                alphaPixels[x, y],
            )
    return result


def _dotScreenInk(x, y, centerX, centerY, width, angle, amount, transition):
    if amount <= 0:
        return 0
    if amount >= 1:
        return 1
    tx = x - centerX
    ty = y - centerY
    cosAngle = math.cos(angle)
    sinAngle = math.sin(angle)
    rx = tx * cosAngle + ty * sinAngle
    ry = -tx * sinAngle + ty * cosAngle
    cellX = (rx / width) - round(rx / width)
    cellY = (ry / width) - round(ry / width)
    dot = max(0, 1 - math.hypot(cellX, cellY) * 2)
    return max(0, min(1, (dot - (1 - amount)) / transition + 0.5))


def _radialMask(size, center, radius, amount=1.0):
    from PIL import Image

    width, height = size
    cx, cy = center
    radius = max(1, float(radius))
    amount = max(0, float(amount))
    mask = Image.new("L", size)
    pixels = mask.load()
    for y in range(height):
        for x in range(width):
            distance = math.hypot(x - cx, y - cy)
            pixels[x, y] = _clampByte(max(0, 1 - distance / radius) * 255 * amount)
    return mask


def _bokehBlurImage(image, radius, ringAmount, ringSize, softness):
    from PIL import Image
    from PIL import ImageFilter

    radius = max(0, int(round(float(radius))))
    if radius == 0:
        return image.convert("RGBA")
    size = radius * 2 + 1
    ringAmount = max(0, float(ringAmount))
    ringSize = max(0, min(1, float(ringSize)))
    softness = max(0, min(1, float(softness)))
    weights = []
    for y in range(size):
        for x in range(size):
            distance = math.hypot(x - radius, y - radius) / radius
            if distance > 1:
                weight = 0.0
            elif softness:
                edgeStart = max(0, 1 - softness)
                weight = 1.0 if distance <= edgeStart else max(0, (1 - distance) / max(0.0001, softness))
            else:
                weight = 1.0
            if weight and ringAmount:
                ringDistance = abs(distance - ringSize)
                ringWidth = max(0.05, 0.2 * (1 - softness) + 0.05)
                ring = max(0, 1 - ringDistance / ringWidth)
                weight *= 1 + ring * ringAmount
            weights.append(weight)
    total = sum(weights) or 1
    kernel = ImageFilter.Kernel((size, size), [weight / total for weight in weights], scale=1)
    source = image.convert("RGBA")
    channels = [channel.filter(kernel) for channel in source.split()]
    return Image.merge("RGBA", channels)


def _discBlurImage(image, radius):
    from PIL import Image

    source = image.convert("RGBA")
    radius = max(0, int(round(float(radius))))
    if radius == 0:
        return source
    offsets = [
        (x, y)
        for y in range(-radius, radius + 1)
        for x in range(-radius, radius + 1)
        if x * x + y * y <= radius * radius
    ]
    sampleCount = len(offsets) or 1
    sourcePixels = source.load()
    result = Image.new("RGBA", source.size)
    resultPixels = result.load()
    for y in range(source.height):
        for x in range(source.width):
            totals = [0, 0, 0, 0]
            for offsetX, offsetY in offsets:
                sampleX = max(0, min(source.width - 1, x + offsetX))
                sampleY = max(0, min(source.height - 1, y + offsetY))
                pixel = sourcePixels[sampleX, sampleY]
                for channel in range(4):
                    totals[channel] += pixel[channel]
            resultPixels[x, y] = tuple(_clampByte(total / sampleCount) for total in totals)
    return result


def _maskedVariableBlurImage(image, mask, radius):
    from PIL import Image
    from PIL import ImageFilter

    source = image.convert("RGBA")
    maskImage = mask.resize(source.size).convert("L")
    radius = max(0, float(radius))
    if radius == 0:
        return source
    levels = 8
    blurredLevels = [
        source if level == 0 else source.filter(ImageFilter.GaussianBlur(radius * level / levels))
        for level in range(levels + 1)
    ]
    maskPixels = maskImage.load()
    levelPixels = [blurred.load() for blurred in blurredLevels]
    result = Image.new("RGBA", source.size)
    resultPixels = result.load()
    for y in range(source.height):
        for x in range(source.width):
            position = maskPixels[x, y] / 255 * levels
            lower = int(math.floor(position))
            upper = min(levels, lower + 1)
            amount = position - lower
            if amount <= 0:
                resultPixels[x, y] = levelPixels[lower][x, y]
            else:
                a = levelPixels[lower][x, y]
                b = levelPixels[upper][x, y]
                resultPixels[x, y] = tuple(_clampByte(a[index] * (1 - amount) + b[index] * amount) for index in range(4))
    return result


def _edgePreserveUpsampleImage(image, smallImage, spatialSigma=3.0, lumaSigma=0.15):
    from PIL import Image
    from PIL import ImageFilter
    from PIL import ImageOps

    source = image.convert("RGBA")
    upsampled = smallImage.convert("RGBA").resize(source.size, Image.Resampling.BICUBIC)
    radius = max(0, float(spatialSigma))
    if not radius:
        return upsampled
    smoothed = upsampled.filter(ImageFilter.GaussianBlur(radius))
    guide = ImageOps.autocontrast(source.convert("L").filter(ImageFilter.FIND_EDGES))
    guidePixels = list(_getImageData(guide))
    upsampledPixels = list(_getImageData(upsampled))
    smoothedPixels = list(_getImageData(smoothed))
    threshold = max(1, min(255, int(round(float(lumaSigma) * 255))))
    data = []
    for edge, detail, smooth in zip(guidePixels, upsampledPixels, smoothedPixels):
        detailAmount = max(0, min(1, edge / threshold))
        data.append(_mixRGBABytes(smooth, detail, detailAmount))
    return _newRGBAWithData(source.size, data)


def _guidedFilterImage(image, guide, radius, epsilon):
    from PIL import Image
    from PIL import ImageFilter

    source = image.convert("RGBA")
    radius = max(0, float(radius))
    if radius == 0:
        return source
    guideImage = source if guide is None else guide.resize(source.size).convert("RGBA")
    smoothed = source.filter(ImageFilter.GaussianBlur(radius))
    edges = guideImage.convert("L").filter(ImageFilter.FIND_EDGES)
    epsilon = max(0.000001, float(epsilon))
    edgeScale = max(1, epsilon * 255)
    sourcePixels = source.load()
    smoothPixels = smoothed.load()
    edgePixels = edges.load()
    result = Image.new("RGBA", source.size)
    resultPixels = result.load()
    for y in range(source.height):
        for x in range(source.width):
            preserve = edgePixels[x, y] / (edgePixels[x, y] + edgeScale)
            original = sourcePixels[x, y]
            smooth = smoothPixels[x, y]
            resultPixels[x, y] = tuple(
                _clampByte(smooth[index] * (1 - preserve) + original[index] * preserve)
                for index in range(4)
            )
    return result


def _depthOfFieldImage(image, point0, point1, saturation, unsharpMaskRadius, unsharpMaskIntensity, radius):
    from PIL import Image
    from PIL import ImageEnhance
    from PIL import ImageFilter

    source = image.convert("RGBA")
    radius = max(0, float(radius))
    if radius == 0:
        focused = source
    else:
        blurred = source.filter(ImageFilter.GaussianBlur(radius))
        mask = Image.new("L", source.size, 0)
        maskPixels = mask.load()
        focusWidth = max(1, radius)
        falloff = max(1, radius * 2)
        for y in range(source.height):
            for x in range(source.width):
                distance = _distanceToSegment(x, y, point0, point1)
                amount = max(0, min(1, (distance - focusWidth) / falloff))
                maskPixels[x, y] = _clampByte(amount * 255)
        focused = Image.composite(blurred, source, mask)
    focused = ImageEnhance.Color(focused).enhance(float(saturation))
    return focused.filter(
        ImageFilter.UnsharpMask(
            radius=max(0, float(unsharpMaskRadius)),
            percent=max(0, int(float(unsharpMaskIntensity) * 250)),
        )
    )


def _distanceToSegment(x, y, point0, point1):
    x0, y0 = point0
    x1, y1 = point1
    dx = x1 - x0
    dy = y1 - y0
    lengthSquared = dx * dx + dy * dy
    if lengthSquared == 0:
        return math.hypot(x - x0, y - y0)
    t = max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / lengthSquared))
    closestX = x0 + t * dx
    closestY = y0 + t * dy
    return math.hypot(x - closestX, y - closestY)


def _shadedMaterialImage(image, shadingImage, scale):
    from PIL import Image

    source = image.convert("RGBA")
    shading = shadingImage.resize(source.size).convert("L")
    scale = float(scale)
    sourcePixels = source.load()
    shadingPixels = shading.load()
    result = Image.new("RGBA", source.size)
    resultPixels = result.load()
    lightX, lightY, lightZ = -0.45, -0.45, 1.0
    lightLength = math.sqrt(lightX * lightX + lightY * lightY + lightZ * lightZ)
    lightX /= lightLength
    lightY /= lightLength
    lightZ /= lightLength
    strength = max(0, scale) / 10
    for y in range(source.height):
        y0 = max(0, y - 1)
        y1 = min(source.height - 1, y + 1)
        for x in range(source.width):
            x0 = max(0, x - 1)
            x1 = min(source.width - 1, x + 1)
            dx = (shadingPixels[x1, y] - shadingPixels[x0, y]) / 255 * strength
            dy = (shadingPixels[x, y1] - shadingPixels[x, y0]) / 255 * strength
            normalX = -dx
            normalY = -dy
            normalZ = 1.0
            normalLength = math.sqrt(normalX * normalX + normalY * normalY + normalZ * normalZ) or 1
            normalX /= normalLength
            normalY /= normalLength
            normalZ /= normalLength
            diffuse = max(0, normalX * lightX + normalY * lightY + normalZ * lightZ)
            ambient = 0.35
            factor = ambient + diffuse * (1 - ambient)
            red, green, blue, alpha = sourcePixels[x, y]
            resultPixels[x, y] = (
                _clampByte(red * factor),
                _clampByte(green * factor),
                _clampByte(blue * factor),
                alpha,
            )
    return result


def _spotLightImage(image, lightPosition, lightPointsAt, brightness, concentration, color):
    from PIL import Image

    source = image.convert("RGBA")
    lightX, lightY, lightZ = _point3D(lightPosition)
    targetX, targetY, _targetZ = _point3D(lightPointsAt)
    maxDimension = max(source.size)
    concentration = float(concentration)
    radius = abs(concentration)
    if radius <= 1:
        radius = maxDimension * (0.1 + radius * 0.9)
    radius = max(1, radius)
    heightScale = 1 + min(2, abs(lightZ) / max(1, maxDimension))
    directionX = targetX - lightX
    directionY = targetY - lightY
    directionLength = math.hypot(directionX, directionY) or 1
    axisX = directionX / directionLength
    axisY = directionY / directionLength
    brightness = max(0, float(brightness))
    tint = _colorToRGBABytes(color)
    sourcePixels = source.load()
    result = Image.new("RGBA", source.size, (0, 0, 0, 0))
    resultPixels = result.load()
    for y in range(source.height):
        for x in range(source.width):
            dx = x - targetX
            dy = y - targetY
            along = dx * axisX + dy * axisY
            across = -dx * axisY + dy * axisX
            distance = math.hypot(across / 0.75, along / heightScale)
            amount = max(0, 1 - distance / radius) ** 2
            if amount <= 0:
                continue
            red, green, blue, alpha = sourcePixels[x, y]
            lightAmount = min(1, amount * brightness)
            resultPixels[x, y] = (
                _clampByte(red + tint[0] * lightAmount),
                _clampByte(green + tint[1] * lightAmount),
                _clampByte(blue + tint[2] * lightAmount),
                _clampByte(alpha * min(1, amount * max(1, brightness))),
            )
    return result


def _point3D(point):
    values = tuple(point)
    if len(values) == 2:
        return float(values[0]), float(values[1]), 0.0
    return float(values[0]), float(values[1]), float(values[2])


def _radialTransitionMask(size, center, radius, extent=None):
    from PIL import Image

    width, height = size
    cx, cy = center
    radius = max(1, float(radius))
    mask = Image.new("L", size)
    pixels = mask.load()
    for y in range(height):
        for x in range(width):
            if not _pointInExtent(x, y, extent, size):
                pixels[x, y] = 0
                continue
            distance = math.hypot(x - cx, y - cy)
            pixels[x, y] = _clampByte((1 - distance / radius) * 255)
    return mask


def _modTransitionMask(size, center, time, angle, radius, compression):
    from PIL import Image

    width, height = size
    cx, cy = center
    time = max(0, min(1, float(time)))
    radius = max(1, float(radius))
    compression = max(1, float(compression))
    angle = float(angle)
    cosAngle = math.cos(angle)
    sinAngle = math.sin(angle)
    reach = radius * (0.25 + time)
    mask = Image.new("L", size)
    pixels = mask.load()
    for y in range(height):
        for x in range(width):
            dx = x - cx
            dy = y - cy
            distance = math.hypot(dx, dy)
            if distance > reach:
                pixels[x, y] = 0
                continue
            rotated = dx * cosAngle + dy * sinAngle
            wave = (math.sin((rotated / compression + time) * math.tau) + 1) / 2
            radial = max(0, 1 - distance / reach)
            pixels[x, y] = _clampByte(radial * (0.35 + 0.65 * wave) * 255)
    return mask


def _accordionFoldTransitionImage(source, target, bottomHeight, numberOfFolds, foldShadowAmount, time):
    source = source.convert("RGBA")
    target = target.convert("RGBA").resize(source.size)
    width, height = source.size
    bottomHeight = max(0, min(height, int(round(float(bottomHeight)))))
    folds = max(1, int(round(float(numberOfFolds))))
    foldWidth = max(1, width / folds)
    foldShadowAmount = max(0, min(1, float(foldShadowAmount)))
    time = max(0, min(1, float(time)))
    reveal = width * time
    result = source.copy()
    sourcePixels = source.load()
    targetPixels = target.load()
    resultPixels = result.load()
    for y in range(height):
        if bottomHeight and y >= height - bottomHeight:
            continue
        for x in range(width):
            foldIndex = min(folds - 1, int(x / foldWidth))
            foldStart = foldIndex * foldWidth
            foldPhase = (x - foldStart) / foldWidth
            foldProgress = max(0, min(1, (reveal - foldStart) / foldWidth))
            if foldPhase <= foldProgress:
                pixel = targetPixels[x, y]
            else:
                pixel = sourcePixels[x, y]
            shade = 1 - foldShadowAmount * (0.25 + 0.75 * abs(0.5 - foldPhase) * 2) * (foldIndex % 2)
            resultPixels[x, y] = (
                _clampByte(pixel[0] * shade),
                _clampByte(pixel[1] * shade),
                _clampByte(pixel[2] * shade),
                pixel[3],
            )
    return result


def _pageCurlTransitionImage(
    source,
    target,
    backside,
    shading,
    extent,
    time,
    angle,
    radius,
    shadowSize=0.0,
    shadowAmount=0.0,
    shadowExtent=None,
):
    from PIL import ImageFilter

    size = source.size
    radius = max(1, float(radius))
    transitionMask = _linearTransitionMask(size, time, angle, radius, extent)
    curlMask = _linearTransitionBandMask(size, time, angle, radius, extent)
    result = _blendWithMask(source, target, transitionMask)
    backside = backside.convert("RGBA")
    if shading is not None:
        shade = shading.resize(size).convert("L")
        shadedData = []
        for pixel, shadeValue in zip(_getImageData(backside), _getImageData(shade)):
            factor = 0.55 + 0.45 * (shadeValue / 255)
            shadedData.append((
                _clampByte(pixel[0] * factor),
                _clampByte(pixel[1] * factor),
                _clampByte(pixel[2] * factor),
                pixel[3],
            ))
        backside = _newRGBAWithData(size, shadedData)
    if shadowAmount:
        shadow = curlMask.filter(ImageFilter.GaussianBlur(max(0, float(shadowSize) * radius))).point(
            lambda value: _clampByte(value * float(shadowAmount))
        )
        if shadowExtent is not None:
            clipped = _extentMask(size, shadowExtent)
            shadow = _multiplyMask(shadow, clipped)
        result = _blendWithMask(result, _solidFromColor((0, 0, 0, 255), size), shadow)
    return _blendWithMask(result, backside, curlMask)


def _rippleDistortImage(image, shading, center, width, scale, time):
    shading = shading.resize(image.size).convert("L")
    shadingPixels = shading.load()
    cx, cy = center
    width = max(1, float(width))
    scale = float(scale)
    time = max(0, min(1, float(time)))

    def mapPoint(x, y):
        dx = x - cx
        dy = y - cy
        distance = math.hypot(dx, dy)
        if distance == 0:
            return x, y
        phase = distance / width - time * 4
        wave = math.sin(phase * math.tau)
        shadingAmount = (shadingPixels[x, y] - 128) / 128
        amount = wave * shadingAmount * scale * 0.1
        return x - dx / distance * amount, y - dy / distance * amount

    return _distortImage(image, mapPoint)


def _linearTransitionMask(size, time, angle, width, extent=None):
    from PIL import Image

    imageWidth, imageHeight = size
    time = max(0, min(1, float(time)))
    width = max(1, float(width))
    angle = float(angle)
    dx = math.cos(angle)
    dy = math.sin(angle)
    fullExtent = abs(dx) * imageWidth + abs(dy) * imageHeight
    edge = -fullExtent / 2 + fullExtent * time
    mask = Image.new("L", size)
    pixels = mask.load()
    cx = imageWidth / 2
    cy = imageHeight / 2
    for y in range(imageHeight):
        for x in range(imageWidth):
            projection = (x - cx) * dx + (y - cy) * dy
            value = _clampByte((edge - projection + width / 2) / width * 255)
            pixels[x, y] = value if _pointInExtent(x, y, extent, size) else 0
    return mask


def _linearTransitionBandMask(size, time, angle, width, extent=None):
    from PIL import Image

    imageWidth, imageHeight = size
    time = max(0, min(1, float(time)))
    width = max(1, float(width))
    angle = float(angle)
    dx = math.cos(angle)
    dy = math.sin(angle)
    fullExtent = abs(dx) * imageWidth + abs(dy) * imageHeight
    edge = -fullExtent / 2 + fullExtent * time
    mask = Image.new("L", size)
    pixels = mask.load()
    cx = imageWidth / 2
    cy = imageHeight / 2
    halfWidth = width / 2
    for y in range(imageHeight):
        for x in range(imageWidth):
            if not _pointInExtent(x, y, extent, size):
                pixels[x, y] = 0
                continue
            projection = (x - cx) * dx + (y - cy) * dy
            pixels[x, y] = _clampByte(max(0, 1 - abs(projection - edge) / halfWidth) * 255)
    return mask


def _disintegrateMasks(maskSource, time, shadowRadius, shadowDensity, shadowOffset):
    from PIL import Image
    from PIL import ImageChops
    from PIL import ImageFilter

    time = max(0, min(1, float(time)))
    transitionWidth = 0.12
    low = max(0, time - transitionWidth / 2)
    high = min(1, time + transitionWidth / 2)
    span = high - low or 1
    mask = maskSource.point(lambda value: _clampByte((time - value / 255 + transitionWidth / 2) / span * 255))
    radius = max(0, float(shadowRadius))
    density = max(0, min(1, float(shadowDensity)))
    if radius == 0 or density == 0:
        return mask, None
    edge = ImageChops.difference(mask, mask.filter(ImageFilter.MinFilter(3)))
    shadow = edge.filter(ImageFilter.GaussianBlur(radius)).point(lambda value: _clampByte(value * density))
    offsetX, offsetY = shadowOffset
    shifted = Image.new("L", maskSource.size, 0)
    shifted.paste(shadow, (int(round(float(offsetX))), int(round(float(offsetY)))))
    return mask, shifted


def _pointInExtent(x, y, extent, size):
    if extent is None:
        return True
    ex, ey, ew, eh = extent
    if ew <= 0 or eh <= 0:
        return True
    imageWidth, imageHeight = size
    # Core Image extents are image-space rectangles. Clamp generously so the
    # default DrawBot/Core Image extent still covers small test images.
    left = max(0, float(ex))
    top = max(0, float(ey))
    right = min(imageWidth, left + float(ew))
    bottom = min(imageHeight, top + float(eh))
    return left <= x < right and top <= y < bottom


def _extentMask(size, extent, value=255):
    from PIL import Image

    mask = Image.new("L", size, 0)
    pixels = mask.load()
    width, height = size
    value = _clampByte(value)
    for y in range(height):
        for x in range(width):
            pixels[x, y] = value if _pointInExtent(x, y, extent, size) else 0
    return mask


def _multiplyMask(mask1, mask2):
    from PIL import ImageChops

    return ImageChops.multiply(mask1, mask2)


def _barsTransitionMask(size, time, angle, width, barOffset):
    from PIL import Image

    imageWidth, imageHeight = size
    time = max(0, min(1, float(time)))
    width = max(1, float(width))
    barOffset = float(barOffset)
    angle = float(angle)
    dx = math.cos(angle)
    dy = math.sin(angle)
    mask = Image.new("L", size)
    pixels = mask.load()
    for y in range(imageHeight):
        for x in range(imageWidth):
            projection = x * dx + y * dy + barOffset
            phase = (projection % (width * 2)) / (width * 2)
            pixels[x, y] = 255 if phase < time else 0
    return mask


def _blendWithMask(image1, image2, mask):
    from PIL import Image

    return Image.composite(image2.convert("RGBA"), image1.convert("RGBA"), mask)


def _samplePixel(pixels, width, height, x, y):
    x = max(0, min(width - 1, int(round(x))))
    y = max(0, min(height - 1, int(round(y))))
    return pixels[x, y]


def _affineTileImage(image, transform):
    from PIL import Image

    xx, xy, yx, yy, dx, dy = (float(value) for value in transform)
    source = image.convert("RGBA")
    sourcePixels = source.load()
    result = Image.new("RGBA", source.size, (0, 0, 0, 0))
    resultPixels = result.load()
    width, height = source.size
    for y in range(height):
        for x in range(width):
            sampleX = (xx * x + yx * y + dx) % width
            sampleY = (xy * x + yy * y + dy) % height
            resultPixels[x, y] = _samplePixel(sourcePixels, width, height, sampleX, sampleY)
    return result


def _distortImage(image, mapPoint):
    from PIL import Image

    source = image.convert("RGBA")
    result = Image.new("RGBA", source.size, (0, 0, 0, 0))
    sourcePixels = source.load()
    resultPixels = result.load()
    for y in range(source.height):
        for x in range(source.width):
            sx, sy = mapPoint(x, y)
            resultPixels[x, y] = _samplePixel(sourcePixels, source.width, source.height, sx, sy)
    return result


def _radialDistortImage(image, center, radius, scale, mode):
    cx, cy = center
    radius = max(1, float(radius))
    scale = float(scale)

    def mapPoint(x, y):
        dx = x - cx
        dy = y - cy
        distance = math.hypot(dx, dy)
        if distance <= 0 or distance >= radius:
            return x, y
        amount = (1 - distance / radius) ** 2
        if mode == "bump":
            factor = 1 - scale * amount
        elif mode == "splash":
            factor = 1 + scale * math.sin((1 - distance / radius) * math.pi) * 0.35
        else:
            factor = 1 + scale * amount
        return cx + dx * factor, cy + dy * factor

    return _distortImage(image, mapPoint)


def _linearBumpImage(image, center, radius, angle, scale):
    cx, cy = center
    radius = max(1, float(radius))
    scale = float(scale)
    angle = float(angle)
    normalX = -math.sin(angle)
    normalY = math.cos(angle)

    def mapPoint(x, y):
        distance = (x - cx) * normalX + (y - cy) * normalY
        absolute = abs(distance)
        if absolute >= radius:
            return x, y
        amount = (1 - absolute / radius) ** 2 * scale * radius * 0.25
        sign = 1 if distance >= 0 else -1
        return x - normalX * amount * sign, y - normalY * amount * sign

    return _distortImage(image, mapPoint)


def _twirlImage(image, center, radius, angle):
    cx, cy = center
    radius = max(1, float(radius))
    angle = float(angle)

    def mapPoint(x, y):
        dx = x - cx
        dy = y - cy
        distance = math.hypot(dx, dy)
        if distance >= radius or distance == 0:
            return x, y
        theta = math.atan2(dy, dx) - angle * ((radius - distance) / radius) ** 2
        return cx + math.cos(theta) * distance, cy + math.sin(theta) * distance

    return _distortImage(image, mapPoint)


def _displacementImage(image, displacement, scale):
    displacement = displacement.resize(image.size).convert("RGBA")
    displacementPixels = displacement.load()
    scale = float(scale)

    def mapPoint(x, y):
        red, green, _blue, _alpha = displacementPixels[x, y]
        dx = (red - 128) / 128 * scale
        dy = (green - 128) / 128 * scale
        return x + dx, y + dy

    return _distortImage(image, mapPoint)


def _glassDistortionImage(image, texture, center, scale):
    texture = texture.convert("RGBA")
    texturePixels = texture.load()
    textureWidth, textureHeight = texture.size
    centerX, centerY = (float(value) for value in center)
    textureCenterX = textureWidth / 2
    textureCenterY = textureHeight / 2
    scale = float(scale)

    def mapPoint(x, y):
        tx = int(math.floor(x - centerX + textureCenterX)) % textureWidth
        ty = int(math.floor(y - centerY + textureCenterY)) % textureHeight
        red, green, _blue, _alpha = texturePixels[tx, ty]
        dx = (red - 128) / 128 * scale
        dy = (green - 128) / 128 * scale
        return x + dx, y + dy

    return _distortImage(image, mapPoint)


def _pixellateImage(image, center, scale):
    from PIL import Image
    from PIL import ImageStat

    source = image.convert("RGBA")
    result = Image.new("RGBA", source.size, (0, 0, 0, 0))
    pixels = result.load()
    width, height = source.size
    centerX, centerY = (float(value) for value in center)
    scale = max(1, int(round(float(scale))))
    blockCache = {}
    for y in range(height):
        for x in range(width):
            blockX = math.floor((x - centerX) / scale)
            blockY = math.floor((y - centerY) / scale)
            key = (blockX, blockY)
            color = blockCache.get(key)
            if color is None:
                left = max(0, int(math.floor(centerX + blockX * scale)))
                top = max(0, int(math.floor(centerY + blockY * scale)))
                right = min(width, int(math.floor(centerX + (blockX + 1) * scale)))
                bottom = min(height, int(math.floor(centerY + (blockY + 1) * scale)))
                if right <= left:
                    right = min(width, left + 1)
                if bottom <= top:
                    bottom = min(height, top + 1)
                color = tuple(_clampByte(value) for value in ImageStat.Stat(source.crop((left, top, right, bottom))).mean)
                blockCache[key] = color
            pixels[x, y] = color
    return result


def _motionBlurImage(image, radius, angle):
    from PIL import Image

    source = image.convert("RGBA")
    radius = max(0, int(round(float(radius))))
    if radius == 0:
        return source
    angle = float(angle)
    dx = math.cos(angle)
    dy = math.sin(angle)
    offsets = sorted(
        {
            (int(round(index * dx)), int(round(index * dy)))
            for index in range(-radius, radius + 1)
        }
    )
    sampleCount = len(offsets)
    sourcePixels = source.load()
    result = Image.new("RGBA", source.size)
    resultPixels = result.load()
    for y in range(source.height):
        for x in range(source.width):
            totals = [0, 0, 0, 0]
            for offsetX, offsetY in offsets:
                sampleX = max(0, min(source.width - 1, x + offsetX))
                sampleY = max(0, min(source.height - 1, y + offsetY))
                pixel = sourcePixels[sampleX, sampleY]
                for channel in range(4):
                    totals[channel] += pixel[channel]
            resultPixels[x, y] = tuple(_clampByte(total / sampleCount) for total in totals)
    return result


def _cannyEdgeImage(image, gaussianSigma, perceptual, thresholdHigh, thresholdLow, hysteresisPasses):
    from PIL import Image
    from PIL import ImageFilter

    if perceptual:
        gray = Image.new("L", image.size)
        gray.putdata([_clampByte(_rgbBytesToLab(*pixel[:3])[0] / 100 * 255) for pixel in _getImageData(image)])
    else:
        gray = image.convert("L")
    sigma = max(0, float(gaussianSigma))
    if sigma:
        gray = gray.filter(ImageFilter.GaussianBlur(sigma))
    edge = gray.filter(ImageFilter.FIND_EDGES)
    high = _clampByte(float(thresholdHigh) * 255)
    low = min(high, _clampByte(float(thresholdLow) * 255))
    width, height = image.size
    edgePixels = edge.load()
    strong = set()
    weak = set()
    for y in range(height):
        for x in range(width):
            value = edgePixels[x, y]
            if value >= high:
                strong.add((x, y))
            elif value >= low:
                weak.add((x, y))
    connected = set(strong)
    frontier = set(strong)
    for _ in range(max(0, int(round(float(hysteresisPasses))))):
        nextFrontier = set()
        for x, y in frontier:
            for neighborY in range(max(0, y - 1), min(height, y + 2)):
                for neighborX in range(max(0, x - 1), min(width, x + 2)):
                    point = (neighborX, neighborY)
                    if point in weak and point not in connected:
                        connected.add(point)
                        nextFrontier.add(point)
        frontier = nextFrontier
        if not frontier:
            break
    result = Image.new("L", image.size, 0)
    resultPixels = result.load()
    for x, y in connected:
        resultPixels[x, y] = 255
    return result


def _lozengeDistortImage(image, point0, point1, radius, refraction):
    x0, y0 = point0
    x1, y1 = point1
    radius = max(1, float(radius))
    refraction = float(refraction)
    lengthSquared = (x1 - x0) ** 2 + (y1 - y0) ** 2 or 1

    def mapPoint(x, y):
        t = max(0, min(1, ((x - x0) * (x1 - x0) + (y - y0) * (y1 - y0)) / lengthSquared))
        cx = x0 + (x1 - x0) * t
        cy = y0 + (y1 - y0) * t
        dx = x - cx
        dy = y - cy
        distance = math.hypot(dx, dy)
        if distance <= 0 or distance > radius:
            return x, y
        factor = 1 - (refraction - 1) * (1 - distance / radius) * 0.2
        return cx + dx * factor, cy + dy * factor

    return _distortImage(image, mapPoint)


def _torusDistortImage(image, center, radius, width, refraction):
    cx, cy = center
    radius = max(1, float(radius))
    halfWidth = max(1, float(width) / 2)
    refraction = float(refraction)

    def mapPoint(x, y):
        dx = x - cx
        dy = y - cy
        distance = math.hypot(dx, dy)
        delta = abs(distance - radius)
        if distance <= 0 or delta > halfWidth:
            return x, y
        amount = (1 - delta / halfWidth) * (refraction - 1) * 0.25
        factor = 1 - amount
        return cx + dx * factor, cy + dy * factor

    return _distortImage(image, mapPoint)


def _drosteImage(image, insetPoint0, insetPoint1, strands, periodicity, rotation, zoom):
    from PIL import Image

    source = image.convert("RGBA")
    result = source.copy()
    x0, y0 = insetPoint0
    x1, y1 = insetPoint1
    left = max(0, min(source.width - 1, int(round(min(x0, x1)))))
    top = max(0, min(source.height - 1, int(round(min(y0, y1)))))
    right = max(left + 1, min(source.width, int(round(max(x0, x1)))))
    bottom = max(top + 1, min(source.height, int(round(max(y0, y1)))))
    baseWidth = right - left
    baseHeight = bottom - top
    strandCount = max(1, int(round(abs(float(strands)))))
    iterations = max(1, int(round(abs(float(periodicity)) * 3)))
    zoom = abs(float(zoom)) or 1.0
    rotation = float(rotation)
    if abs(rotation) <= math.tau:
        rotation = math.degrees(rotation)
    for index in range(iterations):
        shrink = zoom ** index / (index + 1)
        targetWidth = max(1, int(round(baseWidth * shrink)))
        targetHeight = max(1, int(round(baseHeight * shrink)))
        targetLeft = left + (baseWidth - targetWidth) // 2
        targetTop = top + (baseHeight - targetHeight) // 2
        for strand in range(strandCount):
            angle = rotation * (index + 1) + (360 * strand / strandCount if strandCount > 1 else 0)
            inset = source.resize((targetWidth, targetHeight), Image.Resampling.BICUBIC)
            if angle:
                inset = inset.rotate(angle, resample=Image.Resampling.BICUBIC)
            if strandCount > 1:
                offset = min(targetWidth, targetHeight) * 0.15
                radians = math.tau * strand / strandCount
                pasteLeft = int(round(targetLeft + math.cos(radians) * offset))
                pasteTop = int(round(targetTop + math.sin(radians) * offset))
            else:
                pasteLeft = targetLeft
                pasteTop = targetTop
            result.alpha_composite(inset, (pasteLeft, pasteTop))
    return result


def _perspectiveRotateImage(image, focalLength, pitch, yaw, roll):
    width, height = image.size
    halfWidth = width / 2
    halfHeight = height / 2
    focal = max(1, float(focalLength)) / 35 * max(width, height)
    pitch = float(pitch)
    yaw = float(yaw)
    roll = float(roll)
    if pitch == 0 and yaw == 0 and roll == 0:
        return image.convert("RGBA")
    cosPitch = math.cos(pitch)
    sinPitch = math.sin(pitch)
    cosYaw = math.cos(yaw)
    sinYaw = math.sin(yaw)
    cosRoll = math.cos(roll)
    sinRoll = math.sin(roll)

    def project(point):
        x, y = point
        z = 0
        y, z = y * cosPitch - z * sinPitch, y * sinPitch + z * cosPitch
        x, z = x * cosYaw + z * sinYaw, -x * sinYaw + z * cosYaw
        x, y = x * cosRoll - y * sinRoll, x * sinRoll + y * cosRoll
        factor = focal / max(1, focal + z)
        return halfWidth + x * factor, halfHeight + y * factor

    corners = [
        project((-halfWidth, -halfHeight)),
        project((halfWidth, -halfHeight)),
        project((halfWidth, halfHeight)),
        project((-halfWidth, halfHeight)),
    ]
    return _quadTransformImage(image, *corners)


def _lightTunnelImage(image, center, rotation, radius):
    cx, cy = center
    radius = max(1, float(radius))
    rotation = float(rotation)

    def mapPoint(x, y):
        dx = x - cx
        dy = y - cy
        distance = math.hypot(dx, dy)
        if distance >= radius or distance == 0:
            return x, y
        amount = 1 - distance / radius
        theta = math.atan2(dy, dx) + rotation + amount * math.tau
        tunnelDistance = distance * (0.45 + 0.55 * amount)
        return cx + math.cos(theta) * tunnelDistance, cy + math.sin(theta) * tunnelDistance

    return _distortImage(image, mapPoint)


def _ninePartImage(image, breakpoint0, breakpoint1, growAmount, tiled=False, flipYTiles=True):
    from PIL import Image

    source = image.convert("RGBA")
    x0, y0 = breakpoint0
    x1, y1 = breakpoint1
    left = max(0, min(source.width, int(round(min(x0, x1)))))
    right = max(left, min(source.width, int(round(max(x0, x1)))))
    top = max(0, min(source.height, int(round(min(y0, y1)))))
    bottom = max(top, min(source.height, int(round(max(y0, y1)))))
    growX, growY = growAmount
    targetWidth = max(1, int(round(source.width + float(growX))))
    targetHeight = max(1, int(round(source.height + float(growY))))
    targetLeft = min(left, targetWidth)
    targetRightWidth = min(source.width - right, max(0, targetWidth - targetLeft))
    targetCenterWidth = max(0, targetWidth - targetLeft - targetRightWidth)
    targetTop = min(top, targetHeight)
    targetBottomHeight = min(source.height - bottom, max(0, targetHeight - targetTop))
    targetCenterHeight = max(0, targetHeight - targetTop - targetBottomHeight)
    sourceXs = (0, left, right, source.width)
    sourceYs = (0, top, bottom, source.height)
    targetXs = (0, targetLeft, targetLeft + targetCenterWidth, targetWidth)
    targetYs = (0, targetTop, targetTop + targetCenterHeight, targetHeight)
    result = Image.new("RGBA", (targetWidth, targetHeight), (0, 0, 0, 0))
    for row in range(3):
        for column in range(3):
            box = (sourceXs[column], sourceYs[row], sourceXs[column + 1], sourceYs[row + 1])
            patch = source.crop(box)
            targetBox = (targetXs[column], targetYs[row], targetXs[column + 1], targetYs[row + 1])
            targetPatchWidth = targetBox[2] - targetBox[0]
            targetPatchHeight = targetBox[3] - targetBox[1]
            if patch.width <= 0 or patch.height <= 0 or targetPatchWidth <= 0 or targetPatchHeight <= 0:
                continue
            if tiled and (row == 1 or column == 1):
                patch = _tilePatch(patch, targetPatchWidth, targetPatchHeight, flipY=flipYTiles and row == 1)
            elif patch.size != (targetPatchWidth, targetPatchHeight):
                patch = patch.resize((targetPatchWidth, targetPatchHeight), Image.Resampling.BICUBIC)
            result.alpha_composite(patch, (targetBox[0], targetBox[1]))
    return result


def _tilePatch(patch, width, height, flipY=False):
    from PIL import Image

    result = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    patch = patch.convert("RGBA")
    for y in range(0, height, patch.height):
        rowIndex = y // patch.height
        rowPatch = patch.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if flipY and rowIndex % 2 else patch
        for x in range(0, width, patch.width):
            tile = rowPatch.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flipY and (x // patch.width) % 2 else rowPatch
            tile = tile.crop((0, 0, min(tile.width, width - x), min(tile.height, height - y)))
            result.alpha_composite(tile, (x, y))
    return result


def _quadTransformImage(image, topLeft, topRight, bottomRight, bottomLeft, resizeToSource=True):
    from PIL import Image

    width, height = image.size
    xs = [point[0] for point in (topLeft, topRight, bottomRight, bottomLeft)]
    ys = [point[1] for point in (topLeft, topRight, bottomRight, bottomLeft)]
    minX = min(xs)
    minY = min(ys)
    maxX = max(xs)
    maxY = max(ys)
    targetWidth = max(1, int(round(maxX - minX)))
    targetHeight = max(1, int(round(maxY - minY)))
    data = (
        topLeft[0] - minX,
        topLeft[1] - minY,
        topRight[0] - minX,
        topRight[1] - minY,
        bottomRight[0] - minX,
        bottomRight[1] - minY,
        bottomLeft[0] - minX,
        bottomLeft[1] - minY,
    )
    transformed = image.transform((targetWidth, targetHeight), Image.Transform.QUAD, data, Image.Resampling.BICUBIC)
    if resizeToSource:
        return transformed.resize((width, height), Image.Resampling.BICUBIC)
    return transformed, (int(round(minX)), int(round(minY)))


def _keystoneCombinedImage(image, focalLength, topLeft, topRight, bottomRight, bottomLeft):
    width, height = image.size
    focal = max(1, float(focalLength))
    amount = max(0.1, min(4, 28 / focal))
    sourceCorners = (
        (0.0, 0.0),
        (float(width), 0.0),
        (float(width), float(height)),
        (0.0, float(height)),
    )
    targetCorners = (topLeft, topRight, bottomRight, bottomLeft)
    adjusted = []
    for source, target in zip(sourceCorners, targetCorners):
        tx, ty = target
        adjusted.append(
            (
                source[0] + (float(tx) - source[0]) * amount,
                source[1] + (float(ty) - source[1]) * amount,
            )
        )
    return _quadTransformImage(image, *adjusted)


def _tileImage(image, rotations=4, reflect=False, angle=0.0, center=None):
    from PIL import Image
    from PIL import ImageChops

    base = image.convert("RGBA")
    rotations = max(1, int(rotations))
    center = None if center is None else tuple(float(value) for value in center)
    angle = math.degrees(float(angle))
    result = Image.new("RGBA", base.size, (0, 0, 0, 0))
    for index in range(rotations):
        tile = base.rotate(
            angle + 360 * index / rotations,
            resample=Image.Resampling.BICUBIC,
            center=center,
        )
        if reflect and index % 2:
            tile = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        result = ImageChops.lighter(result, tile)
    return result


def _triangleKaleidoscopeImage(image, point, size, rotation, decay):
    from PIL import Image
    from PIL import ImageChops
    from PIL import ImageEnhance

    base = image.convert("RGBA")
    px, py = point
    px = float(px)
    py = float(py)
    span = max(1, int(round(float(size))))
    half = span / 2
    left = int(round(px - half))
    top = int(round(py - half))
    wedge = base.crop((left, top, left + span, top + span))
    if wedge.size != base.size:
        framed = Image.new("RGBA", base.size, (0, 0, 0, 0))
        framed.alpha_composite(wedge.resize(base.size, Image.Resampling.BICUBIC))
        wedge = framed
    decay = max(0, min(1, float(decay)))
    rotation = math.degrees(float(rotation))
    result = Image.new("RGBA", base.size, (0, 0, 0, 0))
    for index in range(3):
        tile = wedge.rotate(
            rotation + index * 120,
            resample=Image.Resampling.BICUBIC,
            center=(px, py),
        )
        if index % 2:
            tile = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if decay < 1:
            tile = ImageEnhance.Brightness(tile).enhance(decay**index)
        result = ImageChops.lighter(result, tile)
    return result


def _offsetTileImage(image, width, angle):
    from PIL import ImageChops

    width = int(round(float(width))) or 1
    angle = float(angle)
    dx = int(round(math.cos(angle) * width / 2))
    dy = int(round(math.sin(angle) * width / 2))
    shifted = ImageChops.offset(image.convert("RGBA"), dx, dy)
    return _blendRGBA(image, shifted, 0.5)


def _fourfoldTileSource(image, center, width, angle, acuteAngle):
    from PIL import ImageChops

    source = image.convert("RGBA")
    width = int(round(float(width))) or 1
    phaseX, phaseY = center
    phaseX = int(round(float(phaseX) - source.width / 2))
    phaseY = int(round(float(phaseY) - source.height / 2))
    angle0 = float(angle)
    angle1 = angle0 + float(acuteAngle)
    offsets = (
        (0, 0),
        (int(round(math.cos(angle0) * width / 2)), int(round(math.sin(angle0) * width / 2))),
        (int(round(math.cos(angle1) * width / 2)), int(round(math.sin(angle1) * width / 2))),
        (
            int(round((math.cos(angle0) + math.cos(angle1)) * width / 2)),
            int(round((math.sin(angle0) + math.sin(angle1)) * width / 2)),
        ),
    )
    shifted = [ImageChops.offset(source, dx + phaseX, dy + phaseY) for dx, dy in offsets]
    result = shifted[0]
    for tile in shifted[1:]:
        result = _blendRGBA(result, tile, 0.5)
    return result


def _skewTileImage(image, angle, acuteAngle, width):
    from PIL import Image

    shear = math.cos(float(acuteAngle)) * 0.25
    transformed = image.transform(
        image.size,
        Image.Transform.AFFINE,
        (1, shear, 0, 0, 1, 0),
        resample=Image.Resampling.BICUBIC,
    )
    return _offsetTileImage(transformed.rotate(math.degrees(float(angle)), resample=Image.Resampling.BICUBIC), width, angle)


def _cropExtent(image, extent):
    x, y, width, height = extent
    left = max(0, int(round(x)))
    top = max(0, int(round(y)))
    right = min(image.width, int(round(x + width)))
    bottom = min(image.height, int(round(y + height)))
    if right <= left or bottom <= top:
        return image.crop((0, 0, 1, 1))
    return image.crop((left, top, right, bottom))


def _solidFromColor(color, size=(1, 1)):
    from PIL import Image

    return Image.new("RGBA", size, tuple(_clampByte(value) for value in color))


def _srgbToLinearByte(value):
    value = value / 255
    if value <= 0.04045:
        linear = value / 12.92
    else:
        linear = ((value + 0.055) / 1.055) ** 2.4
    return _clampByte(linear * 255)


def _linearToSRGBByte(value):
    value = value / 255
    if value <= 0.0031308:
        srgb = value * 12.92
    else:
        srgb = 1.055 * (value ** (1 / 2.4)) - 0.055
    return _clampByte(srgb * 255)


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


def _newLWithData(size, data):
    from PIL import Image

    image = Image.new("L", size)
    image.putdata(data)
    return image


def _getImageData(image):
    if hasattr(image, "get_flattened_data"):
        return image.get_flattened_data()
    return image.getdata()


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
