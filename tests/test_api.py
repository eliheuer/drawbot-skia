import os
import pathlib
import sys
import pytest
from PIL import Image
import numpy as np
from drawbot_skia.runner import makeDrawbotNamespace, runScript, runScriptSource
from drawbot_skia.drawing import Drawing
from drawbot_skia.errors import DrawbotError
from drawbot_skia.formattedString import FormattedString
from drawbot_skia.path import BezierPath


testDir = pathlib.Path(__file__).resolve().parent
apiTestsDir = testDir / "apitests"
apiTestsOutputDir = testDir / "apitests_output"
apiTestsExpectedOutputDir = testDir / "apitests_expected_output"


apiScripts = apiTestsDir.glob("*.py")


expectedFailures = [
    ("clip", "svg", "darwin"),
    ("clip", "pdf", "linux"),
    ("clip", "svg", "linux"),
    ("clip", "pdf", "win32"),
    ("clip", "svg", "win32"),
    ("fontFromPath", "pdf", "linux"),
    ("fontFromPath", "pdf", "win32"),
    ("fontFromPath", "svg", "win32"),
    ("fontFromPath2", "pdf", "linux"),
    ("fontFromPath2", "pdf", "win32"),
    ("fontVariations", "pdf", "linux"),
    ("fontVariations", "svg", "linux"),
    ("fontVariations", "pdf", "win32"),
    ("fontVariations", "svg", "win32"),
    ("fontVariations", "pdf", "darwin"),
    ("image", "pdf", "linux"),
    ("image", "pdf", "win32"),
    ("imageBlendMode", "pdf", "linux"),
    ("imageBlendMode", "pdf", "win32"),
    ("language", "pdf", "linux"),
    ("language", "pdf", "win32"),
    ("pathText", "pdf", "linux"),
    ("pathText", "svg", "linux"),
    ("pathText", "pdf", "win32"),
    ("pathText", "svg", "win32"),
    ("pathTextRemoveOverlap", "pdf", "linux"),
    ("pathTextRemoveOverlap", "svg", "linux"),
    ("pathTextRemoveOverlap", "pdf", "win32"),
    ("pathTextRemoveOverlap", "svg", "win32"),
    ("textShaping", "pdf", "linux"),
    ("textShaping", "pdf", "win32"),
]


@pytest.mark.parametrize("apiTestPath", apiScripts)
@pytest.mark.parametrize("imageType", ["png", "jpg", "pdf", "svg"])
def test_apitest(apiTestPath, imageType):
    apiTestPath = pathlib.Path(apiTestPath)
    db = Drawing()
    namespace = makeDrawbotNamespace(db)
    runScript(apiTestPath, namespace)
    if not apiTestsOutputDir.exists():
        apiTestsOutputDir.mkdir()
    fileName = apiTestPath.stem + f".{imageType}"
    outputPath = apiTestsOutputDir / fileName
    expectedOutputPath = apiTestsExpectedOutputDir / fileName
    db.saveImage(outputPath)
    if (apiTestPath.stem, imageType, sys.platform) in expectedFailures:
        # Skip late, so we can still inspect the output
        pytest.skip(f"Skipping expected failure {apiTestPath.stem}.{imageType}")
    same, reason = compareImages(outputPath, expectedOutputPath)
    assert same, f"{reason} {apiTestPath.name} {imageType}"


multipageSource = """
for i in range(3):
    newPage(200, 200)
    rect(50, 50, 100, 100)
"""


singlepageSource = """
newPage(200, 200)
rect(50, 50, 100, 100)
"""


