import contextlib
import functools
import math
import os
import re
import skia
from .document import RecordingDocument
from .errors import DrawbotError
from .formattedString import FormattedString
from .gstate import GraphicsState, GraphicsStateMixin
from .shaping import alignGlyphPositions


DEFAULT_CANVAS_DIMENSIONS = (1000, 1000)

_paperSizes = {
    "Letter": (612, 792),
    "LetterSmall": (612, 792),
    "Tabloid": (792, 1224),
    "Ledger": (1224, 792),
    "Legal": (612, 1008),
    "Statement": (396, 612),
    "Executive": (540, 720),
    "A0": (2384, 3371),
    "A1": (1685, 2384),
    "A2": (1190, 1684),
    "A3": (842, 1190),
    "A4": (595, 842),
    "A4Small": (595, 842),
    "A5": (420, 595),
    "B4": (729, 1032),
    "B5": (516, 729),
    "Folio": (612, 936),
    "Quarto": (610, 780),
    "10x14": (720, 1008),
}

for _name, (_width, _height) in list(_paperSizes.items()):
    _paperSizes[f"{_name}Landscape"] = (_height, _width)


class Drawing:
    def __init__(self, document=None, flipCanvas=True):
        self._flipCanvas = flipCanvas
        self._reset(document)

    def _reset(self, document=None):
        self._stack = []
        self._gstate = GraphicsState()
        self._path = None
        if document is None:
            document = RecordingDocument()
        self._document = document
        self._skia_canvas = None

    @property
    def _canvas(self):
        if self._skia_canvas is None:
            self.size(*DEFAULT_CANVAS_DIMENSIONS)  # This will create the canvas
        return self._skia_canvas

    @_canvas.setter
    def _canvas(self, canvas):
        self._skia_canvas = canvas

    def newDrawing(self):
        self._reset()

    def endDrawing(self):
        self._canvas = None
        self._document.endDrawing()

    def size(self, width, height=None):
        if self._document.isDrawing:
            raise DrawbotError(
                "size() can't be called if there's already a canvas active"
            )
        width, height = _pageSize(width, height)
        self.newPage(width, height)

    def newPage(self, width=None, height=None):
        if isinstance(width, str):
            width, height = _pageSize(width, height)
        if (width is not None and height is None) or (
            height is not None and width is None
        ):
            raise TypeError(
                "newPage() takes either no argument or two - width and height"
            )
        if width is None and height is None:
            width = getattr(self._document, "pageWidth", None)
            height = getattr(self._document, "pageHeight", None)
            if width is None or height is None:
                # this is because dimensions are set only after drawing starts,
                # if you use this function before, it breaks
                width, height = DEFAULT_CANVAS_DIMENSIONS
        if self._document.isDrawing:
            self._document.endPage()
            self._gstate = GraphicsState()
        self._canvas = self._document.beginPage(width, height)
        if self._flipCanvas:
            self._canvas.translate(0, height)
            self._canvas.scale(1, -1)

    def frameDuration(self, duration):
        self._document.setFrameDuration(duration)

    def sizes(self, paperSize=None):
        if paperSize is None:
            return dict(_paperSizes)
        try:
            return _paperSizes[paperSize]
        except KeyError:
            raise DrawbotError(f"unknown paper size: {paperSize}") from None

    def width(self):
        return self._document.pageWidth

    def height(self):
        return self._document.pageHeight

    def pageCount(self):
        return getattr(self._document, "pageCount", 0)

    def numberOfPages(self, path=None):
        if path is None:
            return self.pageCount()
        return _imageNumberOfPages(path)

    def imageSize(self, path):
        image = self._getImage(path)
        return image.width(), image.height()

    def imagePixelColor(self, path, position):
        from PIL import Image

        x, y = position
        if hasattr(path, "_pilImage"):
            imageContext = path._pilImage()
        else:
            imageContext = Image.open(path)
        with imageContext as image:
            width, height = image.size
            if x < 0 or y < 0 or x >= width or y >= height:
                return None
            image = image.convert("RGBA")
            r, g, b, a = image.getpixel((int(x), height - int(y) - 1))
        return tuple(channel / 255 for channel in (r, g, b, a))

    def imageResolution(self, path):
        from PIL import Image

        if hasattr(path, "_pilImage"):
            return (72, 72)
        with Image.open(path) as image:
            return image.info.get("dpi", (72, 72))

    def rect(self, x, y, w, h):
        self._drawItem(self._canvas.drawRect, (x, y, w, h))

    def oval(self, x, y, w, h):
        self._drawItem(self._canvas.drawOval, (x, y, w, h))

    def line(self, pt1, pt2):
        x1, y1 = pt1
        x2, y2 = pt2
        self._drawItem(self._canvas.drawLine, x1, y1, x2, y2)

    def polygon(self, firstPoint, *points, close=True):
        from .path import BezierPath

        bez = BezierPath()
        bez.polygon(firstPoint, *points, close=close)
        self.drawPath(bez)

    def newPath(self):
        from .path import BezierPath

        self._path = BezierPath()

    def _currentPath(self):
        if self._path is None:
            self.newPath()
        return self._path

    def moveTo(self, point):
        self._currentPath().moveTo(point)

    def lineTo(self, point):
        self._currentPath().lineTo(point)

    def curveTo(self, point1, point2, point3):
        self._currentPath().curveTo(point1, point2, point3)

    def qCurveTo(self, *points):
        self._currentPath().qCurveTo(*points)

    def arc(self, center, radius, startAngle, endAngle, clockwise):
        self._currentPath().arc(center, radius, startAngle, endAngle, clockwise)

    def arcTo(self, point1, point2, radius):
        self._currentPath().arcTo(point1, point2, radius)

    def closePath(self):
        self._currentPath().closePath()

    def drawPath(self, path=None):
        if path is None:
            path = self._currentPath()
        self._drawItem(self._canvas.drawPath, path.path)

    def clipPath(self, path=None):
        if path is None:
            path = self._currentPath()
        self._canvas.clipPath(path.path, doAntiAlias=True)

    def textSize(self, txt):
        # TODO: with some smartness we can shape only once, for a
        # textSize()/text() call combination with the same text and
        # the same text parameters.
        if isinstance(txt, FormattedString):
            lines = self._formattedLines(txt)
            if not lines:
                return (0, 0)
            lineWidths = [lineWidth for lineWidth, lineHeight, runs in lines]
            textHeight = _lineSpacing(lines[0])
            for line in lines[1:]:
                textHeight += _lineHeight(line)
            return (max(lineWidths), textHeight)
        else:
            lines = txt.split("\n")
            lineWidths = []
            textStyle = self._gstate.textStyle
            for line in lines:
                if line:
                    lineWidth, runs = self._textLineRuns(
                        line, textStyle, textStyle.tracking
                    )
                    lineWidths.append(lineWidth)
                else:
                    lineWidths.append(0)
            lineHeight = textStyle.getLineHeight()
            textHeight = textStyle.skFont.getSpacing()
            if len(lines) > 1:
                textHeight += lineHeight * (len(lines) - 1)
            return (max(lineWidths), textHeight)

    def text(self, txt, position, align=None):
        if not txt:
            # Hard Skia crash otherwise
            return

        if isinstance(txt, FormattedString):
            self._textFormattedString(txt, position, align)
            return

        textStyle = self._gstate.textStyle
        x, y = position

        with self._savedCanvasState():
            self._canvas.translate(x, y)
            if self._flipCanvas:
                self._canvas.scale(1, -1)
            for lineIndex, line in enumerate(txt.split("\n")):
                if not line:
                    continue
                tracking, baselineShift, underline, strikethrough = (
                    _lineTextProperties(textStyle)
                )
                baseline = lineIndex * textStyle.getLineHeight() + baselineShift
                if not textStyle.tabs or "\t" not in line:
                    glyphsInfo = textStyle.shape(line)
                    if tracking is not None:
                        _applyTracking(glyphsInfo, tracking)
                    alignGlyphPositions(glyphsInfo, align)
                    self._drawGlyphs(glyphsInfo, baseline)
                    x1 = min((x for x, y in glyphsInfo.positions), default=0)
                    x2 = x1 + glyphsInfo.endPos[0]
                else:
                    lineWidth, runs = self._textLineRuns(line, textStyle, tracking)
                    xOffset = _alignmentOffset(lineWidth, align)
                    for runX, glyphsInfo in runs:
                        self._drawGlyphs(
                            glyphsInfo,
                            baseline,
                            x=runX + xOffset,
                        )
                    x1 = xOffset
                    x2 = xOffset + lineWidth
                self._drawTextDecoration(
                    underline,
                    x1,
                    x2,
                    baseline + textStyle.fontSize * 0.1,
                    textStyle,
                    self._gstate.fillPaint,
                )
                self._drawTextDecoration(
                    strikethrough,
                    x1,
                    x2,
                    baseline - textStyle.fontSize * 0.3,
                    textStyle,
                    self._gstate.fillPaint,
                )

    def textBox(self, txt, box, align=None):
        if isinstance(txt, FormattedString):
            return self._textBoxFormattedString(txt, box, align=align)
        x, y, width, height = box
        lineHeight = self._gstate.textStyle.getLineHeight()
        maxLines = max(0, int(height // lineHeight))
        if maxLines == 0:
            return txt

        lines, overflow = self._wrapText(txt, width, maxLines)
        firstBaseline = y + height - self._gstate.textStyle.fontSize
        for lineIndex, line in enumerate(lines):
            lineY = firstBaseline - lineIndex * lineHeight
            self.text(line, (x, lineY), align=_textBoxAlign(align))
        return overflow

    def textOverflow(self, txt, box, align=None):
        if isinstance(txt, FormattedString):
            x, y, width, height = box
            lineHeight = _formattedStringBaseLineHeight(txt, self._gstate.textStyle)
            maxLines = max(0, int(height // lineHeight))
            if maxLines == 0:
                return txt.copy()
            lines, overflow = self._wrapFormattedString(txt, width, maxLines)
            return overflow
        x, y, width, height = box
        lineHeight = self._gstate.textStyle.getLineHeight()
        maxLines = max(0, int(height // lineHeight))
        if maxLines == 0:
            return txt
        lines, overflow = self._wrapText(txt, width, maxLines)
        return overflow

    def textBoxBaselines(self, txt, box, align=None):
        x, y, width, height = box
        if isinstance(txt, FormattedString):
            lineHeight = _formattedStringBaseLineHeight(txt, self._gstate.textStyle)
            maxLines = max(0, int(height // lineHeight))
            if maxLines == 0:
                return []
            lines, overflow = self._wrapFormattedString(txt, width, maxLines)
            baseline = y + height - _formattedLineBaselineOffset(
                lines[0][0], self._gstate.textStyle
            )
            baselines = []
            for line, xOffset, paragraphStart, paragraphEnd, paragraphProperties in lines:
                if paragraphStart:
                    baseline -= paragraphProperties.get("paragraphTopSpacing") or 0
                baselines.append((x + xOffset, baseline))
                if line:
                    lineInfo = self._formattedLines(line)[0]
                    lineHeight = _lineHeight(lineInfo)
                else:
                    lineHeight = _formattedStringBaseLineHeight(
                        line, self._gstate.textStyle
                    )
                baseline -= lineHeight
                if paragraphEnd:
                    baseline -= paragraphProperties.get("paragraphBottomSpacing") or 0
            return baselines
        lineHeight = self._gstate.textStyle.getLineHeight()
        maxLines = max(0, int(height // lineHeight))
        if maxLines == 0:
            return []
        lines, overflow = self._wrapText(txt, width, maxLines)
        firstBaseline = y + height - self._gstate.textStyle.fontSize
        baselines = []
        for lineIndex, line in enumerate(lines):
            lineWidth = self.textSize(line)[0] if line else 0
            baselines.append(
                (
                    x + _alignmentOffset(lineWidth, _textBoxAlign(align)),
                    firstBaseline - lineIndex * lineHeight,
                )
            )
        return baselines

    def _wrapText(self, txt, width, maxLines):
        lines = []
        remainingParagraphs = txt.split("\n")
        for paragraphIndex, paragraph in enumerate(remainingParagraphs):
            words = paragraph.split(" ")
            currentLine = ""
            wordIndex = 0
            while wordIndex < len(words):
                word = words[wordIndex]
                candidate = word if not currentLine else currentLine + " " + word
                if not candidate.strip():
                    wordIndex += 1
                    continue
                if self.textSize(candidate)[0] <= width:
                    currentLine = candidate
                    wordIndex += 1
                    continue
                if currentLine:
                    lines.append(currentLine)
                    currentLine = ""
                    if len(lines) == maxLines:
                        overflow = " ".join(words[wordIndex:])
                        rest = remainingParagraphs[paragraphIndex + 1 :]
                        if rest:
                            overflow += "\n" + "\n".join(rest)
                        return lines, overflow
                else:
                    line, rest = self._breakLongWord(
                        word, width, self._gstate.textStyle.hyphenation
                    )
                    lines.append(line)
                    words[wordIndex] = rest
                    if len(lines) == maxLines:
                        overflow = " ".join(words[wordIndex:])
                        restParagraphs = remainingParagraphs[paragraphIndex + 1 :]
                        if restParagraphs:
                            overflow += "\n" + "\n".join(restParagraphs)
                        return lines, overflow
            if currentLine or paragraph == "":
                lines.append(currentLine)
                if len(lines) == maxLines:
                    rest = remainingParagraphs[paragraphIndex + 1 :]
                    return lines, "\n".join(rest)
        return lines, ""

    def _breakLongWord(self, word, width, hyphenation=False):
        if hyphenation:
            for index in range(len(word) - 1, 0, -1):
                candidate = word[:index] + "-"
                if self.textSize(candidate)[0] <= width:
                    return candidate, word[index:]
        for index in range(1, len(word) + 1):
            if self.textSize(word[:index])[0] > width:
                if index == 1:
                    return word[:1], word[1:]
                return word[: index - 1], word[index - 1 :]
        return word, ""

    def _textBoxFormattedString(self, txt, box, align=None):
        x, y, width, height = box
        lineHeight = _formattedStringBaseLineHeight(txt, self._gstate.textStyle)
        maxLines = max(0, int(height // lineHeight))
        if maxLines == 0:
            return txt.copy()

        lines, overflow = self._wrapFormattedString(txt, width, maxLines)
        firstLine = lines[0][0]
        baseline = y + height - _formattedLineBaselineOffset(
            firstLine, self._gstate.textStyle
        )
        boxAlign = _textBoxAlign(align)
        for line, xOffset, paragraphStart, paragraphEnd, paragraphProperties in lines:
            if paragraphStart:
                baseline -= paragraphProperties.get("paragraphTopSpacing") or 0
            self.text(line, (x + xOffset, baseline), align=boxAlign)
            if line:
                lineInfo = self._formattedLines(line)[0]
                lineHeight = _lineHeight(lineInfo)
            else:
                lineHeight = _formattedStringBaseLineHeight(
                    line, self._gstate.textStyle
                )
            baseline -= lineHeight
            if paragraphEnd:
                baseline -= paragraphProperties.get("paragraphBottomSpacing") or 0
        return overflow

    def _wrapFormattedString(self, txt, width, maxLines):
        tokens = _formattedStringTokens(txt)
        lines = []
        line = []
        index = 0
        paragraphProperties = txt.textProperties()
        paragraphStart = True
        firstParagraphLine = True

        def finishLine(nextIndex, paragraphEnd=False):
            nonlocal firstParagraphLine, paragraphStart
            if line or paragraphEnd or not lines:
                xOffset, lineWidth = _formattedLineBox(
                    paragraphProperties, width, firstParagraphLine
                )
                lines.append(
                    (
                        _formattedStringFromTokens(line, txt),
                        xOffset,
                        paragraphStart,
                        paragraphEnd,
                        dict(paragraphProperties),
                    )
                )
            if len(lines) == maxLines:
                return _formattedStringFromTokens(tokens[nextIndex:], txt)
            line.clear()
            paragraphStart = paragraphEnd
            firstParagraphLine = paragraphEnd
            return None

        while index < len(tokens):
            tokenText, tokenProperties = tokens[index]
            if not line and firstParagraphLine:
                paragraphProperties = tokenProperties
            if tokenText == "\n":
                overflow = finishLine(index + 1, paragraphEnd=True)
                if overflow is not None:
                    return lines, overflow
                index += 1
                continue
            if tokenText.isspace() and not line:
                index += 1
                continue

            candidate = line + [(tokenText, tokenProperties)]
            xOffset, lineWidth = _formattedLineBox(
                paragraphProperties, width, firstParagraphLine
            )
            if self.textSize(_formattedStringFromTokens(candidate, txt))[0] <= lineWidth:
                line[:] = candidate
                index += 1
                continue
            if line:
                overflow = finishLine(index)
                if overflow is not None:
                    return lines, overflow
                continue

            fitText, restText = self._breakFormattedToken(
                tokenText,
                tokenProperties,
                txt,
                lineWidth,
                tokenProperties.get("hyphenation", False),
            )
            line.append((fitText, tokenProperties))
            if restText:
                tokens[index] = (restText, tokenProperties)
            else:
                index += 1
            overflow = finishLine(index)
            if overflow is not None:
                return lines, overflow

        if line or not lines:
            xOffset, lineWidth = _formattedLineBox(
                paragraphProperties, width, firstParagraphLine
            )
            lines.append(
                (
                    _formattedStringFromTokens(line, txt),
                    xOffset,
                    paragraphStart,
                    True,
                    dict(paragraphProperties),
                )
            )
        return lines, _formattedStringFromTokens([], txt)

    def _breakFormattedToken(
        self, tokenText, tokenProperties, source, width, hyphenation=False
    ):
        if hyphenation:
            for index in range(len(tokenText) - 1, 0, -1):
                candidate = _formattedStringFromTokens(
                    [(tokenText[:index] + "-", tokenProperties)], source
                )
                if self.textSize(candidate)[0] <= width:
                    return tokenText[:index] + "-", tokenText[index:]
        for index in range(1, len(tokenText) + 1):
            candidate = _formattedStringFromTokens(
                [(tokenText[:index], tokenProperties)], source
            )
            if self.textSize(candidate)[0] > width:
                if index == 1:
                    return tokenText[:1], tokenText[1:]
                return tokenText[: index - 1], tokenText[index - 1 :]
        return tokenText, ""

    def _textFormattedString(self, txt, position, align=None):
        x, y = position
        lines = self._formattedLines(txt)
        if align is None:
            align = txt.textProperties().get("align")
        with self._savedCanvasState():
            self._canvas.translate(x, y)
            if self._flipCanvas:
                self._canvas.scale(1, -1)
            baseline = 0
            for line in lines:
                lineWidth, lineHeight, runs = line
                xOffset = _alignmentOffset(lineWidth, align)
                for run in runs:
                    (
                        runX,
                        glyphsInfo,
                        textStyle,
                        fillPaint,
                        strokePaint,
                        baselineShift,
                        underline,
                        strikethrough,
                    ) = run
                    with self._temporaryTextState(textStyle, fillPaint, strokePaint):
                        runBaseline = baseline + baselineShift
                        self._drawGlyphs(
                            glyphsInfo,
                            runBaseline,
                            x=runX + xOffset,
                        )
                        self._drawTextDecoration(
                            underline,
                            runX + xOffset,
                            runX + xOffset + glyphsInfo.endPos[0],
                            runBaseline + textStyle.fontSize * 0.1,
                            textStyle,
                            fillPaint,
                        )
                        self._drawTextDecoration(
                            strikethrough,
                            runX + xOffset,
                            runX + xOffset + glyphsInfo.endPos[0],
                            runBaseline - textStyle.fontSize * 0.3,
                            textStyle,
                            fillPaint,
                        )
                baseline += lineHeight

    def _formattedLines(self, txt):
        lines = []
        currentRuns = []
        lineWidth = 0
        lineHeight = self._gstate.textStyle.getLineHeight()
        for runText, properties in txt._iterRuns():
            textStyle = _textStyleWithProperties(self._gstate.textStyle, properties)
            fillPaint = _fillPaintWithProperties(self._gstate.fillPaint, properties)
            strokePaint = _strokePaintWithProperties(
                self._gstate.strokePaint, properties
            )
            runLineHeight = textStyle.getLineHeight()
            for index, part in enumerate(runText.split("\n")):
                if index:
                    lines.append((lineWidth, lineHeight, currentRuns))
                    currentRuns = []
                    lineWidth = 0
                    lineHeight = runLineHeight
                if not part:
                    lineHeight = max(lineHeight, runLineHeight)
                    continue
                runLineWidth, runSegments = self._textLineRuns(
                    part, textStyle, properties.get("tracking", textStyle.tracking)
                )
                for runX, glyphsInfo in runSegments:
                    currentRuns.append(
                        (
                            lineWidth + runX,
                            glyphsInfo,
                            textStyle,
                            fillPaint,
                            strokePaint,
                            properties.get("baselineShift", textStyle.baselineShift),
                            properties.get("underline", textStyle.underline),
                            properties.get("strikethrough", textStyle.strikethrough),
                        )
                    )
                lineWidth += runLineWidth
                lineHeight = max(lineHeight, runLineHeight)
        lines.append((lineWidth, lineHeight, currentRuns))
        return lines

    def _textLineRuns(self, line, textStyle, tracking=None):
        tabs = textStyle.tabs
        if not tabs or "\t" not in line:
            glyphsInfo = textStyle.shape(line)
            if tracking is not None:
                _applyTracking(glyphsInfo, tracking)
            return glyphsInfo.endPos[0], [(0, glyphsInfo)]

        runs = []
        lineWidth = 0
        pendingTab = None
        for index, part in enumerate(line.split("\t")):
            if index:
                pendingTab = _nextTabStop(lineWidth, tabs)
            if not part:
                continue
            glyphsInfo = textStyle.shape(part)
            if tracking is not None:
                _applyTracking(glyphsInfo, tracking)
            runWidth = glyphsInfo.endPos[0]
            if pendingTab is None:
                runX = lineWidth
            else:
                tabPosition, alignment = pendingTab
                runX = _alignedTabRunX(part, runWidth, tabPosition, alignment, textStyle)
                pendingTab = None
            runs.append((runX, glyphsInfo))
            lineWidth = max(lineWidth, runX + runWidth)
        return lineWidth, runs

    def _drawGlyphs(self, glyphsInfo, y, x=0):
        textStyle = self._gstate.textStyle
        if "COLR" not in textStyle.ttFont:
            builder = skia.TextBlobBuilder()
            builder.allocRunPos(textStyle.skFont, glyphsInfo.gids, glyphsInfo.positions)
            blob = builder.make()
            self._drawItem(self._canvas.drawTextBlob, blob, x, y)
        else:
            from blackrenderer.backends.skia import SkiaCanvas

            ttFont = textStyle.ttFont
            brFont = textStyle.brFont
            if textStyle.variations:
                brFont.setLocation(textStyle.variations)

            canvas = SkiaCanvas(self._canvas)
            scaleFactor = textStyle.fontSize / brFont.unitsPerEm
            a, r, g, b = (ch / 255 for ch in self._gstate.fillPaint.color)
            textColor = (r, g, b, a)
            for gid, (glyphX, glyphY) in zip(glyphsInfo.gids, glyphsInfo.positions):
                glyphName = ttFont.getGlyphName(gid)
                with self._savedCanvasState():
                    self._canvas.translate(x + glyphX, glyphY + y)
                    self._canvas.scale(scaleFactor, -scaleFactor)
                    brFont.drawGlyph(
                        glyphName, canvas, palette=None, textColor=textColor
                    )

    def _drawTextDecoration(self, decoration, x1, x2, y, textStyle, fillPaint):
        if decoration is None:
            return
        thickness = max(1, textStyle.fontSize / 16)
        if decoration == "thick":
            thickness = max(2, textStyle.fontSize / 8)
        paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style)
        alpha, red, green, blue = fillPaint.color
        paint.setARGB(round(alpha * fillPaint.opacity), red, green, blue)
        paint.setStrokeWidth(thickness)
        self._canvas.drawLine(x1, y, x2, y, paint)
        if decoration == "double":
            self._canvas.drawLine(
                x1, y + thickness * 2.5, x2, y + thickness * 2.5, paint
            )

    @contextlib.contextmanager
    def _temporaryTextState(self, textStyle, fillPaint, strokePaint):
        oldGState = self._gstate
        self._gstate = self._gstate.copy()
        self._gstate.textStyle = textStyle
        self._gstate.fillPaint = fillPaint
        self._gstate.strokePaint = strokePaint
        try:
            yield
        finally:
            self._gstate = oldGState

    def image(self, imagePath, position, alpha=1.0):
        im = self._getImage(imagePath)
        paint = skia.Paint()
        opacity = alpha * self._gstate.fillPaint.opacity
        if opacity != 1.0:
            paint.setAlpha(round(opacity * 255))
        if self._gstate.fillPaint.blendMode != "normal":
            paint.setBlendMode(self._gstate.fillPaint.skPaint.getBlendMode())
        x, y = position
        with self._savedCanvasState():
            self._canvas.translate(x, y + im.height())
            if self._flipCanvas:
                self._canvas.scale(1, -1)
            self._canvas.drawImage(im, 0, 0, paint=paint)

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def _getImage(imagePath):
        if hasattr(imagePath, "_skiaImage"):
            return imagePath._skiaImage()
        return skia.Image.open(os.fspath(imagePath))

    def translate(self, x, y):
        self._canvas.translate(x, y)

    def rotate(self, angle, center=(0, 0)):
        cx, cy = center
        self._canvas.rotate(angle, cx, cy)

    def scale(self, sx, sy=None, center=(0, 0)):
        if sy is None:
            sy = sx
        cx, cy = center
        if cx != 0 or cy != 0:
            self._canvas.translate(cx, cy)
            self._canvas.scale(sx, sy)
            self._canvas.translate(-cx, -cy)
        else:
            self._canvas.scale(sx, sy)

    def skew(self, sx, sy=0, center=(0, 0)):
        cx, cy = center
        if cx != 0 or cy != 0:
            self._canvas.translate(cx, cy)
            self._canvas.skew(math.radians(sx), math.radians(sy))
            self._canvas.translate(-cx, -cy)
        else:
            self._canvas.skew(math.radians(sx), math.radians(sy))

    def transform(self, matrix, center=(0, 0)):
        m = skia.Matrix()
        m.setAffine(matrix)
        cx, cy = center
        if cx != 0 or cy != 0:
            self._canvas.translate(cx, cy)
            self._canvas.concat(m)
            self._canvas.translate(-cx, -cy)
        else:
            self._canvas.concat(m)

    @contextlib.contextmanager
    def savedState(self):
        self.save()
        try:
            yield
        finally:
            self.restore()

    def save(self):
        self._stack.append(self._gstate.copy())
        self._canvas.save()

    def restore(self):
        if not self._stack:
            raise DrawbotError("restore() called without a matching save()")
        self._canvas.restore()
        self._gstate = self._stack.pop()

    @contextlib.contextmanager
    def _savedCanvasState(self):
        self._canvas.save()
        try:
            yield
        finally:
            self._canvas.restore()

    def saveImage(self, fileName, **kwargs):
        if self._document.isDrawing:
            self._document.endPage()
        self._document.saveImage(fileName, **kwargs)

    # Helpers

    def _drawItem(self, canvasMethod, *items):
        shadowPaintFill, offset = self._gstate.fillPaint.skPaintShadowAndOffset
        if shadowPaintFill is not None:
            shadowPaintStroke, _ = self._gstate.strokePaint.skPaintShadowAndOffset
            dx, dy = offset
            with self._savedCanvasState():
                self._canvas.translate(dx, dy)
                if self._gstate.fillPaint.somethingToDraw:
                    canvasMethod(*items, shadowPaintFill)
                if self._gstate.strokePaint.somethingToDraw:
                    canvasMethod(*items, shadowPaintStroke)

        if self._gstate.fillPaint.somethingToDraw:
            canvasMethod(*items, self._gstate.fillPaint.skPaint)
        if self._gstate.strokePaint.somethingToDraw:
            canvasMethod(*items, self._gstate.strokePaint.skPaint)


def _makeWrapper(name):
    @functools.wraps(getattr(GraphicsStateMixin, name))
    def wrapper(self, *args, **kwargs):
        method = getattr(self._gstate, name)
        return method(*args, **kwargs)

    wrapper.__qualname__ = f"Drawing.{name}"
    return wrapper


def _pageSize(width, height=None):
    if isinstance(width, str):
        if height is not None:
            raise TypeError("named paper sizes take one argument")
        try:
            return _paperSizes[width]
        except KeyError:
            raise DrawbotError(f"unknown paper size: {width}") from None
    if height is None:
        raise TypeError("size() takes either a paper size name or width and height")
    return width, height


def _textStyleWithProperties(textStyle, properties):
    textProperties = {}
    for name in (
        "font",
        "fontSize",
        "lineHeight",
        "features",
        "variations",
        "language",
        "direction",
        "tabs",
        "hyphenation",
        "fallbackFont",
        "fallbackFontNumber",
    ):
        if name in properties:
            textProperties[name] = properties[name]
    if textProperties:
        textStyle = textStyle.copy(**textProperties)
    return textStyle


def _fillPaintWithProperties(fillPaint, properties):
    if "fill" in properties:
        color = properties["fill"]
        if color is None:
            return fillPaint.copy(somethingToDraw=False, shader=None)
        return fillPaint.copy(color=color, somethingToDraw=True, shader=None)
    return fillPaint


def _strokePaintWithProperties(strokePaint, properties):
    update = {}
    if "stroke" in properties:
        color = properties["stroke"]
        if color is None:
            update.update(somethingToDraw=False, shader=None)
        else:
            update.update(color=color, somethingToDraw=True, shader=None)
    if "strokeWidth" in properties:
        update["strokeWidth"] = properties["strokeWidth"]
    if update:
        return strokePaint.copy(**update)
    return strokePaint


def _lineTextProperties(textStyle):
    return (
        textStyle.tracking,
        textStyle.baselineShift or 0,
        textStyle.underline,
        textStyle.strikethrough,
    )


def _applyTracking(glyphsInfo, tracking):
    positions = []
    for index, (x, y) in enumerate(glyphsInfo.positions):
        positions.append((x + index * tracking, y))
    glyphsInfo.positions = positions
    if positions:
        glyphsInfo.endPos = (
            glyphsInfo.endPos[0] + tracking * (len(positions) - 1),
            glyphsInfo.endPos[1],
        )


def _alignmentOffset(lineWidth, align):
    if align == "center":
        return -lineWidth / 2
    elif align == "right":
        return -lineWidth
    else:
        return 0


def _nextTabStop(x, tabs):
    for tab in tabs:
        position = tab[0]
        if position > x:
            alignment = tab[1] if len(tab) > 1 else "left"
            return position, alignment
    position = tabs[-1][0]
    if position <= 0:
        return x, "left"
    while position <= x:
        position += tabs[-1][0]
    alignment = tabs[-1][1] if len(tabs[-1]) > 1 else "left"
    return position, alignment


def _alignedTabRunX(part, runWidth, tabPosition, alignment, textStyle):
    if alignment == "center":
        return tabPosition - runWidth / 2
    if alignment == "right":
        return tabPosition - runWidth
    if isinstance(alignment, str) and len(alignment) == 1:
        index = part.find(alignment)
        if index >= 0:
            anchorText = part[:index]
            if anchorText:
                anchorWidth = textStyle.shape(anchorText).endPos[0]
            else:
                anchorWidth = 0
            return tabPosition - anchorWidth
    return tabPosition


def _textBoxAlign(align):
    if align == "justified":
        return None
    return align


def _formattedLineBox(properties, width, isFirstLine):
    indent = properties.get("indent") or 0
    if isFirstLine:
        indent += properties.get("firstLineIndent") or 0
    tailIndent = properties.get("tailIndent")
    if tailIndent is None:
        rightEdge = width
    elif tailIndent <= 0:
        rightEdge = width + tailIndent
    else:
        rightEdge = tailIndent
    return indent, max(0, rightEdge - indent)


def _formattedStringTokens(txt):
    tokens = []
    for runText, properties in txt._iterRuns():
        for tokenText in re.findall(r"\n| +|[^ \n]+", runText):
            tokens.append((tokenText, dict(properties)))
    return tokens


def _formattedStringFromTokens(tokens, source):
    result = FormattedString()
    result._properties = dict(source._properties)
    result._features = dict(source._features)
    result._variations = dict(source._variations)
    for tokenText, properties in tokens:
        if not tokenText:
            continue
        if result._runs and result._runs[-1][1] == properties:
            previousText, previousProperties = result._runs[-1]
            result._runs[-1] = (previousText + tokenText, previousProperties)
        else:
            result._runs.append((tokenText, dict(properties)))
    return result


def _formattedStringBaseLineHeight(txt, textStyle):
    lineHeight = txt.textProperties().get("lineHeight")
    if lineHeight is not None:
        return lineHeight
    fontSize = txt.textProperties().get("fontSize", textStyle.fontSize)
    return fontSize * 1.2


def _formattedLineBaselineOffset(txt, textStyle):
    fontSizes = [
        properties.get("fontSize", textStyle.fontSize)
        for runText, properties in txt._iterRuns()
        if runText
    ]
    if not fontSizes:
        return textStyle.fontSize
    return max(fontSizes)


def _lineHeight(line):
    lineWidth, lineHeight, runs = line
    return lineHeight


def _lineSpacing(line):
    lineWidth, lineHeight, runs = line
    if not runs:
        return lineHeight
    return max(
        textStyle.skFont.getSpacing()
        for (
            x,
            glyphsInfo,
            textStyle,
            fill,
            stroke,
            baselineShift,
            underline,
            strikethrough,
        ) in runs
    )


def _imageNumberOfPages(path):
    from PIL import Image

    suffix = os.fspath(path).lower().rsplit(".", 1)[-1]
    if suffix == "gif":
        with Image.open(path) as image:
            return getattr(image, "n_frames", 1)
    return None


# Inject GraphicsStateMixin method wrappers into Drawing
for name in dir(GraphicsStateMixin):
    if name[0] != "_":
        setattr(Drawing, name, _makeWrapper(name))
