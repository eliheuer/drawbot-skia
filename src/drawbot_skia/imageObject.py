import os
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
        return None

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