test_data_saveImage = [
    (singlepageSource, "png", ["test.png"]),
    (singlepageSource, "jpg", ["test.jpg"]),
    (singlepageSource, "gif", ["test.gif"]),
    (singlepageSource, "svg", ["test.svg"]),
    (singlepageSource, "pdf", ["test.pdf"]),
    # (singlepageSource, "mp4", ["test.mp4"]),
    (multipageSource, "png", ["test_0.png", "test_1.png", "test_2.png"]),
    (multipageSource, "jpg", ["test_0.jpg", "test_1.jpg", "test_2.jpg"]),
    (multipageSource, "gif", ["test.gif"]),
    (multipageSource, "svg", ["test_0.svg", "test_1.svg", "test_2.svg"]),
    (multipageSource, "pdf", ["test.pdf"]),
    # (multipageSource, "mp4", ["test.mp4"]),
]


@pytest.mark.parametrize("script, imageType, expectedFilenames", test_data_saveImage)
def test_saveImage_multipage(tmpdir, script, imageType, expectedFilenames):
    glob_pattern = f"*.{imageType}"
    tmpdir = pathlib.Path(tmpdir)
    db = Drawing()
    namespace = makeDrawbotNamespace(db)
    runScriptSource(script, "<string>", namespace)
    assert [] == sorted(tmpdir.glob(glob_pattern))
    outputPath = tmpdir / f"test.{imageType}"
    db.saveImage(outputPath)
    assert expectedFilenames == [p.name for p in sorted(tmpdir.glob(glob_pattern))]


@pytest.mark.skipif(sys.platform == "darwin", reason="currently broken on macOS")
def test_saveImage_mp4_codec(tmpdir):
    from drawbot_skia import ffmpeg

    ffmpeg.FFMPEG_PATH = ffmpeg.getPyFFmpegPath()  # Force ffmpeg from pyffmpeg
    tmpdir = pathlib.Path(tmpdir)
    db = Drawing()
    namespace = makeDrawbotNamespace(db)
    runScriptSource(multipageSource, "<string>", namespace)
    assert [] == sorted(tmpdir.glob("*.png"))
    db.saveImage(tmpdir / "test.mp4")
    db.saveImage(tmpdir / "test2.mp4", codec="mpeg4")
    expectedFilenames = ["test.mp4", "test2.mp4"]
    paths = sorted(tmpdir.glob("*.mp4"))
    assert paths[0].stat().st_size < paths[1].stat().st_size
    assert expectedFilenames == [p.name for p in paths]


def test_saveImage_gif_frame_durations(tmpdir):
    source = """
newPage(100, 100)
frameDuration(0.2)
fill(1, 0, 0)
rect(0, 0, 100, 100)
newPage(100, 100)
frameDuration(0.5)
fill(0, 0, 1)
rect(0, 0, 100, 100)
"""
    tmpdir = pathlib.Path(tmpdir)
    db = Drawing()
    namespace = makeDrawbotNamespace(db)
    runScriptSource(source, "<string>", namespace)
    outputPath = tmpdir / "test.gif"
    db.saveImage(outputPath)

    im = Image.open(outputPath)
    assert im.n_frames == 2
    im.seek(0)
    assert im.info["duration"] == 200
    im.seek(1)
    assert im.info["duration"] == 500


def test_noFont(tmpdir):
    db = Drawing()
    # Ensure we don't get an error when font is not set
    db.text("Hallo", (0, 0))


def test_newPage_newGState():
    # Test a bug with the delegate properties of Drawing: they should
    # not return the delegate method itself, but a wrapper that calls the
    # delegate method, as the delegate object does not have a fixed
    # identity
    db = Drawing()
    fill = db.fill  # Emulate a db namespace: all methods are retrieved once
    db.newPage(50, 50)
    with db.savedState():
        fill(0.5)
        assert (255, 128, 128, 128) == db._gstate.fillPaint.color
    db.newPage(50, 50)
    fill(1)
    assert (255, 255, 255, 255) == db._gstate.fillPaint.color


