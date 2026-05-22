from drawbot_skia.path import BezierPath
from fontTools.pens.recordingPen import RecordingPen, RecordingPointPen
import pytest


def test_path_bounds():
    path = BezierPath()
    assert path.bounds() is None
    path.rect(10, 20, 30, 40)
    assert path.bounds() == (10, 20, 40, 60)


def test_path_controlPointBounds():
    path = BezierPath()
    assert path.controlPointBounds() is None
    path.moveTo((0, 0))
    path.curveTo((50, 100), (100, 100), (150, 0))
    assert path.bounds() == (0.0, 0.0, 150.0, 75.0)
    assert path.controlPointBounds() == (0.0, 0.0, 150.0, 100.0)


def test_path_copy():
    path1 = BezierPath()
    path1.rect(0, 0, 100, 100)
    path2 = path1.copy()
    path1.translate(50, 20)
    assert path1.bounds() == (50.0, 20.0, 150.0, 120.0)
    assert path2.bounds() == (0.0, 0.0, 100.0, 100.0)


def test_path_point_args():
    path1 = BezierPath()
    path1.moveTo([0, 0])
    path1.lineTo([0, 100])
    path1.curveTo([50, 100], [100, 100], [200, 0])


def test_path_line_args():
    path1 = BezierPath()
    path1.line([0, 0], [0, 100])


def test_path_drawbot_keyword_point_args():
    path = BezierPath()
    path.moveTo(point=(0, 0))
    path.lineTo(point=(10, 0))
    path.line(point1=(0, 0), point2=(0, 100))
    assert path.bounds() == (0.0, 0.0, 10.0, 100.0)

    otherPath = BezierPath()
    otherPath.rect(20, 20, 10, 10)
    path.appendPath(otherPath=otherPath)
    assert path.bounds() == (0.0, 0.0, 30.0, 100.0)

    path.transform(transformMatrix=(1, 0, 0, 1, 5, 0))
    assert path.bounds() == (5.0, 0.0, 35.0, 100.0)

    path.rect(0, 0, 10, 10)
    assert path.pointInside(xy=(5, 5))
    assert not path.pointInside(xy=(40, 40))

    pointPen = RecordingPointPen()
    path.drawToPointPen(pointPen=pointPen)
    assert pointPen.value[0][0] == "beginPath"


def test_transformed_conic_drawToPen_uses_quadratic_fallback(caplog):
    path = BezierPath()
    path.oval(0, 0, 100, 100)
    path.skew(20)

    pen = RecordingPen()
    path.drawToPen(pen)

    commands = [command for command, args in pen.value]
    assert "qCurveTo" in commands
    assert "curveTo" not in commands
    assert "unsupported conic form" not in caplog.text


def test_path_points():
    path = BezierPath()
    path.moveTo((0, 0))
    path.lineTo((100, 0))
    path.curveTo((120, 20), (120, 80), (100, 100))
    path.qCurveTo((50, 120), (0, 100))
    path.closePath()

    assert path.onCurvePoints == (
        (0.0, 0.0),
        (100.0, 0.0),
        (100.0, 100.0),
        (0.0, 100.0),
    )
    assert path.offCurvePoints == (
        (120.0, 20.0),
        (120.0, 80.0),
        (50.0, 120.0),
    )
    assert path.points == path.onCurvePoints[:2] + path.offCurvePoints[:2] + (
        path.onCurvePoints[2],
        path.offCurvePoints[2],
        path.onCurvePoints[3],
    )


def test_path_contours():
    path = BezierPath()
    path.rect(0, 0, 100, 100)
    path.moveTo((200, 0))
    path.lineTo((300, 0))

    contours = path.contours
    assert len(contours) == 2
    assert contours[0].open is False
    assert contours[1].open is True
    assert tuple(contours[0])[0] == ((0.0, 0.0),)
    assert tuple(contours[1]) == (((200.0, 0.0),), ((300.0, 0.0),))


def test_path_expandStroke():
    path = BezierPath()
    path.line((0, 0), (100, 0))
    expanded = path.expandStroke(20, lineCap="round", lineJoin="round")

    assert isinstance(expanded, BezierPath)
    assert expanded.bounds()[0] < 0
    assert expanded.bounds()[1] < 0
    assert expanded.bounds()[2] > 100
    assert expanded.bounds()[3] > 0

    with pytest.raises(Exception):
        path.expandStroke(20, lineCap="bad")
