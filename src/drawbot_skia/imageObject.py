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
        self._image = skia.Image.MakeFromEncoded(data.getvalue())