def test_newPage_dimensions_arguments():
    from drawbot_skia.drawing import DEFAULT_CANVAS_DIMENSIONS

    db = Drawing()
    db.rect(0, 0, 300, 300)  # the dimensions are set only after drawing starts
    assert (db.width(), db.height()) == DEFAULT_CANVAS_DIMENSIONS
    db.newPage(600, 450)
    db.rect(0, 0, 300, 300)
    assert (db.width(), db.height()) == (600, 450)
    db.newPage()
    db.rect(0, 0, 300, 300)
    assert (db.width(), db.height()) == (600, 450)
    with pytest.raises(TypeError):
        db.newPage(10)
    with pytest.raises(TypeError):
        db.newPage(width=10)
    with pytest.raises(TypeError):
        db.newPage(height=10)


def test_pageCount(tmpdir):
    db = Drawing()
    assert db.pageCount() == 0
    assert db.numberOfPages() == 0
    db.newPage(100, 100)
    assert db.pageCount() == 1
    db.newPage(100, 100)
    assert db.pageCount() == 2
    db.saveImage(pathlib.Path(tmpdir) / "test.pdf")
    assert db.pageCount() == 2


def test_image_properties(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "props.png"
    image = Image.new("RGBA", (4, 3), (0, 0, 0, 0))
    image.putpixel((1, 0), (255, 0, 0, 128))
    image.putpixel((2, 2), (0, 255, 0, 255))
    image.save(imagePath, dpi=(144, 144))

    db = Drawing()
    assert db.imageSize(imagePath) == (4, 3)
    xDpi, yDpi = db.imageResolution(imagePath)
    assert xDpi == pytest.approx(144, abs=0.01)
    assert yDpi == pytest.approx(144, abs=0.01)
    assert db.imagePixelColor(imagePath, (1, 2)) == (1, 0, 0, 128 / 255)
    assert db.imagePixelColor(imagePath, (2, 0)) == (0, 1, 0, 1)
    assert db.imagePixelColor(imagePath, (-1, 0)) is None


def test_numberOfPages_gif(tmpdir):
    source = """
for i in range(3):
    newPage(80, 80)
    fill(i / 2, 0, 1 - i / 2)
    rect(0, 0, width(), height())
"""
    outputPath = pathlib.Path(tmpdir) / "test.gif"
    db = Drawing()
    namespace = makeDrawbotNamespace(db)
    runScriptSource(source, "<string>", namespace)
    db.saveImage(outputPath)

    db = Drawing()
    assert db.numberOfPages(outputPath) == 3
    assert db.numberOfPages(pathlib.Path(tmpdir) / "test.png") is None


def test_multipleDocuments(tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    db = Drawing()
    db.newPage(100, 100)
    db.newPage(100, 100)
    db.saveImage(tmpdir / "test1.png")

    db.newDrawing()
    db.newPage(100, 100)
    db.newPage(100, 100)
    db.saveImage(tmpdir / "test2.png")

    fileNames = sorted(p.name for p in tmpdir.glob("*.png"))
    expectedFileNames = ["test1_0.png", "test1_1.png", "test2_0.png", "test2_1.png"]
    assert expectedFileNames == fileNames


def test_polygon_args():
    db = Drawing()
    db.polygon([0, 0], [0, 100], [100, 0])


def test_line_args():
    db = Drawing()
    db.line([0, 0], [0, 100])


def test_textBox_returns_overflow():
    db = Drawing()
    db.fontSize(20)
    db.lineHeight(24)
    overflow = db.textBox("one two three four five six", (0, 0, 80, 48))
    assert overflow
    assert "five" in overflow or "six" in overflow


def test_formattedString_properties():
    t = FormattedString("Hello", fontSize=20, cmykFill=(0, 1, 1, 0), align="center")
    assert str(t) == "Hello"
    assert t.textProperties()["fill"] == (255, 255, 0, 0)
    assert t.textProperties()["align"] == "center"
    assert t.size()[0] > 0
    assert t.size()[1] == pytest.approx(20)

    t.cmykFill(1, 0, 1, 0, 0.5)
    t.stroke(0, 0, 1)
    t.strokeWidth(2)
    t.align("right")
    t += " world"
    runText, runProperties = list(t._iterRuns())[-1]
    assert runText == " world"
    assert runProperties["fill"] == (128, 0, 255, 0)
    assert runProperties["stroke"] == (255, 0, 0, 255)
    assert runProperties["strokeWidth"] == 2
    assert runProperties["align"] == "right"

    t.cmykStroke(0, 1, 1, 0, 0.5)
    assert t.textProperties()["stroke"] == (128, 255, 0, 0)

    t.clear()
    assert str(t) == ""
    assert t.textProperties()["fill"] == (128, 0, 255, 0)
    assert t.textProperties()["stroke"] == (128, 255, 0, 0)


def test_cmyk_color_arguments():
    db = Drawing()
    db.cmykFill(0, 1, 1, 0)
    assert db._gstate.fillPaint.color == (255, 255, 0, 0)
    db.cmykFill((1, 0, 1, 0, 0.5))
    assert db._gstate.fillPaint.color == (128, 0, 255, 0)
    db.cmykFill(None)
    assert not db._gstate.fillPaint.somethingToDraw

    db.cmykStroke(1, 1, 0, 0)
    assert db._gstate.strokePaint.color == (255, 0, 0, 255)
    db.cmykStroke(None)
    assert not db._gstate.strokePaint.somethingToDraw


def test_bezier_path_dashStroke():
    path = BezierPath()
    path.moveTo((0, 0))
    path.lineTo((100, 0))
    dashed = path.dashStroke(10, 5)
    assert dashed is not path
    assert dashed.contours[0].open
    assert dashed.contours[0][0] == ((0.0, 0.0),)
    assert dashed.contours[0][1] == ((10.0, 0.0),)
    assert len(dashed.contours) == 7

    dashed = path.dashStroke(10, 5, offset=5)
    assert dashed.contours[0][1] == ((5.0, 0.0),)


def test_bezier_path_textBox_returns_overflow():
    path = BezierPath()
    overflow = path.textBox(
        "one two three four five six",
        (0, 0, 90, 48),
        fontSize=20,
    )
    assert overflow
    assert "five" in overflow or "six" in overflow
    assert path.bounds() is not None
    xMin, yMin, xMax, yMax = path.bounds()
    assert xMin >= 0
    assert yMin >= 0
    assert xMax <= 90
    assert yMax <= 48


def test_current_path_api():
    db = Drawing()
    db.newPath()
    db.moveTo((0, 0))
    db.lineTo((50, 0))
    db.qCurveTo((75, 25), (50, 50))
    db.closePath()
    assert len(db._path.contours) == 1
    assert not db._path.contours[0].open

    path = db._path
    db.newPath()
    assert db._path is not path


def test_save_restore_graphics_state():
    db = Drawing()
    db.newPage(100, 100)
    db.fill(1, 0, 0)
    db.save()
    db.fill(0, 1, 0)
    assert db._gstate.fillPaint.color == (255, 0, 255, 0)
    db.restore()
    assert db._gstate.fillPaint.color == (255, 255, 0, 0)
    with pytest.raises(DrawbotError):
        db.restore()


def readbytes(path):
    with open(path, "rb") as f:
        return f.read()


def compareImages(path1, path2):
    data1 = readbytes(path1)
    data2 = readbytes(path2)
    _, ext = os.path.splitext(path1)
    if ext == ".svg":
        # Ignore line endings for svg
        data1 = data1.splitlines()
        data2 = data2.splitlines()
    if data1 == data2:
        return True, "data identical"
    if ext not in {".png", ".jpg"}:
        return False, "image data differs"
    im1 = Image.open(path1)
    im2 = Image.open(path2)
    if im1 == im2:
        return True, "images identical"
    if im1.size != im2.size:
        return False, "sizes differ"
    a1 = np.array(im1).astype(int)
    a2 = np.array(im2).astype(int)
    diff = a1 - a2
    maxDiff = max(abs(np.max(diff)), abs(np.min(diff)))
    if maxDiff < 128:
        return True, "images similar enough"
    return False, f"images differ too much, maxDiff: {maxDiff}"
