import logging
import math
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import skia
from collections.abc import Sequence
from fontTools.misc.transform import Transform
from fontTools.pens.basePen import BasePen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.pointPen import PointToSegmentPen, SegmentToPointPen
from .errors import DrawbotError
from .formattedString import FormattedString
from .gstate import TextStyle, _strokeCapMapping, _strokeJoinMapping
from .shaping import alignGlyphPositions


# MAYBE:
# - intersectionPoints
# - optimizePath
# - svgClass
# - svgID
# - svgLink
# - traceImage


class BezierPath(BasePen):
    def __init__(self, path=None, glyphSet=None):
        super().__init__(glyphSet)
        if path is None:
            path = skia.Path()
        self.path = path

    def _moveTo(self, pt):
        self.path.moveTo(*pt)

    def _lineTo(self, pt):
        self.path.lineTo(*pt)

    def _curveToOne(self, pt1, pt2, pt3):
        x1, y1 = pt1
        x2, y2 = pt2
        x3, y3 = pt3
        self.path.cubicTo(x1, y1, x2, y2, x3, y3)

    def _qCurveToOne(self, pt1, pt2):
        x1, y1 = pt1
        x2, y2 = pt2
        self.path.quadTo(x1, y1, x2, y2)

    def _closePath(self):
        self.path.close()

    def moveTo(self, point):
        super().moveTo(point)

    def lineTo(self, point):
        super().lineTo(point)

    def beginPath(self, identifier=None):
        self._pointToSegmentPen = PointToSegmentPen(self)
        self._pointToSegmentPen.beginPath()

    def addPoint(
        self,
        point,
        segmentType=None,
        smooth=False,
        name=None,
        identifier=None,
        **kwargs
    ):
        if not hasattr(self, "_pointToSegmentPen"):
            raise AttributeError(
                "path.beginPath() must be called before the path can be used as a point pen"
            )
        self._pointToSegmentPen.addPoint(
            point,
            segmentType=segmentType,
            smooth=smooth,
            name=name,
            identifier=identifier,
            **kwargs
        )

    def endPath(self):
        if hasattr(self, "_pointToSegmentPen"):
            # We are drawing as a point pen
            pointToSegmentPen = self._pointToSegmentPen
            del self._pointToSegmentPen
            pointToSegmentPen.endPath()

    def arc(self, center, radius, startAngle, endAngle, clockwise):
        cx, cy = center
        diameter = radius * 2
        rect = (cx - radius, cy - radius, diameter, diameter)
        sweepAngle = (endAngle - startAngle) % 360
        if clockwise:
            sweepAngle -= 360
        self.path.arcTo(rect, startAngle, sweepAngle, False)

    def arcTo(self, point1, point2, radius):
        self.path.arcTo(point1, point2, radius)

    def rect(self, x, y, w, h):
        self.path.addRect((x, y, w, h))

    def oval(self, x, y, w, h):
        self.path.addOval((x, y, w, h))

    def line(self, point1, point2):
        points = [(x, y) for x, y in [point1, point2]]
        self.path.addPoly(points, False)

    def polygon(self, *points, **kwargs):
        if len(points) <= 1:
            raise TypeError("polygon() expects more than a single point")
        close = kwargs.get("close", True)
        if (len(kwargs) == 1 and "close" not in kwargs) or len(kwargs) > 1:
            raise TypeError("unexpected keyword argument for this function")
        points = [(x, y) for x, y in points]
        self.path.addPoly(points, close)

    def getNSBezierPath(self):
        raise DrawbotError(
            "getNSBezierPath() returns a macOS NSBezierPath and is not available in drawbot-skia"
        )

    def setNSBezierPath(self, path):
        raise DrawbotError(
            "setNSBezierPath() requires a macOS NSBezierPath and is not available in drawbot-skia"
        )

    def pointInside(self, xy):
        x, y = xy
        return self.path.contains(x, y)

    def bounds(self):
        if self.path.countVerbs() == 0:
            return None
        return tuple(self.path.computeTightBounds())

    def controlPointBounds(self):
        if self.path.countVerbs() == 0:
            return None
        return tuple(self.path.getBounds())

    @property
    def contours(self):
        contours = []
        currentContour = None
        for segmentType, points in _iterPathSegments(self.path):
            if segmentType == "moveTo":
                if currentContour is not None:
                    contours.append(currentContour)
                currentContour = _Contour(open=True)
                currentContour._appendSegment(points)
            elif segmentType == "closePath":
                if currentContour is not None:
                    currentContour.open = False
                    contours.append(currentContour)
                    currentContour = None
            else:
                if currentContour is None:
                    currentContour = _Contour(open=True)
                currentContour._appendSegment(points)
        if currentContour is not None:
            contours.append(currentContour)
        return tuple(contours)

    @property
    def points(self):
        return tuple(
            point for contour in self.contours for segment in contour for point in segment
        )

    @property
    def onCurvePoints(self):
        points = []
        for segmentType, segmentPoints in _iterPathSegments(self.path):
            if segmentType != "closePath":
                points.append(segmentPoints[-1])
        return tuple(points)

    @property
    def offCurvePoints(self):
        points = []
        for segmentType, segmentPoints in _iterPathSegments(self.path):
            if segmentType in {"curveTo", "qCurveTo", "conicTo"}:
                points.extend(segmentPoints[:-1])
        return tuple(points)

    def reverse(self):
        path = skia.Path()
        path.reverseAddPath(self.path)
        self.path = path

    def appendPath(self, otherPath):
        self.path.addPath(otherPath.path)

    def copy(self):
        path = skia.Path(self.path)
        return BezierPath(path=path)

    def translate(self, x=0, y=0):
        self.path.offset(x, y)

    def scale(self, x=1, y=None, center=(0, 0)):
        if y is None:
            y = x
        self.transform((x, 0, 0, y, 0, 0), center=center)

    def rotate(self, angle, center=(0, 0)):
        t = Transform()
        t = t.rotate(math.radians(angle))
        self.transform(t, center=center)

    def skew(self, angle1, angle2=0, center=(0, 0)):
        t = Transform()
        t = t.skew(math.radians(angle1), math.radians(angle2))
        self.transform(t, center=center)

    def transform(self, transformMatrix, center=(0, 0)):
        cx, cy = center
        t = Transform()
        t = t.translate(cx, cy)
        t = t.transform(transformMatrix)
        t = t.translate(-cx, -cy)
        matrix = skia.Matrix()
        matrix.setAffine(t)
        self.path.transform(matrix)

    def drawToPen(self, pen):
        it = skia.Path.Iter(self.path, False)
        needEndPath = False
        for verb, points in it:
            penVerb, startIndex, numPoints = _pathVerbsToPenMethod.get(
                verb, (None, None, None)
            )
            if penVerb is None:
                continue
            assert len(points) == numPoints, (verb, numPoints, len(points))
            if penVerb == "conicTo":
                quadPoints = _convertTransformedConicToQuads(*points)
                if quadPoints is not None:
                    for index in range(1, len(quadPoints), 2):
                        pen.qCurveTo(quadPoints[index], quadPoints[index + 1])
                else:
                    # We should only call _convertConicToCubicDirty()
                    # if it.conicWeight() == sqrt(2)/2, but skia-python doesn't
                    # give the correct value.
                    # https://github.com/kyamagu/skia-python/issues/116
                    pen.curveTo(*_convertConicToCubicDirty(*points))
            elif penVerb == "closePath":
                needEndPath = False
                pen.closePath()
            else:
                if penVerb == "moveTo":
                    if needEndPath:
                        pen.endPath()
                    needEndPath = True
                pointArgs = ((x, y) for x, y in points[startIndex:])
                getattr(pen, penVerb)(*pointArgs)
        if needEndPath:
            pen.endPath()

    def drawToPointPen(self, pointPen):
        self.drawToPen(SegmentToPointPen(pointPen))

    def text(self, txt, offset=None, font=None, fontSize=10, align=None, fontNumber=0):
        if not txt:
            return
        textStyle = TextStyle(font=font, fontSize=fontSize, fontNumber=fontNumber)
        glyphsInfo = textStyle.shape(txt)
        alignGlyphPositions(glyphsInfo, align)
        x, y = (0, 0) if offset is None else offset
        self._addGlyphPaths(glyphsInfo, textStyle, x, y)

    def textBox(
        self,
        txt,
        box,
        font=None,
        fontSize=10,
        align=None,
        hyphenation=None,
        fontNumber=0,
    ):
        if not txt:
            return ""
        if isinstance(txt, FormattedString):
            return self._textBoxFormattedString(
                txt, box, align=align, hyphenation=hyphenation
            )

        textStyle = TextStyle(
            font=font,
            fontSize=fontSize,
            fontNumber=fontNumber,
            hyphenation=bool(hyphenation),
        )
        x, y, width, height = box
        lineHeight = textStyle.getLineHeight()
        maxLines = max(0, int(height // lineHeight))
        if maxLines == 0:
            return txt

        lines, overflow = _wrapText(txt, width, maxLines, textStyle)
        firstBaseline = y + height - fontSize
        for lineIndex, line in enumerate(lines):
            if not line:
                continue
            glyphsInfo = textStyle.shape(line)
            lineX = x
            lineAlign = align
            if align == "center":
                lineX += width / 2
            elif align == "right":
                lineX += width
            alignGlyphPositions(glyphsInfo, lineAlign)
            lineY = firstBaseline - lineIndex * lineHeight
            self._addGlyphPaths(glyphsInfo, textStyle, lineX, lineY)
        return overflow

    def _textBoxFormattedString(self, txt, box, align=None, hyphenation=None):
        from .drawing import (
            Drawing,
            _alignmentOffset,
            _formattedLineBaselineOffset,
            _formattedStringBaseLineHeight,
            _lineHeight,
            _textBoxAlign,
        )

        if hyphenation is not None:
            txt = txt.copy()
            txt._properties["hyphenation"] = hyphenation
            txt._runs = [
                (runText, {**properties, "hyphenation": hyphenation})
                for runText, properties in txt._runs
            ]

        drawing = Drawing()
        x, y, width, height = box
        lineHeight = _formattedStringBaseLineHeight(txt, drawing._gstate.textStyle)
        maxLines = max(0, int(height // lineHeight))
        if maxLines == 0:
            return txt.copy()

        lines, overflow = drawing._wrapFormattedString(txt, width, maxLines)
        firstLine = lines[0][0]
        baseline = y + height - _formattedLineBaselineOffset(
            firstLine, drawing._gstate.textStyle
        )
        boxAlign = _textBoxAlign(align)
        for line, xOffset, paragraphStart, paragraphEnd, paragraphProperties in lines:
            if paragraphStart:
                baseline -= paragraphProperties.get("paragraphTopSpacing") or 0
            lineInfo = drawing._formattedLines(line)[0]
            lineWidth, currentLineHeight, runs = lineInfo
            alignOffset = _alignmentOffset(lineWidth, boxAlign)
            for (
                runX,
                glyphsInfo,
                textStyle,
                fillPaint,
                strokePaint,
                baselineShift,
                underline,
                strikethrough,
            ) in runs:
                self._addGlyphPaths(
                    glyphsInfo,
                    textStyle,
                    x + xOffset + alignOffset + runX,
                    baseline + baselineShift,
                )
            baseline -= _lineHeight(lineInfo) if line else currentLineHeight
            if paragraphEnd:
                baseline -= paragraphProperties.get("paragraphBottomSpacing") or 0
        return overflow

    def traceImage(
        self,
        path,
        threshold=0.2,
        blur=None,
        invert=False,
        turd=2,
        tolerance=0.2,
        offset=(0, 0),
    ):
        _traceImage(path, self, threshold, blur, invert, turd, tolerance, offset)

    def _addGlyphPaths(self, glyphsInfo, textStyle, x, y):
        gids = sorted(set(glyphsInfo.gids))
        paths = []
        for gid in gids:
            path = textStyle.skFont.getPath(gid)
            if path is not None:
                path.transform(FLIP_MATRIX)
            paths.append(path)
        paths = dict(zip(gids, paths))
        for gid, pos in zip(glyphsInfo.gids, glyphsInfo.positions):
            path = paths[gid]
            if path is not None:
                self.path.addPath(path, pos[0] + x, pos[1] + y)

    def _doPathOp(self, other, operator):
        from pathops import Path, op

        path1 = Path()
        path2 = Path()
        self.drawToPen(path1.getPen())
        other.drawToPen(path2.getPen())
        result = op(
            path1,
            path2,
            operator,
            fix_winding=True,
            keep_starting_points=True,
        )
        resultPath = BezierPath()
        result.draw(resultPath)
        return resultPath

    def union(self, other):
        from pathops import PathOp

        return self._doPathOp(other, PathOp.UNION)

    def intersection(self, other):
        from pathops import PathOp

        return self._doPathOp(other, PathOp.INTERSECTION)

    def difference(self, other):
        from pathops import PathOp

        return self._doPathOp(other, PathOp.DIFFERENCE)

    def xor(self, other):
        from pathops import PathOp

        return self._doPathOp(other, PathOp.XOR)

    def removeOverlap(self):
        from pathops import Path

        path = Path()
        self.drawToPen(path.getPen())
        path.simplify(
            fix_winding=True,
            keep_starting_points=False,
        )
        resultPath = BezierPath()
        path.draw(resultPath)
        self.path = resultPath.path

    def intersectionPoints(self, other=None):
        if other is not None:
            assert isinstance(other, self.__class__)
        selfSegments = _pathIntersectionSegments(self.path)
        otherSegments = (
            _pathIntersectionSegments(other.path)
            if other is not None
            else selfSegments
        )
        points = []
        seen = set()
        for index1, segment1 in enumerate(selfSegments):
            startIndex = 0 if other is not None else index1 + 1
            for index2, segment2 in enumerate(otherSegments[startIndex:], startIndex):
                if other is None and _segmentsAreAdjacent(segment1, segment2):
                    continue
                for intersection in _segmentIntersections(segment1, segment2):
                    point = tuple(float(v) for v in intersection.pt)
                    key = (round(point[0], 6), round(point[1], 6))
                    if key not in seen:
                        points.append(point)
                        seen.add(key)
        return points

    def optimizePath(self):
        segments = list(_iterRawPathSegments(self.path))
        while segments and segments[-1][0] == "moveTo":
            segments.pop()
        optimizedPath = BezierPath()
        for segmentType, points in segments:
            if segmentType == "moveTo":
                optimizedPath.moveTo(points[0])
            elif segmentType == "lineTo":
                optimizedPath.lineTo(points[0])
            elif segmentType == "curveTo":
                optimizedPath.curveTo(*points)
            elif segmentType == "qCurveTo":
                optimizedPath.qCurveTo(*points)
            elif segmentType == "closePath":
                optimizedPath.closePath()
        self.path = optimizedPath.path

    def expandStroke(
        self, width, lineCap="round", lineJoin="round", miterLimit=10
    ):
        if lineCap not in _strokeCapMapping:
            raise DrawbotError(f"lineCap must be one of: {sorted(_strokeCapMapping)}")
        if lineJoin not in _strokeJoinMapping:
            raise DrawbotError(f"lineJoin must be one of: {sorted(_strokeJoinMapping)}")
        paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=width,
        )
        paint.setStrokeCap(_strokeCapMapping[lineCap])
        paint.setStrokeJoin(_strokeJoinMapping[lineJoin])
        paint.setStrokeMiter(miterLimit)
        path = skia.Path()
        paint.getFillPath(self.path, path)
        return BezierPath(path=path)

    def dashStroke(self, *dash, offset=0):
        if not dash:
            return self.copy()
        intervals = tuple(dash)
        if len(intervals) % 2:
            intervals = intervals * 2
        effect = skia.DashPathEffect.Make(intervals, offset)
        path = skia.Path()
        strokeRec = skia.StrokeRec(skia.StrokeRec.kHairline_InitStyle)
        if not effect.filterPath(path, self.path, strokeRec, self.path.getBounds()):
            path = skia.Path(self.path)
        return BezierPath(path=path)

    __mod__ = difference

    def __imod__(self, other):
        result = self.difference(other)
        self.path = result.path
        return self

    __or__ = union

    def __ior__(self, other):
        result = self.union(other)
        self.path = result.path
        return self

    __and__ = intersection

    def __iand__(self, other):
        result = self.intersection(other)
        self.path = result.path
        return self

    __xor__ = xor

    def __ixor__(self, other):
        result = self.xor(other)
        self.path = result.path
        return self


FLIP_MATRIX = skia.Matrix()
FLIP_MATRIX.setAffine((1, 0, 0, -1, 0, 0))


def _convertTransformedConicToQuads(pt1, pt2, pt3):
    if _conicLooksSafeForCubicShortcut(pt1, pt2, pt3):
        return None
    quadPoints = skia.Path.ConvertConicToQuads(
        skia.Point(*pt1),
        skia.Point(*pt2),
        skia.Point(*pt3),
        math.sqrt(0.5),
        5,
    )
    return [tuple(point) for point in quadPoints]


def _iterConvertedConicSegments(points):
    quadPoints = _convertTransformedConicToQuads(*points)
    if quadPoints is not None:
        for index in range(1, len(quadPoints), 2):
            yield "qCurveTo", (quadPoints[index], quadPoints[index + 1])
        return
    yield "curveTo", _convertConicToCubicDirty(*points)


def _conicLooksSafeForCubicShortcut(pt1, pt2, pt3):
    (x1, y1), (x2, y2), (x3, y3) = pt1, pt2, pt3
    angle1 = math.atan2(y2 - y1, x2 - x1)
    angle2 = math.atan2(y3 - y2, x3 - x2)
    angleDiff = abs((angle1 - angle2) % (2 * math.pi))
    if angleDiff > math.pi:
        angleDiff = 2 * math.pi - angleDiff
    if abs(angleDiff - math.pi / 2) < 0.0001:
        return True
    d1 = math.hypot(x2 - x1, y2 - y1)
    d2 = math.hypot(x2 - x3, y2 - y3)
    return abs(d1 - d2) <= 0.00001


def _convertConicToCubicDirty(pt1, pt2, pt3):
    #
    # NOTE: we do a crude conversion from a conic segment to a cubic bezier,
    # for two common cases, based on the following assumptions:
    # - drawbot itself does not allow conics to be drawn
    # - skia draws conics implicitly for oval(), arc() and arcTo()
    # - for oval the conic segments span 90 degrees
    # - for arc and arcTo the conic segments do not span more than 90 degrees
    # - for arc and arcTo the conic segments are circular, never elliptical
    # For all these cases, the conic weight will be (close to) zero.
    #
    # This no longer holds for some transformed paths. Those fall back to
    # skia.Path.ConvertConicToQuads() before reaching this helper, using the
    # known quarter-arc conic weight where applicable.
    # https://github.com/kyamagu/skia-python/issues/116
    # https://github.com/eliheuer/drawbot-skia/issues/14
    #
    (x1, y1), (x2, y2), (x3, y3) = pt1, pt2, pt3
    dx1 = x2 - x1
    dy1 = y2 - y1
    dx2 = x2 - x3
    dy2 = y2 - y3
    angle1 = math.atan2(dy1, dx1)
    angle2 = math.atan2(-dy2, -dx2)
    angleDiff = (angle1 - angle2) % (2 * math.pi)
    if angleDiff > math.pi:
        angleDiff = 2 * math.pi - angleDiff
    if abs(angleDiff - math.pi / 2) < 0.0001:
        # angle is close enough to 90 degrees, we use stupid old BEZIER_ARC_MAGIC
        handleRatio = 0.5522847498
    else:
        # Fall back to the circular assumption: |pt1 pt2| == |pt2 pt3|
        d1 = math.hypot(dx1, dy1)
        d2 = math.hypot(dx2, dy2)
        if abs(d1 - d2) > 0.00001:
            logging.warning(
                "unsupported conic form (non-circular, non-90-degrees): conic to cubic conversion will be bad"
            )
        angleHalf = angleDiff / 2
        radius = d1 / math.tan(angleHalf)
        D = radius * (1 - math.cos(angleHalf))
        handleLength = (4 * D / 3) / math.sin(angleHalf)  # length of the bcp line
        handleRatio = handleLength / d1
    return (
        (x1 + dx1 * handleRatio, y1 + dy1 * handleRatio),
        (x3 + dx2 * handleRatio, y3 + dy2 * handleRatio),
        (x3, y3),
    )


_pathVerbsToPenMethod = {
    skia.Path.Verb.kMove_Verb: ("moveTo", 0, 1),
    skia.Path.Verb.kLine_Verb: ("lineTo", 1, 2),
    skia.Path.Verb.kCubic_Verb: ("curveTo", 1, 4),
    skia.Path.Verb.kQuad_Verb: ("qCurveTo", 1, 3),
    skia.Path.Verb.kConic_Verb: ("conicTo", 1, 3),
    skia.Path.Verb.kClose_Verb: ("closePath", 1, 1),
    # skia.Path.Verb.kDone_Verb: (None, None),  # "StopIteration", not receiving when using Python iterator
}


def _wrapText(txt, width, maxLines, textStyle):
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
            if _textWidth(candidate, textStyle) <= width:
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
                line, rest = _breakLongWord(word, width, textStyle)
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


def _breakLongWord(word, width, textStyle):
    if textStyle.hyphenation:
        for index in range(len(word) - 1, 0, -1):
            candidate = word[:index] + "-"
            if _textWidth(candidate, textStyle) <= width:
                return candidate, word[index:]
    for index in range(1, len(word) + 1):
        if _textWidth(word[:index], textStyle) > width:
            if index == 1:
                return word[:1], word[1:]
            return word[: index - 1], word[index - 1 :]
    return word, ""


def _textWidth(txt, textStyle):
    if not txt:
        return 0
    return textStyle.shape(txt).endPos[0]


class _Contour(Sequence):
    def __init__(self, segments=(), open=True):
        self._segments = list(segments)
        self.open = open

    def _appendSegment(self, points):
        self._segments.append(tuple(points))

    def __iter__(self):
        return iter(tuple(self._segments))

    def __len__(self):
        return len(self._segments)

    def __getitem__(self, index):
        return tuple(self._segments)[index]

    def __repr__(self):
        return f"{self.__class__.__name__}({tuple(self._segments)!r}, open={self.open!r})"


def _iterPathSegments(path):
    rawSegments = list(skia.Path.Iter(path, False))
    contourStart = None
    for index, (verb, points) in enumerate(rawSegments):
        segmentType, startIndex, numPoints = _pathVerbsToPenMethod.get(
            verb, (None, None, None)
        )
        if segmentType is None:
            continue
        nextVerb = rawSegments[index + 1][0] if index + 1 < len(rawSegments) else None
        if segmentType == "conicTo":
            for conicSegmentType, conicPoints in _iterConvertedConicSegments(points):
                yield conicSegmentType, tuple(
                    _normalizePoint(point) for point in conicPoints
                )
        elif segmentType == "closePath":
            contourStart = None
            yield segmentType, ()
        else:
            segmentPoints = tuple(
                _normalizePoint(point) for point in points[startIndex:]
            )
            if segmentType == "moveTo":
                contourStart = segmentPoints[-1]
            elif (
                segmentType == "lineTo"
                and nextVerb == skia.Path.Verb.kClose_Verb
                and segmentPoints[-1] == contourStart
            ):
                continue
            yield segmentType, segmentPoints


def _iterRawPathSegments(path):
    for verb, points in skia.Path.RawIter(path):
        segmentType, startIndex, numPoints = _pathVerbsToPenMethod.get(
            verb, (None, None, None)
        )
        if segmentType is None:
            continue
        if segmentType == "conicTo":
            for conicSegmentType, conicPoints in _iterConvertedConicSegments(points):
                yield conicSegmentType, tuple(
                    _normalizePoint(point) for point in conicPoints
                )
        elif segmentType == "closePath":
            yield segmentType, ()
        else:
            yield segmentType, tuple(
                _normalizePoint(point) for point in points[startIndex:]
            )


def _pathIntersectionSegments(path):
    contours = []
    contour = []
    contourIndex = -1
    for verb, points in skia.Path.Iter(path, False):
        segmentType, startIndex, numPoints = _pathVerbsToPenMethod.get(
            verb, (None, None, None)
        )
        if segmentType is None:
            continue
        if segmentType == "moveTo":
            if contour:
                contours.append((False, contour))
            contourIndex += 1
            contour = []
            continue
        if segmentType == "closePath":
            if contour:
                contours.append((True, contour))
                contour = []
            continue
        if segmentType == "conicTo":
            for _, conicPoints in _iterConvertedConicSegments(points):
                segmentPoints = tuple(_normalizePoint(point) for point in conicPoints)
                if segmentPoints:
                    contour.append((contourIndex, segmentPoints))
        else:
            segmentPoints = tuple(_normalizePoint(point) for point in points)
            if segmentPoints:
                contour.append((contourIndex, segmentPoints))
    if contour:
        contours.append((False, contour))

    segments = []
    for closed, contour in contours:
        lastIndex = len(contour) - 1
        for index, (contourIndex, points) in enumerate(contour):
            segments.append(
                _IntersectionSegment(
                    points=points,
                    contour=contourIndex,
                    index=index,
                    first=index == 0,
                    last=index == lastIndex,
                    closed=closed,
                )
            )
    return segments


def _segmentsAreAdjacent(segment1, segment2):
    if segment1.contour != segment2.contour:
        return False
    if abs(segment1.index - segment2.index) == 1:
        return True
    return segment1.closed and (
        (segment1.first and segment2.last) or (segment1.last and segment2.first)
    )


def _segmentIntersections(segment1, segment2):
    from fontTools.misc.bezierTools import segmentSegmentIntersections

    return segmentSegmentIntersections(segment1.points, segment2.points)


class _IntersectionSegment:
    def __init__(self, points, contour, index, first, last, closed):
        self.points = points
        self.contour = contour
        self.index = index
        self.first = first
        self.last = last
        self.closed = closed


def _traceImage(path, outPen, threshold, blur, invert, turd, tolerance, offset):
    mkbitmap = shutil.which("mkbitmap")
    potrace = shutil.which("potrace")
    if mkbitmap is None or potrace is None:
        raise DrawbotError("traceImage() requires mkbitmap and potrace")

    from PIL import Image
    from .imageObject import ImageObject

    if isinstance(path, ImageObject):
        image = path._pilImage()
        imageOffset = path.offset()
    else:
        image = Image.open(os.fspath(path)).convert("RGBA")
        imageOffset = (0, 0)
    offset = (imageOffset[0] + offset[0], imageOffset[1] + offset[1])

    with tempfile.TemporaryDirectory(prefix="drawbot-skia-trace-") as tempDir:
        imagePath = os.path.join(tempDir, "image.bmp")
        bitmapPath = os.path.join(tempDir, "image.pgm")
        svgPath = os.path.join(tempDir, "image.svg")
        background = Image.new("RGBA", image.size, (255, 255, 255, 255))
        background.alpha_composite(image)
        background.convert("RGB").save(imagePath)

        command = [mkbitmap, "-x", "-t", str(threshold)]
        if blur:
            command.extend(["-b", str(blur)])
        if invert:
            command.append("-i")
        command.extend(["-o", bitmapPath, imagePath])
        _runTraceCommand(command)

        command = [
            potrace,
            "-s",
            "-t",
            str(turd),
            "-O",
            str(tolerance),
            "-o",
            svgPath,
            bitmapPath,
        ]
        _runTraceCommand(command)
        _importSVGPaths(svgPath, outPen, offset)


def _runTraceCommand(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        raise DrawbotError(f"traceImage() command failed: {message}")


def _importSVGPaths(svgPath, outPen, offset):
    from fontTools.svgLib.path import parse_path

    root = ET.parse(svgPath).getroot()
    identity = Transform()
    offsetTransform = Transform().translate(*offset)
    for element, transform in _iterSVGElements(root, identity):
        if _stripXMLNamespace(element.tag) != "path":
            continue
        pathData = element.attrib.get("d")
        if not pathData:
            continue
        pen = TransformPen(outPen, offsetTransform.transform(transform))
        parse_path(pathData, pen)


def _iterSVGElements(element, transform):
    transform = transform.transform(_parseSVGTransform(element.attrib.get("transform")))
    yield element, transform
    for child in element:
        yield from _iterSVGElements(child, transform)


_svgTransformRE = re.compile(r"([a-zA-Z]+)\(([^)]*)\)")


def _parseSVGTransform(value):
    transform = Transform()
    if not value:
        return transform
    for name, args in _svgTransformRE.findall(value):
        values = [float(v) for v in re.split(r"[,\s]+", args.strip()) if v]
        name = name.lower()
        if name == "translate":
            x = values[0]
            y = values[1] if len(values) > 1 else 0
            transform = transform.translate(x, y)
        elif name == "scale":
            x = values[0]
            y = values[1] if len(values) > 1 else x
            transform = transform.scale(x, y)
        elif name == "matrix" and len(values) == 6:
            transform = transform.transform(values)
    return transform


def _stripXMLNamespace(tag):
    return tag.rsplit("}", 1)[-1]


def _normalizePoint(point):
    x, y = point
    return (float(x), float(y))
