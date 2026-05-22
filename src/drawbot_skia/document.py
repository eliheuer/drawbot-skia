from abc import ABC, abstractmethod
from contextlib import contextmanager
from io import BytesIO
import logging
import os
import pathlib
import tempfile
from xml.sax.saxutils import quoteattr
import skia


class Document(ABC):

    # pageWidth
    # pageHeight

    @property
    @abstractmethod
    def isDrawing(self):
        return ...

    @abstractmethod
    def beginPage(self, width: int, height: int) -> skia.Canvas:
        return ...

    @abstractmethod
    def endPage(self):
        ...

    @abstractmethod
    def endDrawing(self):
        ...

    @abstractmethod
    def setFrameDuration(self, duration):
        ...

    @abstractmethod
    def saveImage(self, path, **kwargs):
        ...


DEFAULT_FRAMEDURATION = 1 / 10


class RecordingDocument(Document):
    def __init__(self):
        self._pictures = []
        self._frameDurations = []
        self._linkAnnotations = []
        self._currentRecorder = None
        self._currentFrameDuration = DEFAULT_FRAMEDURATION
        self._currentLinkAnnotations = None
        self.pageWidth = self.pageHeight = None

    @property
    def isDrawing(self):
        return self._currentRecorder is not None

    def beginPage(self, width, height):
        assert self._currentRecorder is None
        self.pageWidth = width
        self.pageHeight = height
        self._currentRecorder = skia.PictureRecorder()
        self._currentLinkAnnotations = []
        return self._currentRecorder.beginRecording(width, height)

    def endPage(self):
        self._pictures.append(self._currentRecorder.finishRecordingAsPicture())
        self._frameDurations.append(self._currentFrameDuration)
        self._linkAnnotations.append(tuple(self._currentLinkAnnotations))
        self._currentRecorder = None
        self._currentFrameDuration = DEFAULT_FRAMEDURATION
        self._currentLinkAnnotations = None
        self.pageWidth = self.pageHeight = None

    def endDrawing(self):
        ...

    def setFrameDuration(self, duration):
        self._currentFrameDuration = duration

    def addLinkAnnotation(self, annotation):
        if self._currentLinkAnnotations is None:
            self._currentLinkAnnotations = []
        self._currentLinkAnnotations.append(annotation)

    @property
    def pageCount(self):
        return len(self._pictures) + int(self.isDrawing)

    def saveImage(self, path, **kwargs):
        path = pathlib.Path(path).resolve()
        suffix = path.suffix.lower().lstrip(".")
        methodName = f"_saveImage_{suffix}"
        method = getattr(self, methodName, None)
        if method is None:
            raise ValueError(f"unsupported file type: {suffix}")
        method(path, **kwargs)

    def _saveImage_pdf(self, path, **kwargs):
        stream = skia.FILEWStream(os.fspath(path))
        with skia.PDF.MakeDocument(stream) as document:
            for picture in self._pictures:
                x, y, width, height = picture.cullRect()
                assert x == 0 and y == 0
                with document.page(width, height) as canvas:
                    canvas.drawPicture(picture)
        stream.flush()

    def _saveImage_svg(self, path, **kwargs):
        for index, (picture, framePath) in enumerate(_iteratePictures(self._pictures, path)):
            x, y, width, height = picture.cullRect()
            assert x == 0 and y == 0
            stream = skia.FILEWStream(os.fspath(framePath))
            canvas = skia.SVGCanvas.Make((width, height), stream)
            canvas.drawPicture(picture)
            del canvas
            stream.flush()
            _appendSVGLinkAnnotations(
                framePath,
                self._linkAnnotations[index] if index < len(self._linkAnnotations) else (),
                height,
            )

    def _saveImage_png(self, path, **kwargs):
        _savePixelImages(self._pictures, path, skia.kPNG)

    def _saveImage_jpeg(self, path, **kwargs):
        _savePixelImages(self._pictures, path, skia.kJPEG, whiteBackground=True)

    _saveImage_jpg = _saveImage_jpeg

    def _saveImage_gif(self, path, loop=0, optimize=False, **kwargs):
        if not self._pictures:
            return
        frames = [_pictureToPILImage(picture) for picture in self._pictures]
        durations = [
            max(1, round(frameDuration * 1000))
            for frameDuration in self._frameDurations
        ]
        firstFrame, restFrames = frames[0], frames[1:]
        firstFrame.save(
            os.fspath(path),
            save_all=True,
            append_images=restFrames,
            duration=durations,
            loop=loop,
            optimize=optimize,
        )

    def _saveImage_mp4(self, path, codec="libx264", **kwargs):
        from .ffmpeg import generateMP4

        if not self._pictures:
            # Empty mp4?
            return
        frameRate = max(1, round(1 / self._frameDurations[-1]))
        if len(set(self._frameDurations)) != 1:
            logging.warning("ignoring varying frame durations for mp4 export")
        with tempfile.TemporaryDirectory(prefix="drawbot-skia-") as tempDir:
            tempDir = pathlib.Path(tempDir)
            imagePath = tempDir / "frame.png"
            _savePixelImages(
                self._pictures,
                imagePath,
                skia.kPNG,
                whiteBackground=True,
                singlePage=False,
            )
            imagesTemplate = tempDir / "frame_%d.png"
            generateMP4(imagesTemplate, path, frameRate, codec=codec)


def _savePixelImages(pictures, path, format, whiteBackground=False, singlePage=None):
    for picture, framePath in _iteratePictures(pictures, path, singlePage):
        _savePixelImage(picture, framePath, format, whiteBackground=whiteBackground)


def _iteratePictures(pictures, path, singlePage=None):
    if singlePage is None:
        singlePage = len(pictures) == 1
    for index, picture in enumerate(pictures):
        if singlePage:
            framePath = path
        else:
            framePath = path.parent / f"{path.stem}_{index}{path.suffix}"
        yield picture, framePath


def _savePixelImage(picture, path, format, whiteBackground=False):
    image = _pictureToSkiaImage(picture, whiteBackground=whiteBackground)
    image.save(os.fspath(path), format)


def _appendSVGLinkAnnotations(path, annotations, pageHeight):
    if not annotations:
        return
    path = pathlib.Path(path)
    svg = path.read_text(encoding="utf-8")
    marker = "</svg>"
    links = [_svgLinkAnnotation(annotation, pageHeight) for annotation in annotations]
    links = "".join(links)
    if marker in svg:
        svg = svg.replace(marker, links + marker, 1)
    elif svg.rstrip().endswith("/>"):
        trailingWhitespace = svg[len(svg.rstrip()):]
        svg = svg.rstrip()[:-2] + ">\n" + links + marker + trailingWhitespace
    else:
        return
    path.write_text(svg, encoding="utf-8")


def _svgLinkAnnotation(annotation, pageHeight):
    kind = annotation["type"]
    if kind == "destination":
        x, y = annotation["xy"]
        if x is None and y is None:
            x = annotation["width"] * 0.5
            y = annotation["height"] * 0.5
        x = max(0, min(x, annotation["width"]))
        y = max(0, min(y, annotation["height"]))
        return (
            f'<rect id={quoteattr(annotation["name"])} '
            f'x={quoteattr(_svgNumber(x))} y={quoteattr(_svgNumber(pageHeight - y))} '
            'width="1" height="1" fill="transparent"/>\n'
        )
    x, y, width, height = annotation["rect"]
    rect = (
        f'<rect x={quoteattr(_svgNumber(x))} '
        f'y={quoteattr(_svgNumber(pageHeight - y - height))} '
        f'width={quoteattr(_svgNumber(width))} height={quoteattr(_svgNumber(height))} '
        'fill="transparent"/>\n'
    )
    if kind == "url":
        href = annotation["url"]
    else:
        href = "#" + annotation["name"]
    return f'<a href={quoteattr(href)}>\n{rect}</a>\n'


def _svgNumber(value):
    return f"{value:g}"


def _pictureToSkiaImage(picture, whiteBackground=False):
    x, y, width, height = picture.cullRect()
    assert x == 0 and y == 0
    surface = skia.Surface(int(width), int(height))
    with surface as canvas:
        if whiteBackground:
            canvas.clear(skia.ColorWHITE)
        canvas.drawPicture(picture)
    return surface.makeImageSnapshot()


def _pictureToPILImage(picture):
    from PIL import Image

    data = _pictureToSkiaImage(picture).encodeToData(skia.kPNG, 100).bytes()
    return Image.open(BytesIO(data)).convert("RGBA")


class PixelDocument(Document):
    ...


class MP4Document(PixelDocument):
    ...


class PDFDocument(Document):
    def __init__(self, path):
        self._stream = skia.FILEWStream(os.fspath(path))
        self._document = skia.PDF.MakeDocument(self._stream)
        self.pageWidth = self.pageHeight = None
        self._isDrawing = False

    @contextmanager
    def drawing(self):
        from .drawing import Drawing

        drawing = Drawing(self)
        try:
            yield drawing
        finally:
            drawing.endDrawing()

    @property
    def isDrawing(self):
        return self._isDrawing

    def beginPage(self, width, height):
        self.pageWidth = width
        self.pageHeight = height
        self._isDrawing = True
        return self._document.beginPage(width, height)

    def endPage(self):
        self._isDrawing = False
        self._document.endPage()

    def endDrawing(self):
        if self.isDrawing:
            self.endPage()
        self._stream.flush()
        del self._document

    def setFrameDuration(self, duration):
        ...

    def saveImage(self, path, **kwargs):
        raise NotImplementedError()


class SVGDocument(Document):
    ...
