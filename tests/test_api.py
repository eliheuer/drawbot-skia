import os
import math
import pathlib
import shutil
import sys
import pytest
from PIL import Image
from PIL import ImageDraw
import numpy as np
import drawbot_skia.drawbot as drawbot
from drawbot_skia.runner import makeDrawbotNamespace, runScript, runScriptSource
from drawbot_skia.drawing import Drawing
from drawbot_skia.errors import DrawbotError
from drawbot_skia.formattedString import FormattedString
from drawbot_skia.imageObject import ImageObject
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
    assert db.sizes("A4") == (595, 842)
    assert db.sizes("A4Landscape") == (842, 595)
    db.newDrawing()
    db.size("A5")
    assert (db.width(), db.height()) == (420, 595)
    db.newPage("LetterLandscape")
    assert (db.width(), db.height()) == (792, 612)


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


def test_imageObject():
    db = Drawing()
    imagePath = testDir / "images" / "drawbot.png"
    im = ImageObject(imagePath)
    assert im.size() == (512, 512)
    assert im.offset() == (0, 0)
    assert db.imageSize(im) == (512, 512)
    assert db.imagePixelColor(im, (128, 128)) == db.imagePixelColor(
        imagePath, (128, 128)
    )
    assert db.imageResolution(im) == (72, 72)
    im2 = im.copy()
    assert im2 is not im
    assert im2.size() == im.size()
    im2.gaussianBlur(radius=4)
    assert im2.offset() == (-12, -12)
    assert im2.size() == (536, 536)
    assert im.size() == (512, 512)
    im2.clearFilters()
    assert im2.offset() == (0, 0)
    assert im2.size() == (512, 512)
    originalColor = db.imagePixelColor(im, (128, 128))
    im2.colorInvert()
    invertedColor = db.imagePixelColor(im2, (128, 128))
    assert invertedColor[:3] != originalColor[:3]
    im2.clearFilters()
    im2.photoEffectMono()
    monoColor = db.imagePixelColor(im2, (128, 128))
    assert monoColor[0] == monoColor[1] == monoColor[2]
    im2.clearFilters()
    im2.sepiaTone(intensity=1)
    sepiaColor = db.imagePixelColor(im2, (128, 128))
    assert sepiaColor[0] >= sepiaColor[1] >= sepiaColor[2]
    im2.clearFilters()
    im2.boxBlur(radius=2)
    im2.colorControls(saturation=0.5, brightness=0.1, contrast=1.2)
    im2.sharpenLuminance()
    im2.photoEffectNoir()
    assert im2.size() == (512, 512)


def test_imageObject_pillow_filter_batch(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "filters.png"
    image = Image.new("RGBA", (20, 20), (20, 40, 80, 255))
    image.putpixel((10, 10), (200, 100, 50, 255))
    image.save(imagePath)

    im = ImageObject(imagePath)
    im.crop((2, 3, 10, 11))
    assert im.size() == (10, 11)
    assert im.offset() == (2, 3)
    im.lanczosScaleTransform(scale=2)
    assert im.size() == (20, 22)

    filterCalls = [
        ("gammaAdjust", (), {"power": 0.8}),
        ("exposureAdjust", (), {"EV": 1}),
        ("hueAdjust", (), {"angle": 45}),
        ("vibrance", (), {"amount": 0.4}),
        ("temperatureAndTint", (), {"targetNeutral": (7000, 10)}),
        ("whitePointAdjust", (), {"color": (0.8, 0.9, 1, 1)}),
        ("colorMonochrome", (), {}),
        ("falseColor", (), {}),
        ("colorPosterize", (), {"levels": 4}),
        ("minimumComponent", (), {}),
        ("maximumComponent", (), {}),
        ("maskToAlpha", (), {}),
        ("unsharpMask", (), {}),
        ("noiseReduction", (), {"noiseLevel": 0.02}),
        ("edges", (), {}),
        ("edgeWork", (), {}),
        ("pixellate", (), {"scale": 4}),
        ("motionBlur", (), {"radius": 2}),
        ("zoomBlur", (), {"amount": 5}),
        ("vignette", (), {"intensity": 0.2}),
        ("vignetteEffect", (), {"center": (10, 10), "radius": 8}),
        ("bloom", (), {}),
        ("gloom", (), {}),
        ("photoEffectTonal", (), {}),
        ("photoEffectFade", (), {}),
        ("photoEffectInstant", (), {}),
        ("photoEffectProcess", (), {}),
        ("photoEffectTransfer", (), {}),
        ("photoEffectChrome", (), {}),
    ]
    for methodName, args, kwargs in filterCalls:
        im = ImageObject(imagePath)
        assert getattr(im, methodName)(*args, **kwargs) is None
        assert im.size() == (20, 20)


def test_imageObject_photo_effects_use_extrapolate(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "photo-effects.png"
    image = Image.new("RGBA", (4, 3))
    for y in range(3):
        for x in range(4):
            image.putpixel((x, y), (40 + x * 45, 30 + y * 70, 80 + (x + y) * 25, 255))
    image.save(imagePath)

    expected = {
        "photoEffectMono": ((115, 115, 115, 255), (115, 115, 115, 255), 6918, 6903),
        "photoEffectNoir": ((119, 119, 119, 255), (122, 122, 122, 255), 6903, 6981),
        "photoEffectTonal": ((115, 115, 115, 255), (115, 115, 115, 255), 6918, 6903),
        "photoEffectFade": ((121, 105, 135, 255), (120, 106, 131, 255), 7075, 7044),
        "photoEffectInstant": ((131, 98, 114, 255), (131, 98, 103, 255), 6838, 6725),
        "photoEffectProcess": ((137, 92, 175, 255), (139, 91, 180, 255), 7392, 7461),
        "photoEffectTransfer": ((126, 100, 129, 255), (125, 100, 124, 255), 6988, 6929),
        "photoEffectChrome": ((143, 90, 187, 255), (146, 87, 196, 255), 7541, 7676),
    }
    for methodName, (normalPixel, extrapolatedPixel, normalSum, extrapolatedSum) in expected.items():
        normal = ImageObject(imagePath)
        assert getattr(normal, methodName)(extrapolate=False) is None
        normalImage = normal._pilImage()

        extrapolated = ImageObject(imagePath)
        assert getattr(extrapolated, methodName)(extrapolate=True) is None
        extrapolatedImage = extrapolated._pilImage()

        assert normalImage.getpixel((2, 1)) == normalPixel
        assert extrapolatedImage.getpixel((2, 1)) == extrapolatedPixel
        assert sum(normalImage.tobytes()) == normalSum
        assert sum(extrapolatedImage.tobytes()) == extrapolatedSum
        assert normalImage.tobytes() != extrapolatedImage.tobytes()


def test_imageObject_zoom_blur_uses_center(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "zoom-blur.png"
    image = Image.new("RGBA", (5, 1), (0, 0, 0, 255))
    image.putpixel((1, 0), (255, 255, 255, 255))
    image.save(imagePath)

    unchanged = ImageObject(imagePath)
    assert unchanged.zoomBlur(center=(0, 0), amount=0) is None
    assert unchanged._pilImage().tobytes() == image.tobytes()

    left = ImageObject(imagePath)
    assert left.zoomBlur(center=(0, 0), amount=200) is None
    assert [left._pilImage().getpixel((x, 0))[0] for x in range(5)] == [0, 89, 138, 143, 101]

    right = ImageObject(imagePath)
    assert right.zoomBlur(center=(4, 0), amount=200) is None
    assert [right._pilImage().getpixel((x, 0))[0] for x in range(5)] == [77, 54, 0, 0, 0]


def test_imageObject_blend_and_compositing_batch(tmpdir):
    sourcePath = pathlib.Path(tmpdir) / "source.png"
    backgroundPath = pathlib.Path(tmpdir) / "background.png"
    maskPath = pathlib.Path(tmpdir) / "mask.png"
    Image.new("RGBA", (12, 12), (200, 80, 40, 180)).save(sourcePath)
    Image.new("RGBA", (12, 12), (20, 100, 180, 255)).save(backgroundPath)
    mask = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    mask.putpixel((6, 6), (255, 255, 255, 255))
    mask.save(maskPath)

    blendCalls = [
        "additionCompositing",
        "maximumCompositing",
        "minimumCompositing",
        "multiplyCompositing",
        "multiplyBlendMode",
        "screenBlendMode",
        "overlayBlendMode",
        "hardLightBlendMode",
        "softLightBlendMode",
        "darkenBlendMode",
        "lightenBlendMode",
        "differenceBlendMode",
        "exclusionBlendMode",
        "colorBurnBlendMode",
        "colorDodgeBlendMode",
        "divideBlendMode",
        "linearBurnBlendMode",
        "linearDodgeBlendMode",
        "linearLightBlendMode",
        "pinLightBlendMode",
        "subtractBlendMode",
        "vividLightBlendMode",
        "hueBlendMode",
        "saturationBlendMode",
        "colorBlendMode",
        "luminosityBlendMode",
        "sourceOverCompositing",
        "sourceInCompositing",
        "sourceOutCompositing",
        "sourceAtopCompositing",
    ]
    for methodName in blendCalls:
        im = ImageObject(sourcePath)
        assert getattr(im, methodName)(ImageObject(backgroundPath)) is None
        assert im.size() == (12, 12)

    im = ImageObject(sourcePath)
    assert im.blendWithAlphaMask(backgroundPath, maskPath) is None
    assert im.size() == (12, 12)
    im = ImageObject(sourcePath)
    assert im.blendWithMask(backgroundPath, maskPath) is None
    assert im.size() == (12, 12)
    im = ImageObject(sourcePath)
    assert im.blendWithRedMask(backgroundPath, maskPath) is None
    assert im.size() == (12, 12)
    im = ImageObject(sourcePath)
    assert im.blendWithBlueMask(backgroundPath, maskPath) is None
    assert im.size() == (12, 12)


def test_imageObject_color_and_morphology_batch(tmpdir):
    sourcePath = pathlib.Path(tmpdir) / "source.png"
    otherPath = pathlib.Path(tmpdir) / "other.png"
    gradientPath = pathlib.Path(tmpdir) / "gradient.png"
    Image.new("RGBA", (12, 12), (80, 120, 200, 255)).save(sourcePath)
    Image.new("RGBA", (12, 12), (200, 80, 40, 255)).save(otherPath)
    gradient = Image.new("RGBA", (16, 1))
    for x in range(16):
        gradient.putpixel((x, 0), (x * 16, 0, 255 - x * 16, 255))
    gradient.save(gradientPath)
    calls = [
        ("colorClamp", (), {"minComponents": (0.1, 0.1, 0.1, 0), "maxComponents": (0.9, 0.9, 0.9, 1)}),
        ("colorMatrix", (), {"biasVector": (0.05, 0, 0, 0)}),
        ("colorPolynomial", (), {}),
        ("colorCrossPolynomial", (), {}),
        ("colorThreshold", (), {"threshold": 0.4}),
        ("colorThresholdOtsu", (), {}),
        ("colorAbsoluteDifference", (otherPath,), {}),
        ("colorMap", (gradientPath,), {}),
        ("convertRGBtoLab", (), {}),
        ("convertLabToRGB", (), {}),
        ("labDeltaE", (otherPath,), {}),
        ("spotColor", (), {}),
        ("mix", (otherPath,), {"amount": 0.5}),
        ("comicEffect", (), {}),
        ("XRay", (), {}),
        ("thermal", (), {}),
        ("dither", (), {"intensity": 0.5}),
        ("sampleNearest", (), {}),
        ("morphologyMaximum", (), {"radius": 1}),
        ("morphologyMinimum", (), {"radius": 1}),
        ("morphologyGradient", (), {"radius": 1}),
        ("morphologyRectangleMaximum", (), {"width": 3, "height": 5}),
        ("morphologyRectangleMinimum", (), {"width": 3, "height": 5}),
    ]
    for methodName, args, kwargs in calls:
        im = ImageObject(sourcePath)
        assert getattr(im, methodName)(*args, **kwargs) is None
        assert im.size() == (12, 12)


def test_imageObject_palette_filters(tmpdir):
    from drawbot_skia.imageObject import _getImageData

    sourcePath = pathlib.Path(tmpdir) / "palette-source.png"
    palettePath = pathlib.Path(tmpdir) / "palette.png"
    source = Image.new("RGBA", (4, 1))
    source.putdata(
        [
            (250, 0, 0, 255),
            (200, 0, 0, 255),
            (0, 0, 250, 255),
            (0, 0, 200, 255),
        ]
    )
    source.save(sourcePath)
    palette = Image.new("RGBA", (2, 1))
    palette.putdata([(255, 0, 0, 255), (0, 0, 255, 255)])
    palette.save(palettePath)

    kmeans = ImageObject(sourcePath)
    assert kmeans.KMeans(count=2) is None
    assert kmeans.size() == (2, 1)
    kmeansPixels = list(_getImageData(kmeans._pilImage()))
    assert {pixel[:3] for pixel in kmeansPixels} == {(225, 0, 0), (0, 0, 225)}
    assert sorted(pixel[3] for pixel in kmeansPixels) == [128, 128]

    palettized = ImageObject(sourcePath)
    assert palettized.palettize(palettePath) is None
    assert list(_getImageData(palettized._pilImage())) == [
        (255, 0, 0, 255),
        (255, 0, 0, 255),
        (0, 0, 255, 255),
        (0, 0, 255, 255),
    ]

    centroid = ImageObject(sourcePath)
    assert centroid.paletteCentroid(palettePath) is None
    assert centroid.size() == (2, 1)
    assert list(_getImageData(centroid._pilImage())) == [(225, 0, 0, 128), (0, 0, 225, 128)]


def test_imageObject_spot_color_contrast(tmpdir):
    from drawbot_skia.imageObject import _getImageData

    sourcePath = pathlib.Path(tmpdir) / "spot-source.png"
    image = Image.new("RGBA", (3, 1))
    image.putdata([(255, 0, 0, 255), (230, 0, 0, 255), (0, 0, 255, 128)])
    image.save(sourcePath)

    hard = ImageObject(sourcePath)
    assert hard.spotColor(
        centerColor1=(1, 0, 0, 1),
        replacementColor1=(0, 1, 0, 1),
        closeness1=0.06,
        contrast1=1,
        closeness2=0,
        closeness3=0,
    ) is None
    assert list(_getImageData(hard._pilImage())) == [
        (0, 255, 0, 255),
        (0, 255, 0, 255),
        (0, 0, 255, 128),
    ]

    soft = ImageObject(sourcePath)
    assert soft.spotColor(
        centerColor1=(1, 0, 0, 1),
        replacementColor1=(0, 1, 0, 1),
        closeness1=0.06,
        contrast1=0,
        closeness2=0,
        closeness3=0,
    ) is None
    softPixels = list(_getImageData(soft._pilImage()))
    assert softPixels[0] == (0, 255, 0, 255)
    assert 0 < softPixels[1][1] < 255
    assert softPixels[2] == (0, 0, 255, 128)


def test_imageObject_lab_conversion_and_delta_e(tmpdir):
    from drawbot_skia.imageObject import _labToBytes
    from drawbot_skia.imageObject import _rgbBytesToLab

    sourcePath = pathlib.Path(tmpdir) / "lab-source.png"
    samePath = pathlib.Path(tmpdir) / "lab-same.png"
    otherPath = pathlib.Path(tmpdir) / "lab-other.png"
    image = Image.new("RGBA", (2, 1))
    image.putdata([(255, 0, 0, 255), (80, 120, 200, 128)])
    image.save(sourcePath)
    image.save(samePath)
    Image.new("RGBA", (2, 1), (0, 255, 0, 255)).save(otherPath)

    im = ImageObject(sourcePath)
    assert im.convertRGBtoLab() is None
    labImage = im._pilImage()
    assert labImage.getpixel((0, 0)) == (*_labToBytes(*_rgbBytesToLab(255, 0, 0)), 255)
    assert labImage.getpixel((1, 0))[3] == 128

    assert im.convertLabToRGB() is None
    roundTripped = im._pilImage()
    assert roundTripped.getpixel((0, 0))[:3] == (255, 2, 1)
    assert all(abs(a - b) <= 5 for a, b in zip(roundTripped.getpixel((1, 0))[:3], (80, 120, 200)))
    assert roundTripped.getpixel((1, 0))[3] == 128

    same = ImageObject(sourcePath)
    assert same.labDeltaE(samePath) is None
    assert same._pilImage().getpixel((0, 0)) == (0, 0, 0, 255)

    different = ImageObject(sourcePath)
    assert different.labDeltaE(otherPath) is None
    assert different._pilImage().getpixel((0, 0))[0] > 100


def test_imageObject_kmeans_uses_passes_and_perceptual_distance():
    from drawbot_skia.imageObject import _getImageData

    source = Image.new("RGBA", (6, 1))
    source.putdata(
        [
            (20, 20, 20, 255),
            (40, 40, 40, 255),
            (200, 30, 30, 255),
            (220, 50, 50, 255),
            (30, 200, 30, 255),
            (50, 220, 50, 255),
        ]
    )

    initial = ImageObject()
    initial._setPILImage(source)
    assert initial.KMeans(count=2, passes=0) is None
    assert list(_getImageData(initial._pilImage())) == [
        (110, 26, 26, 170),
        (84, 129, 42, 85),
    ]

    refined = ImageObject()
    refined._setPILImage(source)
    assert refined.KMeans(count=2, passes=1) is None
    assert list(_getImageData(refined._pilImage())) == [
        (120, 34, 34, 170),
        (39, 210, 39, 85),
    ]

    hueRows = Image.new("RGBA", (6, 1))
    hueRows.putdata(
        [
            (255, 0, 0, 255),
            (255, 80, 0, 255),
            (255, 160, 0, 255),
            (0, 0, 255, 255),
            (0, 80, 255, 255),
            (0, 160, 255, 255),
        ]
    )

    rgbDistance = ImageObject()
    rgbDistance._setPILImage(hueRows)
    assert rgbDistance.KMeans(count=2, passes=3, perceptual=False) is None
    assert list(_getImageData(rgbDistance._pilImage())) == [
        (128, 120, 128, 170),
        (129, 0, 129, 85),
    ]

    perceptualDistance = ImageObject()
    perceptualDistance._setPILImage(hueRows)
    assert perceptualDistance.KMeans(count=2, passes=3, perceptual=True) is None
    assert list(_getImageData(perceptualDistance._pilImage())) == [
        (255, 80, 0, 128),
        (0, 80, 255, 128),
    ]


def test_imageObject_generator_batch():
    calls = [
        ("constantColorGenerator", ((16, 12),), {}),
        ("checkerboardGenerator", ((16, 12),), {"width": 4}),
        ("stripesGenerator", ((16, 12),), {"width": 4}),
        ("randomGenerator", ((16, 12),), {}),
        ("linearGradient", ((16, 12),), {}),
        ("smoothLinearGradient", ((16, 12),), {}),
        ("radialGradient", ((16, 12),), {}),
        ("gaussianGradient", ((16, 12),), {}),
        ("roundedRectangleGenerator", ((16, 12),), {"extent": (2, 2, 10, 8)}),
        ("roundedRectangleStrokeGenerator", ((16, 12),), {"extent": (2, 2, 10, 8)}),
        ("blurredRectangleGenerator", ((16, 12),), {"extent": (2, 2, 10, 8), "sigma": 1}),
        ("QRCodeGenerator", ((16, 12), "drawbot"), {}),
        ("aztecCodeGenerator", ((16, 12), "drawbot"), {}),
        ("PDF417BarcodeGenerator", ((16, 12), "drawbot"), {}),
        ("code128BarcodeGenerator", ((16, 12), "drawbot"), {}),
        ("lenticularHaloGenerator", ((16, 12),), {"center": (8, 6), "haloRadius": 4, "haloWidth": 6}),
        ("starShineGenerator", ((16, 12),), {"center": (8, 6), "radius": 3}),
        ("sunbeamsGenerator", ((16, 12),), {"center": (8, 6), "sunRadius": 3}),
        ("meshGenerator", ((16, 12),), {"width": 4}),
    ]
    for methodName, args, kwargs in calls:
        im = ImageObject()
        assert getattr(im, methodName)(*args, **kwargs) is None
        assert im.size() == (16, 12)
        assert im.offset() == (0, 0)


def test_imageObject_checkerboard_and_stripes_use_sharpness():
    hardChecker = ImageObject()
    assert hardChecker.checkerboardGenerator((5, 3), center=(0.5, 0.5), width=2, sharpness=1) is None
    assert [[hardChecker._pilImage().getpixel((x, y))[0] for x in range(5)] for y in range(3)] == [
        [255, 0, 0, 255, 255],
        [0, 255, 255, 0, 0],
        [0, 255, 255, 0, 0],
    ]

    softChecker = ImageObject()
    assert softChecker.checkerboardGenerator((5, 3), center=(0.5, 0.5), width=2, sharpness=0) is None
    assert [[softChecker._pilImage().getpixel((x, y))[0] for x in range(5)] for y in range(3)] == [
        [191, 64, 64, 191, 191],
        [64, 191, 191, 64, 64],
        [64, 191, 191, 64, 64],
    ]

    hardStripes = ImageObject()
    assert hardStripes.stripesGenerator((5, 1), center=(0.5, 0), width=2, sharpness=1) is None
    assert [hardStripes._pilImage().getpixel((x, 0))[0] for x in range(5)] == [0, 255, 255, 0, 0]

    softStripes = ImageObject()
    assert softStripes.stripesGenerator((5, 1), center=(0.5, 0), width=2, sharpness=0) is None
    assert [softStripes._pilImage().getpixel((x, 0))[0] for x in range(5)] == [64, 191, 191, 64, 64]


def test_imageObject_qr_code_generator():
    from drawbot_skia.imageObject import _qrInterleavedCodewords
    from drawbot_skia.imageObject import _qrMatrix

    im = ImageObject()
    assert im.QRCodeGenerator((128, 128), "drawbot", correctionLevel="M") is None
    image = im._pilImage()
    assert image.size == (128, 128)

    expectedCodewords = [
        64,
        118,
        71,
        38,
        23,
        118,
        38,
        247,
        64,
        236,
        17,
        236,
        17,
        236,
        17,
        236,
        231,
        145,
        143,
        230,
        229,
        168,
        58,
        201,
        12,
        27,
    ]
    dataCodewords = expectedCodewords[:16]
    assert _qrInterleavedCodewords(1, "M", dataCodewords) == expectedCodewords

    expectedMatrix = [
        "111111101011001111111",
        "100000100101101000001",
        "101110100111101011101",
        "101110101010101011101",
        "101110101010101011101",
        "100000101001001000001",
        "111111101010101111111",
        "000000001001100000000",
        "100010111111011111001",
        "111011010111100000100",
        "101011101101001111110",
        "010110011010011110000",
        "001010111010111100001",
        "000000001110111110110",
        "111111101100110010010",
        "100000100011100000011",
        "101110101101001111001",
        "101110100011100011111",
        "101110100101001010100",
        "100000100100011100000",
        "111111101000111000001",
    ]
    assert ["".join("1" if value else "0" for value in row) for row in _qrMatrix("drawbot", "M")] == expectedMatrix


def test_imageObject_sunbeams_generator_uses_striation_parameters():
    smooth = ImageObject()
    assert smooth.sunbeamsGenerator(
        (7, 7),
        center=(3, 3),
        color=(1, 1, 1, 1),
        sunRadius=2,
        maxStriationRadius=1,
        striationStrength=0,
        striationContrast=1,
        time=0,
    ) is None
    assert [smooth._pilImage().getpixel((x, 3))[0] for x in range(7)] == [219, 255, 219, 182, 219, 255, 219]

    striated = ImageObject()
    assert striated.sunbeamsGenerator(
        (7, 7),
        center=(3, 3),
        color=(1, 1, 1, 1),
        sunRadius=2,
        maxStriationRadius=3,
        striationStrength=1,
        striationContrast=2,
        time=0,
    ) is None
    assert [striated._pilImage().getpixel((x, 3))[0] for x in range(7)] == [56, 64, 56, 44, 56, 64, 56]

    shifted = ImageObject()
    assert shifted.sunbeamsGenerator(
        (7, 7),
        center=(3, 3),
        color=(1, 1, 1, 1),
        sunRadius=2,
        maxStriationRadius=3,
        striationStrength=1,
        striationContrast=2,
        time=0.25,
    ) is None
    assert shifted._pilImage().tobytes() != striated._pilImage().tobytes()


def test_imageObject_lenticular_halo_generator_uses_overlap_and_striations():
    narrow = ImageObject()
    assert narrow.lenticularHaloGenerator(
        (7, 7),
        center=(3, 3),
        color=(1, 1, 1, 1),
        haloRadius=2,
        haloWidth=1,
        haloOverlap=0,
        striationStrength=0,
        striationContrast=1,
        time=0,
    ) is None
    assert [narrow._pilImage().getpixel((x, 3))[0] for x in range(7)] == [0, 255, 0, 0, 0, 255, 0]

    wide = ImageObject()
    assert wide.lenticularHaloGenerator(
        (7, 7),
        center=(3, 3),
        color=(1, 1, 1, 1),
        haloRadius=2,
        haloWidth=1,
        haloOverlap=1,
        striationStrength=0,
        striationContrast=1,
        time=0,
    ) is None
    assert [wide._pilImage().getpixel((x, 3))[0] for x in range(7)] == [128, 255, 128, 0, 128, 255, 128]

    striated = ImageObject()
    assert striated.lenticularHaloGenerator(
        (7, 7),
        center=(3, 3),
        color=(1, 1, 1, 1),
        haloRadius=2,
        haloWidth=1,
        haloOverlap=0,
        striationStrength=1,
        striationContrast=2,
        time=0,
    ) is None
    assert [striated._pilImage().getpixel((x, 3))[0] for x in range(7)] == [0, 64, 0, 0, 0, 64, 0]

    shifted = ImageObject()
    assert shifted.lenticularHaloGenerator(
        (7, 7),
        center=(3, 3),
        color=(1, 1, 1, 1),
        haloRadius=2,
        haloWidth=1,
        haloOverlap=0,
        striationStrength=1,
        striationContrast=2,
        time=0.25,
    ) is None
    assert shifted._pilImage().tobytes() != striated._pilImage().tobytes()


def test_imageObject_star_shine_generator_uses_cross_opacity_and_epsilon():
    opaque = ImageObject()
    assert opaque.starShineGenerator(
        (9, 9),
        center=(4, 4),
        color=(1, 1, 1, 1),
        radius=1,
        crossScale=4,
        crossAngle=0,
        crossOpacity=0,
        crossWidth=1,
        epsilon=0,
    ) is None
    assert [opaque._pilImage().getpixel((x, 4))[3] for x in range(9)] == [252, 252, 252, 255, 255, 252, 252, 252, 252]

    dim = ImageObject()
    assert dim.starShineGenerator(
        (9, 9),
        center=(4, 4),
        color=(1, 1, 1, 1),
        radius=1,
        crossScale=4,
        crossAngle=0,
        crossOpacity=-3,
        crossWidth=1,
        epsilon=0,
    ) is None
    assert [dim._pilImage().getpixel((x, 4))[3] for x in range(9)] == [32, 32, 32, 32, 32, 32, 32, 32, 32]

    soft = ImageObject()
    assert soft.starShineGenerator(
        (9, 9),
        center=(4, 4),
        color=(1, 1, 1, 1),
        radius=1,
        crossScale=4,
        crossAngle=0,
        crossOpacity=0,
        crossWidth=1,
        epsilon=-4,
    ) is None
    assert soft._pilImage().getpixel((0, 3))[3] > opaque._pilImage().getpixel((0, 3))[3]
    assert soft._pilImage().tobytes() != opaque._pilImage().tobytes()


def test_imageObject_pdf417_barcode_generator():
    import pdf417gen

    im = ImageObject()
    assert im.PDF417BarcodeGenerator((180, 60), "drawbot", dataColumns=4, correctionLevel=2) is None
    image = im._pilImage()
    assert image.size == (180, 60)

    expectedCodes = [
        [130728, 125680, 108640, 66956, 113056, 124742, 120032, 260649],
        [130728, 128280, 102516, 97968, 97968, 97968, 129720, 260649],
        [130728, 109040, 118606, 126452, 85054, 80140, 108792, 260649],
        [130728, 89720, 90504, 73858, 85088, 69008, 89980, 260649],
    ]
    assert pdf417gen.encode("drawbot", columns=4, security_level=2) == expectedCodes
    assert image.getbbox() == (0, 0, 180, 60)
    assert any(image.getpixel((x, image.height // 2))[:3] == (0, 0, 0) for x in range(image.width))


def test_imageObject_aztec_code_generator():
    from aztec_code_generator import AztecCode

    im = ImageObject()
    assert im.aztecCodeGenerator((120, 120), "drawbot", correctionLevel=23) is None
    image = im._pilImage()
    assert image.size == (120, 120)

    expectedMatrix = [
        "001100011010110",
        "110111100011101",
        "101100000110111",
        "001111111111101",
        "010100000001011",
        "011101111101100",
        "101101000101100",
        "010101010101111",
        "100101000101100",
        "000101111101110",
        "101100000001010",
        "110111111111111",
        "000011110110011",
        "001001111111011",
        "001100001000111",
    ]
    matrix = AztecCode("drawbot").matrix
    assert ["".join("1" if value else "0" for value in row) for row in matrix] == expectedMatrix
    assert any(image.getpixel((x, image.height // 2))[:3] == (0, 0, 0) for x in range(image.width))


def test_imageObject_code128_barcode_generator():
    from drawbot_skia.imageObject import _CODE128_PATTERNS

    im = ImageObject()
    assert im.code128BarcodeGenerator((220, 40), "ABC", quietSpace=10, barcodeHeight=20) is None
    image = im._pilImage()
    assert image.size == (220, 40)

    codes = [104, ord("A") - 32, ord("B") - 32, ord("C") - 32]
    checksum = (104 + sum(index * code for index, code in enumerate(codes[1:], start=1))) % 103
    expectedPattern = "".join(_CODE128_PATTERNS[code] for code in [*codes, checksum, 106])
    assert expectedPattern.startswith("11010010000")
    moduleWidth = 200 / len(expectedPattern)
    sampled = ""
    for index in range(len(expectedPattern)):
        x = int(round(10 + (index + 0.5) * moduleWidth))
        sampled += "1" if image.getpixel((x, 20))[:3] == (0, 0, 0) else "0"
    assert sampled == expectedPattern


def test_imageObject_keystone_combined_uses_focal_length(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "keystone.png"
    image = Image.new("RGBA", (6, 4))
    for y in range(4):
        for x in range(6):
            image.putpixel((x, y), (x * 30, y * 60, (x + y) * 20, 255))
    image.save(imagePath)

    kwargs = {
        "topLeft": (0, 0),
        "topRight": (6, 1),
        "bottomRight": (5, 4),
        "bottomLeft": (1, 3),
    }
    outputs = {}
    for focalLength in (14, 28, 56):
        im = ImageObject(imagePath)
        assert im.keystoneCorrectionCombined(focalLength=focalLength, **kwargs) is None
        outputs[focalLength] = im._pilImage()

    assert [outputs[14].getpixel((x, 0))[0] for x in range(6)] == [8, 14, 23, 36, 43, 46]
    assert [outputs[28].getpixel((x, 0))[0] for x in range(6)] == [7, 9, 12, 16, 20, 26]
    assert [outputs[56].getpixel((x, 0))[0] for x in range(6)] == [6, 7, 9, 10, 11, 13]
    assert outputs[14].tobytes() != outputs[28].tobytes()
    assert outputs[28].tobytes() != outputs[56].tobytes()


def test_imageObject_simple_geometry_batch(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "geometry.png"
    texturePath = pathlib.Path(tmpdir) / "texture.png"
    image = Image.new("RGBA", (20, 12), (120, 80, 40, 255))
    for x in range(20):
        image.putpixel((x, x % 12), (220, 40, 120, 255))
    image.save(imagePath)
    Image.new("RGBA", (20, 12), (80, 160, 200, 255)).save(texturePath)

    im = ImageObject(imagePath)
    assert im.clamp((2, 3, 10, 6)) is None
    assert im.size() == (10, 6)
    assert im.offset() == (2, 3)

    calls = [
        ("affineClamp", (), {}),
        ("affineTile", (), {}),
        ("straightenFilter", (), {"angle": 0.2}),
        ("stretchCrop", (), {"size": (16, 16)}),
        ("perspectiveTransform", (), {"topLeft": (0, 0), "topRight": (20, 1), "bottomRight": (19, 12), "bottomLeft": (1, 11)}),
        ("perspectiveTransformWithExtent", (), {"extent": (0, 0, 20, 12), "topLeft": (0, 0), "topRight": (20, 1), "bottomRight": (19, 12), "bottomLeft": (1, 11)}),
        ("perspectiveCorrection", (), {"topLeft": (0, 0), "topRight": (20, 1), "bottomRight": (19, 12), "bottomLeft": (1, 11)}),
        ("perspectiveTile", (), {"topLeft": (0, 0), "topRight": (20, 1), "bottomRight": (19, 12), "bottomLeft": (1, 11)}),
        ("perspectiveRotate", (), {"pitch": 5, "yaw": 5, "roll": 5}),
        ("keystoneCorrectionCombined", (), {"topLeft": (0, 0), "topRight": (20, 1), "bottomRight": (19, 12), "bottomLeft": (1, 11)}),
        ("keystoneCorrectionHorizontal", (), {}),
        ("keystoneCorrectionVertical", (), {}),
        ("bumpDistortion", (), {"center": (10, 6), "radius": 8, "scale": 0.4}),
        ("bumpDistortionLinear", (), {"center": (10, 6), "radius": 8, "angle": 15, "scale": 0.4}),
        ("circleSplashDistortion", (), {"center": (10, 6), "radius": 6}),
        ("circularWrap", (), {"center": (10, 6), "radius": 8, "angle": 15}),
        ("glassLozenge", (), {"point0": (5, 6), "point1": (15, 6), "radius": 4}),
        ("holeDistortion", (), {"center": (10, 6), "radius": 8}),
        ("pinchDistortion", (), {"center": (10, 6), "radius": 8, "scale": 0.4}),
        ("torusLensDistortion", (), {"center": (10, 6), "radius": 5, "width": 3}),
        ("twirlDistortion", (), {"center": (10, 6), "radius": 8, "angle": 15}),
        ("vortexDistortion", (), {"center": (10, 6), "radius": 8, "angle": 15}),
        ("displacementDistortion", (texturePath,), {"scale": 3}),
        ("glassDistortion", (texturePath,), {"scale": 3}),
        ("droste", (), {"insetPoint0": (4, 3), "insetPoint1": (16, 9)}),
        ("lightTunnel", (), {"center": (10, 6), "radius": 8}),
        ("ninePartStretched", (), {"growAmount": (4, 4)}),
        ("ninePartTiled", (), {"growAmount": (4, 4)}),
    ]
    for methodName, args, kwargs in calls:
        im = ImageObject(imagePath)
        assert getattr(im, methodName)(*args, **kwargs) is None
        width, height = im.size()
        assert width > 0
        assert height > 0

    tileCalls = [
        ("kaleidoscope", (), {"count": 4}),
        ("triangleKaleidoscope", (), {"size": 10}),
        ("fourfoldReflectedTile", (), {"width": 8}),
        ("fourfoldRotatedTile", (), {"width": 8}),
        ("fourfoldTranslatedTile", (), {"width": 8}),
        ("glideReflectedTile", (), {"width": 8}),
        ("eightfoldReflectedTile", (), {"width": 8}),
        ("sixfoldReflectedTile", (), {"width": 8}),
        ("sixfoldRotatedTile", (), {"width": 8}),
        ("twelvefoldReflectedTile", (), {"width": 8}),
        ("triangleTile", (), {"width": 8}),
        ("parallelogramTile", (), {"width": 8}),
        ("opTile", (), {"width": 8}),
    ]
    for methodName, args, kwargs in tileCalls:
        im = ImageObject(imagePath)
        assert getattr(im, methodName)(*args, **kwargs) is None
        assert im.size() == (20, 12)


def test_imageObject_nine_part_geometry_preserves_regions(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "nine-part.png"
    image = Image.new("RGBA", (4, 4), (0, 0, 0, 255))
    rows = [
        [(255, 0, 0, 255), (220, 0, 0, 255), (180, 0, 0, 255), (140, 0, 0, 255)],
        [(0, 255, 0, 255), (10, 20, 30, 255), (40, 50, 60, 255), (0, 180, 0, 255)],
        [(0, 0, 255, 255), (70, 80, 90, 255), (100, 110, 120, 255), (0, 0, 180, 255)],
        [(255, 255, 0, 255), (220, 220, 0, 255), (180, 180, 0, 255), (140, 140, 0, 255)],
    ]
    for y, row in enumerate(rows):
        for x, color in enumerate(row):
            image.putpixel((x, y), color)
    image.save(imagePath)

    stretched = ImageObject(imagePath)
    assert stretched.ninePartStretched(breakpoint0=(1, 1), breakpoint1=(3, 3), growAmount=(2, 2)) is None
    stretchedImage = stretched._pilImage()
    assert stretchedImage.size == (6, 6)
    assert stretchedImage.getpixel((0, 0)) == rows[0][0]
    assert stretchedImage.getpixel((5, 0)) == rows[0][3]
    assert stretchedImage.getpixel((0, 5)) == rows[3][0]
    assert stretchedImage.getpixel((5, 5)) == rows[3][3]

    tiled = ImageObject(imagePath)
    assert tiled.ninePartTiled(
        breakpoint0=(1, 1),
        breakpoint1=(3, 3),
        growAmount=(2, 2),
        flipYTiles=False,
    ) is None
    tiledImage = tiled._pilImage()
    assert tiledImage.size == (6, 6)
    assert [tiledImage.getpixel((x, 1)) for x in range(1, 5)] == [
        rows[1][1],
        rows[1][2],
        rows[1][1],
        rows[1][2],
    ]
    assert [tiledImage.getpixel((x, 2)) for x in range(1, 5)] == [
        rows[2][1],
        rows[2][2],
        rows[2][1],
        rows[2][2],
    ]
    assert tiledImage.getpixel((0, 0)) == rows[0][0]
    assert tiledImage.getpixel((5, 5)) == rows[3][3]


def test_imageObject_stretch_crop_uses_crop_and_center_stretch(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "stretch-crop.png"
    image = Image.new("RGBA", (6, 2))
    for y in range(2):
        for x in range(6):
            image.putpixel((x, y), (x * 40, y * 100, 0, 255))
    image.save(imagePath)

    stretched = ImageObject(imagePath)
    assert stretched.stretchCrop(size=(4, 2), cropAmount=0, centerStretchAmount=1) is None
    cropped = ImageObject(imagePath)
    assert cropped.stretchCrop(size=(4, 2), cropAmount=1, centerStretchAmount=1) is None
    narrowCenter = ImageObject(imagePath)
    assert narrowCenter.stretchCrop(size=(8, 2), cropAmount=0, centerStretchAmount=0.25) is None
    wideCenter = ImageObject(imagePath)
    assert wideCenter.stretchCrop(size=(8, 2), cropAmount=0, centerStretchAmount=0.75) is None

    assert [stretched._pilImage().getpixel((x, 0))[0] for x in range(4)] == [12, 68, 132, 188]
    assert [cropped._pilImage().getpixel((x, 0))[0] for x in range(4)] == [40, 80, 120, 160]
    assert [narrowCenter._pilImage().getpixel((x, 0))[0] for x in range(8)] == [0, 40, 76, 88, 112, 124, 160, 200]
    assert [wideCenter._pilImage().getpixel((x, 0))[0] for x in range(8)] == [0, 37, 56, 87, 113, 144, 163, 200]
    assert stretched._pilImage().tobytes() != cropped._pilImage().tobytes()
    assert narrowCenter._pilImage().tobytes() != wideCenter._pilImage().tobytes()


def test_imageObject_affine_tile_wraps_transformed_samples(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "affine-tile.png"
    image = Image.new("RGBA", (4, 1))
    for x, color in enumerate([(10, 0, 0, 255), (20, 0, 0, 255), (30, 0, 0, 255), (40, 0, 0, 255)]):
        image.putpixel((x, 0), color)
    image.save(imagePath)

    shifted = ImageObject(imagePath)
    assert shifted.affineTile(transform=(1, 0, 0, 1, 1, 0)) is None
    assert [shifted._pilImage().getpixel((x, 0))[0] for x in range(4)] == [20, 30, 40, 10]

    reverse = ImageObject(imagePath)
    assert reverse.affineTile(transform=(1, 0, 0, 1, -1, 0)) is None
    assert [reverse._pilImage().getpixel((x, 0))[0] for x in range(4)] == [40, 10, 20, 30]


def test_imageObject_tile_filters_use_center(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "tile-center.png"
    image = Image.new("RGBA", (5, 5), (0, 0, 0, 255))
    image.putpixel((0, 2), (255, 0, 0, 255))
    image.save(imagePath)

    centered = ImageObject(imagePath)
    assert centered.fourfoldRotatedTile(center=(2, 2)) is None
    offCenter = ImageObject(imagePath)
    assert offCenter.fourfoldRotatedTile(center=(0, 2)) is None

    centeredImage = centered._pilImage()
    offCenterImage = offCenter._pilImage()
    assert centeredImage.getpixel((1, 0)) == (255, 0, 0, 255)
    assert centeredImage.getpixel((3, 1)) == (255, 0, 0, 255)
    assert offCenterImage.getpixel((0, 1)) == (255, 0, 0, 255)
    assert offCenterImage.getpixel((1, 0)) == (0, 0, 0, 255)
    assert centeredImage.tobytes() != offCenterImage.tobytes()


def test_imageObject_rotated_tile_uses_width(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "tile-width.png"
    image = Image.new("RGBA", (7, 5), (0, 0, 0, 255))
    for y in range(5):
        for x in range(7):
            image.putpixel((x, y), (x * 30, y * 40, 0, 255))
    image.save(imagePath)

    narrow = ImageObject(imagePath)
    assert narrow.fourfoldRotatedTile(center=(3, 2), angle=0, width=2) is None
    wide = ImageObject(imagePath)
    assert wide.fourfoldRotatedTile(center=(3, 2), angle=0, width=6) is None

    narrowImage = narrow._pilImage()
    wideImage = wide._pilImage()
    assert [narrowImage.getpixel((x, 2))[0] for x in range(7)] == [135, 105, 75, 75, 105, 135, 165]
    assert [wideImage.getpixel((x, 2))[0] for x in range(7)] == [105, 120, 120, 120, 120, 120, 135]
    assert narrowImage.tobytes() != wideImage.tobytes()


def test_imageObject_fourfold_and_parallelogram_tiles_use_phase_controls(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "tile-phase.png"
    image = Image.new("RGBA", (6, 4))
    for y in range(4):
        for x in range(6):
            image.putpixel((x, y), (x * 30, y * 60, 0, 255))
    image.save(imagePath)

    rightAngle = ImageObject(imagePath)
    assert rightAngle.fourfoldTranslatedTile(center=(3, 2), angle=0, width=4, acuteAngle=math.pi / 2) is None
    acute = ImageObject(imagePath)
    assert acute.fourfoldTranslatedTile(center=(3, 2), angle=0, width=4, acuteAngle=math.pi / 4) is None
    offCenter = ImageObject(imagePath)
    assert offCenter.fourfoldTranslatedTile(center=(0, 0), angle=0, width=4, acuteAngle=math.pi / 2) is None
    reflected = ImageObject(imagePath)
    assert reflected.fourfoldReflectedTile(center=(3, 2), angle=0, width=4, acuteAngle=math.pi / 4) is None
    parallelogram = ImageObject(imagePath)
    assert parallelogram.parallelogramTile(center=(0, 2), angle=0, acuteAngle=0.8, width=4) is None

    assert [rightAngle._pilImage().getpixel((x, 0))[0] for x in range(6)] == [75, 105, 22, 52, 82, 112]
    assert [acute._pilImage().getpixel((x, 0))[0] for x in range(6)] == [97, 82, 90, 30, 60, 90]
    assert [offCenter._pilImage().getpixel((x, 0))[0] for x in range(6)] == [52, 82, 112, 75, 105, 22]
    assert [reflected._pilImage().getpixel((x, 1))[1] for x in range(6)] == [75, 135, 75, 75, 135, 75]
    assert [parallelogram._pilImage().getpixel((x, 1))[1] for x in range(6)] == [60, 60, 60, 60, 60, 60]
    assert rightAngle._pilImage().tobytes() != acute._pilImage().tobytes()
    assert rightAngle._pilImage().tobytes() != offCenter._pilImage().tobytes()


def test_imageObject_triangle_kaleidoscope_uses_size_and_decay(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "triangle-kaleidoscope.png"
    image = Image.new("RGBA", (7, 7), (0, 0, 0, 255))
    for y in range(7):
        for x in range(7):
            image.putpixel((x, y), (x * 30, y * 30, (x + y) * 15, 255))
    image.save(imagePath)

    small = ImageObject(imagePath)
    assert small.triangleKaleidoscope(point=(3, 3), size=3, rotation=0, decay=1) is None
    large = ImageObject(imagePath)
    assert large.triangleKaleidoscope(point=(3, 3), size=7, rotation=0, decay=1) is None
    faded = ImageObject(imagePath)
    assert faded.triangleKaleidoscope(point=(3, 3), size=7, rotation=0, decay=0.25) is None

    assert [small._pilImage().getpixel((x, 3))[0] for x in range(7)] == [108, 99, 94, 90, 105, 117, 123]
    assert [large._pilImage().getpixel((x, 3))[0] for x in range(7)] == [128, 108, 98, 90, 120, 150, 180]
    assert [faded._pilImage().getpixel((x, 3))[0] for x in range(7)] == [8, 30, 60, 90, 120, 150, 180]
    assert small._pilImage().tobytes() != large._pilImage().tobytes()
    assert large._pilImage().tobytes() != faded._pilImage().tobytes()


def test_imageObject_displacement_distortion_uses_red_green_channels(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "displacement.png"
    displacementPath = pathlib.Path(tmpdir) / "displacement-map.png"
    image = Image.new("RGBA", (4, 3))
    for y in range(3):
        for x in range(4):
            image.putpixel((x, y), (x * 50, y * 80, 0, 255))
    image.save(imagePath)

    Image.new("RGBA", (4, 3), (255, 128, 0, 255)).save(displacementPath)
    horizontal = ImageObject(imagePath)
    assert horizontal.displacementDistortion(displacementPath, scale=1) is None
    assert [horizontal._pilImage().getpixel((x, 1)) for x in range(4)] == [
        (50, 80, 0, 255),
        (100, 80, 0, 255),
        (150, 80, 0, 255),
        (150, 80, 0, 255),
    ]

    Image.new("RGBA", (4, 3), (128, 255, 0, 255)).save(displacementPath)
    vertical = ImageObject(imagePath)
    assert vertical.displacementDistortion(displacementPath, scale=1) is None
    assert [vertical._pilImage().getpixel((1, y)) for y in range(3)] == [
        (50, 80, 0, 255),
        (50, 160, 0, 255),
        (50, 160, 0, 255),
    ]


def test_imageObject_glass_distortion_uses_centered_texture(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "glass.png"
    texturePath = pathlib.Path(tmpdir) / "glass-texture.png"
    image = Image.new("RGBA", (5, 1))
    for x in range(5):
        image.putpixel((x, 0), (x * 50, 0, 0, 255))
    image.save(imagePath)

    texture = Image.new("RGBA", (3, 1))
    for x, color in enumerate([(0, 128, 0, 255), (128, 128, 0, 255), (255, 128, 0, 255)]):
        texture.putpixel((x, 0), color)
    texture.save(texturePath)

    centered = ImageObject(imagePath)
    assert centered.glassDistortion(texturePath, center=(0, 0), scale=1) is None
    assert [centered._pilImage().getpixel((x, 0)) for x in range(5)] == [
        (0, 0, 0, 255),
        (100, 0, 0, 255),
        (50, 0, 0, 255),
        (150, 0, 0, 255),
        (200, 0, 0, 255),
    ]

    shifted = ImageObject(imagePath)
    assert shifted.glassDistortion(texturePath, center=(1, 0), scale=1) is None
    assert [shifted._pilImage().getpixel((x, 0)) for x in range(5)] == [
        (0, 0, 0, 255),
        (50, 0, 0, 255),
        (150, 0, 0, 255),
        (100, 0, 0, 255),
        (200, 0, 0, 255),
    ]


def test_imageObject_droste_uses_inset_and_recursion_parameters(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "droste.png"
    image = Image.new("RGBA", (6, 6), (0, 0, 0, 255))
    for y in range(6):
        for x in range(6):
            image.putpixel((x, y), (x * 30, y * 30, 0, 255))
    image.save(imagePath)

    im = ImageObject(imagePath)
    assert im.droste(insetPoint0=(1, 1), insetPoint1=(5, 5), periodicity=1, zoom=1, rotation=0, strands=1) is None
    assert im.size() == (6, 6)
    assert [im._pilImage().getpixel((x, 1))[:3] for x in range(6)] == [
        (0, 30, 0),
        (9, 9, 0),
        (51, 9, 0),
        (99, 9, 0),
        (141, 9, 0),
        (150, 30, 0),
    ]
    assert im._pilImage().getpixel((0, 0))[:3] == (0, 0, 0)


def test_imageObject_perspective_correction_crop_flag(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "perspective-correction.png"
    Image.new("RGBA", (4, 3), (100, 0, 0, 255)).save(imagePath)
    kwargs = {
        "topLeft": (-1, 0),
        "topRight": (5, 0),
        "bottomRight": (4, 3),
        "bottomLeft": (0, 3),
    }

    cropped = ImageObject(imagePath)
    assert cropped.perspectiveCorrection(**kwargs, crop=True) is None
    assert cropped.size() == (4, 3)
    assert cropped.offset() == (0, 0)

    expanded = ImageObject(imagePath)
    assert expanded.perspectiveCorrection(**kwargs, crop=False) is None
    assert expanded.size() == (6, 3)
    assert expanded.offset() == (-1, 0)


def test_imageObject_perspective_rotate_projects_corners(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "perspective-rotate.png"
    image = Image.new("RGBA", (5, 5), (0, 0, 0, 255))
    for y in range(5):
        for x in range(5):
            image.putpixel((x, y), (x * 50, y * 50, 0, 255))
    image.save(imagePath)

    identity = ImageObject(imagePath)
    assert identity.perspectiveRotate(focalLength=28, yaw=0, pitch=0, roll=0) is None
    assert [identity._pilImage().getpixel((x, 2))[:3] for x in range(5)] == [
        (0, 100, 0),
        (50, 100, 0),
        (100, 100, 0),
        (150, 100, 0),
        (200, 100, 0),
    ]

    yawed = ImageObject(imagePath)
    assert yawed.perspectiveRotate(focalLength=28, yaw=0.6, pitch=0, roll=0) is None
    assert yawed.size() == (5, 5)
    assert [yawed._pilImage().getpixel((x, 2))[:3] for x in range(5)] == [
        (94, 55, 0),
        (94, 116, 0),
        (94, 175, 0),
        (78, 205, 0),
        (0, 0, 0),
    ]


def test_imageObject_light_tunnel_uses_center_and_radius(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "light-tunnel.png"
    image = Image.new("RGBA", (5, 5), (0, 0, 0, 255))
    for y in range(5):
        for x in range(5):
            image.putpixel((x, y), (x * 50, y * 50, 0, 255))
    image.save(imagePath)

    unchanged = ImageObject(imagePath)
    assert unchanged.lightTunnel(center=(2, 2), rotation=0, radius=1) is None
    assert [unchanged._pilImage().getpixel((x, 2))[:3] for x in range(5)] == [
        (0, 100, 0),
        (50, 100, 0),
        (100, 100, 0),
        (150, 100, 0),
        (200, 100, 0),
    ]

    tunneled = ImageObject(imagePath)
    assert tunneled.lightTunnel(center=(2, 2), rotation=0, radius=3) is None
    assert [tunneled._pilImage().getpixel((x, 2))[:3] for x in range(5)] == [
        (150, 50, 0),
        (100, 150, 0),
        (100, 100, 0),
        (100, 50, 0),
        (50, 150, 0),
    ]


def test_imageObject_focus_context_draws_into_image_and_restores_drawing(tmpdir):
    mainPath = pathlib.Path(tmpdir) / "main.png"
    drawbot.newDrawing()
    try:
        drawbot.size(8, 4)
        drawbot.fill(1, 0, 0)
        drawbot.rect(0, 0, 8, 4)

        im = ImageObject()
        with im:
            drawbot.size(4, 4)
            drawbot.fill(0, 1, 0)
            drawbot.rect(0, 0, 4, 4)

        drawbot.fill(0, 0, 1)
        drawbot.rect(4, 0, 4, 4)
        drawbot.saveImage(mainPath)

        assert im.size() == (4, 4)
        assert im._pilImage().getpixel((2, 2)) == (0, 255, 0, 255)
        with Image.open(mainPath) as mainImage:
            mainImage = mainImage.convert("RGBA")
            assert mainImage.getpixel((2, 2)) == (255, 0, 0, 255)
            assert mainImage.getpixel((6, 2)) == (0, 0, 255, 255)
    finally:
        drawbot.newDrawing()


def test_imageObject_focus_context_uses_bound_namespace_drawing(tmpdir):
    mainPath = pathlib.Path(tmpdir) / "bound-main.png"
    db = Drawing()
    namespace = makeDrawbotNamespace(db)
    BoundImageObject = namespace["ImageObject"]

    namespace["size"](6, 3)
    namespace["fill"](1, 0, 0)
    namespace["rect"](0, 0, 6, 3)

    im = BoundImageObject()
    with im:
        namespace["size"](3, 3)
        namespace["fill"](0, 1, 0)
        namespace["rect"](0, 0, 3, 3)

    namespace["fill"](0, 0, 1)
    namespace["rect"](3, 0, 3, 3)
    db.saveImage(mainPath)

    assert im.size() == (3, 3)
    assert im._pilImage().getpixel((1, 1)) == (0, 255, 0, 255)
    with Image.open(mainPath) as mainImage:
        mainImage = mainImage.convert("RGBA")
        assert mainImage.getpixel((1, 1)) == (255, 0, 0, 255)
        assert mainImage.getpixel((4, 1)) == (0, 0, 255, 255)


def test_imageObject_lock_focus_errors():
    im = ImageObject()
    with pytest.raises(DrawbotError):
        im.unlockFocus()
    drawbot.newDrawing()
    try:
        assert im.lockFocus() is None
        with pytest.raises(DrawbotError):
            im.lockFocus()
    finally:
        im.unlockFocus()
        drawbot.newDrawing()


def test_imageObject_analysis_and_stylize_batch(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "analysis.png"
    image = Image.new("RGBA", (24, 16), (40, 80, 160, 255))
    for x in range(8):
        image.putpixel((x, 8), (200, 40, 20, 128))
    image.save(imagePath)

    onePixelCalls = [
        "areaAverage",
        "areaMaximum",
        "areaMinimum",
        "areaMaximumAlpha",
        "areaMinimumAlpha",
    ]
    for methodName in onePixelCalls:
        im = ImageObject(imagePath)
        assert getattr(im, methodName)((0, 0, 24, 16)) is None
        assert im.size() == (1, 1)

    sizedCalls = [
        ("areaMinMax", ((0, 0, 24, 16),), {}, (2, 1)),
        ("areaMinMaxRed", ((0, 0, 24, 16),), {}, (2, 1)),
        ("rowAverage", ((0, 0, 24, 16),), {}, (1, 16)),
        ("columnAverage", ((0, 0, 24, 16),), {}, (24, 1)),
        ("areaHistogram", (), {"extent": (0, 0, 24, 16), "count": 8}, (8, 1)),
        ("areaLogarithmicHistogram", (), {"extent": (0, 0, 24, 16), "count": 8}, (8, 1)),
        ("histogramDisplayFilter", (), {"height": 12}, (256, 12)),
    ]
    for methodName, args, kwargs, expectedSize in sizedCalls:
        im = ImageObject(imagePath)
        assert getattr(im, methodName)(*args, **kwargs) is None
        assert im.size() == expectedSize

    calls = [
        ("SRGBToneCurveToLinear", (), {}),
        ("linearToSRGBToneCurve", (), {}),
        ("depthToDisparity", (), {}),
        ("disparityToDepth", (), {}),
        ("bokehBlur", (), {"radius": 2}),
        ("discBlur", (), {"radius": 2}),
        ("depthOfField", (), {"radius": 2}),
        ("documentEnhancer", (), {}),
        ("gaborGradients", (), {}),
        ("guidedFilter", (), {}),
        ("personSegmentation", (), {}),
        ("saliencyMapFilter", (), {}),
        ("highlightShadowAdjust", (), {"shadowAmount": 0.2}),
        ("heightFieldFromMask", (), {"radius": 1}),
        ("lineOverlay", (), {}),
        ("cannyEdgeDetector", (), {}),
        ("sobelGradients", (), {}),
        ("dotScreen", (), {"width": 4}),
        ("lineScreen", (), {"width": 4}),
        ("circularScreen", (), {"width": 4}),
        ("hatchedScreen", (), {"width": 4}),
        ("CMYKHalftone", (), {"width": 4}),
        ("crystallize", (), {"radius": 4}),
        ("hexagonalPixellate", (), {"scale": 4}),
        ("pointillize", (), {"radius": 4}),
    ]
    for methodName, args, kwargs in calls:
        im = ImageObject(imagePath)
        assert getattr(im, methodName)(*args, **kwargs) is None
        width, height = im.size()
        assert width > 0
        assert height > 0

    maskPath = pathlib.Path(tmpdir) / "analysis-mask.png"
    mask = Image.new("RGBA", (24, 16), (0, 0, 255, 255))
    mask.save(maskPath)
    for methodName, args, kwargs in [
        ("maskedVariableBlur", (maskPath,), {"radius": 2}),
        ("edgePreserveUpsampleFilter", (maskPath,), {}),
        ("shadedMaterial", (maskPath,), {"scale": 2}),
    ]:
        im = ImageObject(imagePath)
        assert getattr(im, methodName)(*args, **kwargs) is None
        assert im.size() == (24, 16)

    im = ImageObject(imagePath)
    assert im.spotLight(lightPosition=(12, 8, 20), concentration=0.4) is None
    assert im.size() == (24, 16)


def test_imageObject_cmyk_halftone_uses_gcr_and_ucr(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "cmyk-halftone.png"
    colors = [
        (80, 80, 80, 255),
        (160, 80, 80, 255),
        (80, 160, 80, 255),
        (80, 80, 160, 255),
        (220, 180, 120, 255),
        (30, 120, 200, 255),
    ]
    image = Image.new("RGBA", (6, 4))
    for y in range(4):
        for x, color in enumerate(colors):
            image.putpixel((x, y), color)
    image.save(imagePath)

    noBlack = ImageObject(imagePath)
    assert noBlack.CMYKHalftone(center=(0, 0), angle=0, width=3, sharpness=1, GCR=0, UCR=0.5) is None
    blackReplacement = ImageObject(imagePath)
    assert blackReplacement.CMYKHalftone(center=(0, 0), angle=0, width=3, sharpness=1, GCR=1, UCR=0.5) is None
    noRemoval = ImageObject(imagePath)
    assert noRemoval.CMYKHalftone(center=(0, 0), angle=0, width=3, sharpness=1, GCR=1, UCR=0) is None
    fullRemoval = ImageObject(imagePath)
    assert fullRemoval.CMYKHalftone(center=(0, 0), angle=0, width=3, sharpness=1, GCR=1, UCR=1) is None

    assert [noBlack._pilImage().getpixel((x, 0))[:3] for x in range(6)] == [
        (0, 0, 0),
        (255, 0, 0),
        (255, 255, 0),
        (0, 0, 0),
        (255, 255, 255),
        (255, 255, 255),
    ]
    assert [blackReplacement._pilImage().getpixel((x, 0))[:3] for x in range(6)] == [
        (0, 0, 0),
        (255, 255, 255),
        (255, 255, 255),
        (255, 255, 0),
        (255, 255, 255),
        (255, 255, 255),
    ]
    assert [fullRemoval._pilImage().getpixel((x, 0))[:3] for x in range(6)] == [
        (0, 0, 0),
        (255, 255, 255),
        (255, 255, 255),
        (255, 255, 255),
        (255, 255, 255),
        (255, 255, 255),
    ]
    assert noBlack._pilImage().tobytes() != blackReplacement._pilImage().tobytes()
    assert noRemoval._pilImage().tobytes() != fullRemoval._pilImage().tobytes()


def test_imageObject_spot_light_targets_light_points_at(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "spotlight.png"
    Image.new("RGBA", (7, 5), (20, 40, 60, 255)).save(imagePath)

    im = ImageObject(imagePath)
    assert im.spotLight(
        lightPosition=(0, 2, 10),
        lightPointsAt=(5, 2, 0),
        brightness=1,
        concentration=0.3,
        color=(1, 0, 0, 1),
    ) is None
    image = im._pilImage()
    assert image.getpixel((5, 2)) == (255, 40, 60, 255)
    assert image.getpixel((0, 2))[3] < image.getpixel((3, 2))[3] < image.getpixel((5, 2))[3]
    assert image.getpixel((0, 0)) == (0, 0, 0, 0)


def test_imageObject_bokeh_blur_uses_ring_parameters(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "bokeh.png"
    image = Image.new("RGBA", (7, 7), (0, 0, 0, 255))
    image.putpixel((3, 3), (255, 255, 255, 255))
    image.save(imagePath)

    plain = ImageObject(imagePath)
    assert plain.bokehBlur(radius=2, ringAmount=0, ringSize=0.5, softness=0) is None
    assert [plain._pilImage().getpixel((x, 3))[0] for x in range(7)] == [0, 0, 20, 20, 20, 0, 0]

    ringed = ImageObject(imagePath)
    assert ringed.bokehBlur(radius=2, ringAmount=1, ringSize=0.5, softness=0) is None
    assert [ringed._pilImage().getpixel((x, 3))[0] for x in range(7)] == [0, 0, 29, 14, 29, 0, 0]
    assert [ringed._pilImage().getpixel((x, 2))[0] for x in range(7)] == [0, 0, 17, 29, 17, 0, 0]


def test_imageObject_bokeh_blur_zero_radius_is_noop(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "bokeh-zero.png"
    image = Image.new("RGBA", (5, 5), (0, 0, 0, 255))
    image.putpixel((2, 2), (255, 255, 255, 255))
    image.save(imagePath)

    unchanged = ImageObject(imagePath)
    assert unchanged.bokehBlur(radius=0, ringAmount=0, ringSize=0.5, softness=0) is None
    assert unchanged._pilImage().tobytes() == image.tobytes()

    blurred = ImageObject(imagePath)
    assert blurred.bokehBlur(radius=1, ringAmount=0, ringSize=0.5, softness=0) is None
    assert [blurred._pilImage().getpixel((x, 2))[0] for x in range(5)] == [0, 51, 51, 51, 0]
    assert blurred._pilImage().tobytes() != image.tobytes()


def test_imageObject_motion_blur_uses_radius_and_angle(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "motion-blur.png"
    image = Image.new("RGBA", (7, 7), (0, 0, 0, 255))
    image.putpixel((3, 3), (255, 255, 255, 255))
    image.save(imagePath)

    unchanged = ImageObject(imagePath)
    assert unchanged.motionBlur(radius=0, angle=0) is None
    assert unchanged._pilImage().tobytes() == image.tobytes()

    horizontal = ImageObject(imagePath)
    assert horizontal.motionBlur(radius=1, angle=0) is None
    assert [horizontal._pilImage().getpixel((x, 3))[0] for x in range(7)] == [0, 0, 85, 85, 85, 0, 0]
    assert [horizontal._pilImage().getpixel((3, y))[0] for y in range(7)] == [0, 0, 0, 85, 0, 0, 0]

    vertical = ImageObject(imagePath)
    assert vertical.motionBlur(radius=1, angle=90) is None
    assert [vertical._pilImage().getpixel((x, 3))[0] for x in range(7)] == [0, 0, 0, 85, 0, 0, 0]
    assert [vertical._pilImage().getpixel((3, y))[0] for y in range(7)] == [0, 0, 85, 85, 85, 0, 0]

    wide = ImageObject(imagePath)
    assert wide.motionBlur(radius=3, angle=0) is None
    assert [wide._pilImage().getpixel((x, 3))[0] for x in range(7)] == [36, 36, 36, 36, 36, 36, 36]


def test_imageObject_noise_reduction_controls_noise_and_sharpness(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "noise-reduction.png"
    image = Image.new("RGBA", (5, 5), (80, 90, 100, 255))
    colors = [
        (20, 40, 60, 255),
        (200, 180, 160, 255),
        (70, 120, 190, 255),
        (250, 250, 250, 255),
        (0, 10, 20, 255),
    ]
    for y in range(5):
        for x in range(5):
            image.putpixel((x, y), colors[(x + y * 2) % len(colors)])
    image.save(imagePath)

    unchanged = ImageObject(imagePath)
    assert unchanged.noiseReduction(noiseLevel=0, sharpness=0) is None
    assert unchanged._pilImage().tobytes() == image.tobytes()

    sharpened = ImageObject(imagePath)
    assert sharpened.noiseReduction(noiseLevel=0, sharpness=0.8) is None
    assert sharpened._pilImage().getpixel((2, 2)) == (255, 255, 208, 255)
    assert sharpened._pilImage().getpixel((0, 0)) == (0, 0, 0, 255)
    assert sum(sharpened._pilImage().tobytes()) == 15691

    denoised = ImageObject(imagePath)
    assert denoised.noiseReduction(noiseLevel=0.02, sharpness=0) is None
    assert denoised._pilImage().getpixel((2, 2)) == (70, 120, 160, 255)
    assert denoised._pilImage().getpixel((0, 0)) == (70, 120, 160, 255)
    assert sum(denoised._pilImage().tobytes()) == 15095


def test_imageObject_sharpen_luminance_preserves_chroma_and_alpha(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "sharpen-luminance.png"
    image = Image.new("RGBA", (5, 1))
    for x, pixel in enumerate(
        [
            (40, 20, 180, 101),
            (50, 30, 190, 111),
            (200, 180, 30, 121),
            (210, 190, 40, 131),
            (220, 200, 50, 141),
        ]
    ):
        image.putpixel((x, 0), pixel)
    image.save(imagePath)
    baseline = ImageObject(imagePath)._pilImage().tobytes()

    unchanged = ImageObject(imagePath)
    assert unchanged.sharpenLuminance(sharpness=0, radius=1) is None
    assert unchanged._pilImage().tobytes() == baseline

    luminance = ImageObject(imagePath)
    assert luminance.sharpenLuminance(sharpness=1, radius=1) is None
    assert [luminance._pilImage().getpixel((x, 0)) for x in range(5)] == [
        (13, 0, 151, 101),
        (0, 0, 133, 111),
        (255, 255, 105, 121),
        (226, 208, 56, 131),
        (231, 212, 61, 141),
    ]

    rgb = ImageObject(imagePath)
    assert rgb.unsharpMask(intensity=1, radius=1) is None
    assert [rgb._pilImage().getpixel((x, 0))[3] for x in range(5)] == [101, 111, 121, 131, 141]
    assert [luminance._pilImage().getpixel((x, 0))[3] for x in range(5)] == [101, 111, 121, 131, 141]
    assert luminance._pilImage().tobytes() != rgb._pilImage().tobytes()


def test_imageObject_unsharp_mask_preserves_alpha(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "unsharp-mask.png"
    image = Image.new("RGBA", (5, 1))
    for x, pixel in enumerate(
        [
            (40, 20, 180, 101),
            (50, 30, 190, 111),
            (200, 180, 30, 121),
            (210, 190, 40, 131),
            (220, 200, 50, 141),
        ]
    ):
        image.putpixel((x, 0), pixel)
    image.save(imagePath)
    baseline = ImageObject(imagePath)._pilImage().tobytes()

    unchanged = ImageObject(imagePath)
    assert unchanged.unsharpMask(intensity=0, radius=1) is None
    assert unchanged._pilImage().tobytes() == baseline

    sharpened = ImageObject(imagePath)
    assert sharpened.unsharpMask(intensity=1, radius=1) is None
    assert [sharpened._pilImage().getpixel((x, 0)) for x in range(5)] == [
        (8, 0, 194, 101),
        (0, 0, 255, 111),
        (255, 255, 0, 121),
        (232, 216, 19, 131),
        (235, 213, 61, 141),
    ]


def test_imageObject_masked_variable_blur_uses_mask_as_radius(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "variable-blur.png"
    maskPath = pathlib.Path(tmpdir) / "variable-blur-mask.png"
    image = Image.new("RGBA", (7, 1), (0, 0, 0, 255))
    image.putpixel((3, 0), (255, 255, 255, 255))
    image.save(imagePath)
    mask = Image.new("L", (7, 1))
    mask.putdata([0, 0, 64, 128, 192, 255, 255])
    mask.convert("RGBA").save(maskPath)

    im = ImageObject(imagePath)
    assert im.maskedVariableBlur(maskPath, radius=2) is None
    assert [im._pilImage().getpixel((x, 0))[0] for x in range(7)] == [0, 0, 27, 103, 55, 33, 22]


def test_imageObject_guided_filter_preserves_guide_edges(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "guided.png"
    guidePath = pathlib.Path(tmpdir) / "guide.png"
    image = Image.new("RGBA", (7, 1), (0, 0, 0, 255))
    image.putpixel((3, 0), (255, 255, 255, 255))
    image.save(imagePath)
    guide = Image.new("L", (7, 1))
    guide.putdata([0, 0, 0, 255, 255, 255, 255])
    guide.convert("RGBA").save(guidePath)

    preserved = ImageObject(imagePath)
    assert preserved.guidedFilter(guideImage=guidePath, radius=2, epsilon=0.01) is None
    assert [preserved._pilImage().getpixel((x, 0))[0] for x in range(7)] == [22, 33, 44, 253, 0, 0, 0]

    smoothed = ImageObject(imagePath)
    assert smoothed.guidedFilter(guideImage=guidePath, radius=2, epsilon=1) is None
    assert [smoothed._pilImage().getpixel((x, 0))[0] for x in range(7)] == [22, 33, 44, 152, 22, 16, 11]


def test_imageObject_document_enhancer_uses_amount(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "document-enhancer.png"
    image = Image.new("RGBA", (5, 5), (120, 120, 120, 255))
    for y in range(5):
        for x in range(5):
            image.putpixel((x, y), (40 + x * 30, 50 + y * 35, 80 + (x + y) * 15, 255))
    image.putpixel((2, 2), (250, 245, 240, 255))
    image.save(imagePath)

    unchanged = ImageObject(imagePath)
    assert unchanged.documentEnhancer(amount=0) is None
    assert unchanged._pilImage().tobytes() == image.tobytes()

    partial = ImageObject(imagePath)
    assert partial.documentEnhancer(amount=0.5) is None
    assert partial._pilImage().getpixel((2, 2)) == (207, 211, 215, 255)
    assert sum(partial._pilImage().tobytes()) == 15540

    full = ImageObject(imagePath)
    assert full.documentEnhancer(amount=1) is None
    assert full._pilImage().getpixel((2, 2)) == (160, 175, 190, 255)
    assert sum(full._pilImage().tobytes()) == 15244


def test_imageObject_edges_preserves_alpha(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "edges-alpha.png"
    image = Image.new("RGBA", (5, 5), (10, 20, 30, 255))
    for x in range(5):
        image.putpixel((x, 2), (200, 200, 200, 255))
    image.save(imagePath)

    half = ImageObject(imagePath)
    assert half.edges(intensity=0.5) is None
    assert [half._pilImage().getpixel((x, 2)) for x in range(5)] == [
        (200, 200, 200, 255),
        (227, 227, 227, 255),
        (227, 227, 227, 255),
        (227, 227, 227, 255),
        (200, 200, 200, 255),
    ]

    full = ImageObject(imagePath)
    assert full.edges(intensity=1) is None
    assert [full._pilImage().getpixel((x, 2))[3] for x in range(5)] == [255, 255, 255, 255, 255]
    assert [full._pilImage().getpixel((x, 2))[0] for x in range(5)] == [200, 255, 255, 255, 200]


def test_imageObject_person_segmentation_uses_quality_level(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "person-segmentation.png"
    image = Image.new("RGBA", (7, 1), (0, 0, 0, 255))
    for x, value in enumerate([0, 20, 60, 100, 160, 220, 255]):
        image.putpixel((x, 0), (value, value, value, 255))
    image.save(imagePath)

    sharp = ImageObject(imagePath)
    assert sharp.personSegmentation(qualityLevel=1) is None
    assert [sharp._pilImage().getpixel((x, 0))[0] for x in range(7)] == [0, 0, 255, 255, 255, 255, 255]

    soft = ImageObject(imagePath)
    assert soft.personSegmentation(qualityLevel=0) is None
    assert [soft._pilImage().getpixel((x, 0))[0] for x in range(7)] == [33, 61, 103, 152, 196, 227, 244]


def test_imageObject_highlight_shadow_adjust_uses_radius_and_preserves_alpha(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "highlight-shadow.png"
    image = Image.new("RGBA", (5, 1))
    for x, value in enumerate([0, 40, 120, 220, 255]):
        image.putpixel((x, 0), (value, value, value, 128))
    image.save(imagePath)

    local = ImageObject(imagePath)
    assert local.highlightShadowAdjust(radius=0, shadowAmount=1, highlightAmount=0.5) is None
    assert [local._pilImage().getpixel((x, 0)) for x in range(5)] == [
        (80, 80, 80, 128),
        (104, 104, 104, 128),
        (133, 133, 133, 128),
        (135, 135, 135, 128),
        (128, 128, 128, 128),
    ]

    blurred = ImageObject(imagePath)
    assert blurred.highlightShadowAdjust(radius=2, shadowAmount=1, highlightAmount=0.5) is None
    assert [blurred._pilImage().getpixel((x, 0)) for x in range(5)] == [
        (62, 62, 62, 128),
        (86, 86, 86, 128),
        (129, 129, 129, 128),
        (175, 175, 175, 128),
        (177, 177, 177, 128),
    ]


def test_imageObject_edge_work_uses_radius_and_preserves_alpha(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "edge-work.png"
    image = Image.new("RGBA", (7, 3), (0, 0, 0, 123))
    for x in range(2, 5):
        image.putpixel((x, 1), (255, 255, 255, 123))
    image.save(imagePath)

    thin = ImageObject(imagePath)
    assert thin.edgeWork(radius=0) is None
    assert [[thin._pilImage().getpixel((x, y))[0] for x in range(7)] for y in range(3)] == [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 255, 255, 255, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
    ]

    thick = ImageObject(imagePath)
    assert thick.edgeWork(radius=1) is None
    assert [[thick._pilImage().getpixel((x, y))[0] for x in range(7)] for y in range(3)] == [
        [0, 255, 255, 255, 255, 255, 0],
        [0, 255, 255, 255, 255, 255, 0],
        [0, 255, 255, 255, 255, 255, 0],
    ]
    assert thin._pilImage().getpixel((3, 1))[3] == 123
    assert thick._pilImage().getpixel((3, 1))[3] == 123


def test_imageObject_canny_edge_detector_uses_hysteresis_and_perceptual(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "canny.png"
    image = Image.new("RGBA", (6, 1))
    for x, value in enumerate([0, 50, 90, 120, 140, 150]):
        image.putpixel((x, 0), (value, value, value, 77))
    image.save(imagePath)

    strongOnly = ImageObject(imagePath)
    assert strongOnly.cannyEdgeDetector(
        gaussianSigma=0,
        thresholdLow=0.05,
        thresholdHigh=0.5,
        hysteresisPasses=0,
    ) is None
    assert [strongOnly._pilImage().getpixel((x, 0)) for x in range(6)] == [
        (0, 0, 0, 77),
        (0, 0, 0, 77),
        (0, 0, 0, 77),
        (0, 0, 0, 77),
        (255, 255, 255, 77),
        (255, 255, 255, 77),
    ]

    hysteresis = ImageObject(imagePath)
    assert hysteresis.cannyEdgeDetector(
        gaussianSigma=0,
        thresholdLow=0.05,
        thresholdHigh=0.5,
        hysteresisPasses=2,
    ) is None
    assert [hysteresis._pilImage().getpixel((x, 0))[0] for x in range(6)] == [0, 0, 255, 255, 255, 255]

    perceptual = ImageObject(imagePath)
    assert perceptual.cannyEdgeDetector(
        gaussianSigma=0,
        perceptual=True,
        thresholdLow=0.05,
        thresholdHigh=0.5,
        hysteresisPasses=2,
    ) is None
    assert [perceptual._pilImage().getpixel((x, 0))[0] for x in range(6)] == [0, 255, 255, 255, 255, 255]


def test_imageObject_line_overlay_uses_noise_sharpness_and_contrast(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "line-overlay.png"
    image = Image.new("RGBA", (7, 3), (100, 100, 100, 121))
    for x in range(7):
        image.putpixel((x, 1), (100 + x * 10, 100 + x * 10, 100 + x * 10, 121))
    image.putpixel((3, 1), (240, 240, 240, 121))
    image.save(imagePath)

    base = ImageObject(imagePath)
    assert base.lineOverlay(NRNoiseLevel=0, NRSharpness=0, contrast=0, threshold=0.2, edgeIntensity=1) is None
    assert [[base._pilImage().getpixel((x, y))[0] for x in range(7)] for y in range(3)] == [
        [255, 255, 255, 255, 255, 255, 255],
        [255, 255, 0, 255, 255, 255, 255],
        [255, 255, 255, 255, 255, 255, 255],
    ]
    assert base._pilImage().getpixel((3, 1))[3] == 121

    denoised = ImageObject(imagePath)
    assert denoised.lineOverlay(NRNoiseLevel=0.1, NRSharpness=0, contrast=0, threshold=0.2, edgeIntensity=1) is None
    assert [[denoised._pilImage().getpixel((x, y))[0] for x in range(7)] for y in range(3)] == [
        [255, 255, 255, 255, 255, 255, 255],
        [255, 0, 0, 0, 0, 0, 255],
        [255, 255, 255, 255, 255, 255, 255],
    ]

    sharpened = ImageObject(imagePath)
    assert sharpened.lineOverlay(NRNoiseLevel=0, NRSharpness=1, contrast=0, threshold=0.2, edgeIntensity=1) is None
    assert [[sharpened._pilImage().getpixel((x, y))[0] for x in range(7)] for y in range(3)] == [
        [255, 255, 255, 255, 255, 255, 255],
        [255, 255, 255, 255, 255, 255, 255],
        [255, 255, 255, 255, 255, 255, 255],
    ]

    highContrast = ImageObject(imagePath)
    assert highContrast.lineOverlay(NRNoiseLevel=0, NRSharpness=0, contrast=100, threshold=0.8, edgeIntensity=1) is None
    assert [highContrast._pilImage().getpixel((x, 1))[0] for x in range(7)] == [0, 0, 0, 255, 0, 255, 255]


def test_imageObject_morphology_zero_radius_is_noop(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "morphology-zero.png"
    image = Image.new("RGBA", (3, 1))
    image.putdata([(10, 20, 30, 111), (200, 80, 40, 222), (40, 220, 70, 123)])
    image.save(imagePath)
    baseline = ImageObject(imagePath)._pilImage().tobytes()

    maximumZero = ImageObject(imagePath)
    assert maximumZero.morphologyMaximum() is None
    assert maximumZero._pilImage().tobytes() == baseline

    minimumZero = ImageObject(imagePath)
    assert minimumZero.morphologyMinimum() is None
    assert minimumZero._pilImage().tobytes() == baseline

    maximum = ImageObject(imagePath)
    assert maximum.morphologyMaximum(radius=1) is None
    assert [maximum._pilImage().getpixel((x, 0)) for x in range(3)] == [
        (200, 80, 40, 222),
        (200, 221, 70, 222),
        (200, 221, 70, 222),
    ]

    minimum = ImageObject(imagePath)
    assert minimum.morphologyMinimum(radius=1) is None
    assert [minimum._pilImage().getpixel((x, 0)) for x in range(3)] == [
        (9, 21, 30, 111),
        (9, 21, 30, 111),
        (39, 81, 39, 123),
    ]

    gradientZero = ImageObject(imagePath)
    assert gradientZero.morphologyGradient(radius=0) is None
    assert [gradientZero._pilImage().getpixel((x, 0)) for x in range(3)] == [(0, 0, 0, 0)] * 3

    gradient = ImageObject(imagePath)
    assert gradient.morphologyGradient(radius=1) is None
    assert [gradient._pilImage().getpixel((x, 0)) for x in range(3)] == [
        (191, 60, 9, 111),
        (191, 200, 39, 111),
        (162, 139, 31, 99),
    ]


def test_imageObject_morphology_rectangle_uses_width_and_height(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "morphology-rectangle.png"
    image = Image.new("RGBA", (3, 3))
    for y, row in enumerate(([10, 20, 30], [40, 50, 60], [70, 80, 90])):
        for x, value in enumerate(row):
            image.putpixel((x, y), (value, 0, 0, 100 + value))
    image.save(imagePath)

    horizontalMax = ImageObject(imagePath)
    assert horizontalMax.morphologyRectangleMaximum(width=3, height=1) is None
    assert [[horizontalMax._pilImage().getpixel((x, y))[0] for x in range(3)] for y in range(3)] == [
        [19, 29, 29],
        [49, 61, 61],
        [79, 90, 90],
    ]

    verticalMax = ImageObject(imagePath)
    assert verticalMax.morphologyRectangleMaximum(width=1, height=3) is None
    assert [[verticalMax._pilImage().getpixel((x, y))[0] for x in range(3)] for y in range(3)] == [
        [40, 49, 61],
        [70, 79, 90],
        [70, 79, 90],
    ]

    horizontalMin = ImageObject(imagePath)
    assert horizontalMin.morphologyRectangleMinimum(width=3, height=1) is None
    assert [[horizontalMin._pilImage().getpixel((x, y))[0] for x in range(3)] for y in range(3)] == [
        [9, 9, 19],
        [40, 40, 49],
        [70, 70, 79],
    ]

    verticalMin = ImageObject(imagePath)
    assert verticalMin.morphologyRectangleMinimum(width=1, height=3) is None
    assert [[verticalMin._pilImage().getpixel((x, y))[0] for x in range(3)] for y in range(3)] == [
        [9, 19, 29],
        [9, 19, 29],
        [40, 49, 61],
    ]


def test_imageObject_pixellate_uses_center(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "pixellate.png"
    image = Image.new("RGBA", (6, 1))
    for x in range(6):
        image.putpixel((x, 0), (x * 40, 0, 0, 100 + x))
    image.save(imagePath)

    leftAnchored = ImageObject(imagePath)
    assert leftAnchored.pixellate(center=(0, 0), scale=2) is None
    assert [leftAnchored._pilImage().getpixel((x, 0)) for x in range(6)] == [
        (20, 0, 0, 100),
        (20, 0, 0, 100),
        (100, 0, 0, 102),
        (100, 0, 0, 102),
        (179, 0, 0, 104),
        (179, 0, 0, 104),
    ]

    shifted = ImageObject(imagePath)
    assert shifted.pixellate(center=(1, 0), scale=2) is None
    assert [shifted._pilImage().getpixel((x, 0)) for x in range(6)] == [
        (0, 0, 0, 100),
        (60, 0, 0, 102),
        (60, 0, 0, 102),
        (140, 0, 0, 104),
        (140, 0, 0, 104),
        (199, 0, 0, 105),
    ]


def test_imageObject_pointillize_uses_center(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "pointillize.png"
    image = Image.new("RGBA", (6, 3), (0, 0, 0, 0))
    for y in range(3):
        for x in range(6):
            image.putpixel((x, y), (x * 40, y * 70, 0, 255))
    image.save(imagePath)

    leftAnchored = ImageObject(imagePath)
    assert leftAnchored.pointillize(radius=2, center=(0, 0)) is None
    assert [leftAnchored._pilImage().getpixel((x, 1)) for x in range(6)] == [
        (20, 35, 0, 255),
        (20, 35, 0, 255),
        (100, 35, 0, 255),
        (100, 35, 0, 255),
        (180, 35, 0, 255),
        (180, 35, 0, 255),
    ]
    assert leftAnchored._pilImage().getpixel((0, 0)) == (0, 0, 0, 0)

    shifted = ImageObject(imagePath)
    assert shifted.pointillize(radius=2, center=(1, 0)) is None
    assert [shifted._pilImage().getpixel((x, 1)) for x in range(6)] == [
        (0, 35, 0, 255),
        (60, 35, 0, 255),
        (60, 35, 0, 255),
        (140, 35, 0, 255),
        (140, 35, 0, 255),
        (200, 35, 0, 255),
    ]
    assert shifted._pilImage().getpixel((0, 0)) == (0, 35, 0, 255)


def test_imageObject_depth_of_field_uses_focus_line(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "depth-of-field.png"
    image = Image.new("RGBA", (7, 5), (0, 0, 0, 255))
    image.putpixel((3, 2), (255, 255, 255, 255))
    image.save(imagePath)

    focused = ImageObject(imagePath)
    assert focused.depthOfField(
        point0=(0, 2),
        point1=(6, 2),
        saturation=1,
        unsharpMaskRadius=0,
        unsharpMaskIntensity=0,
        radius=1,
    ) is None
    assert focused.size() == (7, 5)
    assert [focused._pilImage().getpixel((x, 2))[0] for x in range(7)] == [0, 0, 0, 255, 0, 0, 0]

    blurred = ImageObject(imagePath)
    assert blurred.depthOfField(
        point0=(0, 0),
        point1=(6, 0),
        saturation=1,
        unsharpMaskRadius=0,
        unsharpMaskIntensity=0,
        radius=1,
    ) is None
    assert [blurred._pilImage().getpixel((x, 2))[0] for x in range(7)] == [1, 3, 12, 148, 12, 3, 1]


def test_imageObject_saliency_map_uses_local_contrast(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "saliency.png"
    image = Image.new("RGBA", (9, 9), (80, 80, 80, 255))
    for y in range(3, 6):
        for x in range(3, 6):
            image.putpixel((x, y), (240, 240, 240, 255))
    image.save(imagePath)

    im = ImageObject(imagePath)
    assert im.saliencyMapFilter() is None
    result = im._pilImage()
    center = result.getpixel((4, 4))
    corner = result.getpixel((0, 0))
    assert center[0] == center[1] == center[2]
    assert corner[0] == corner[1] == corner[2]
    assert center[0] > corner[0]
    assert center[3] == corner[3] == 255


def test_imageObject_shaded_material_uses_height_gradient(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "material.png"
    shadingPath = pathlib.Path(tmpdir) / "material-shading.png"
    Image.new("RGBA", (5, 3), (100, 100, 100, 255)).save(imagePath)
    shading = Image.new("L", (5, 3))
    for y in range(3):
        for x, value in enumerate([255, 192, 128, 64, 0]):
            shading.putpixel((x, y), value)
    shading.convert("RGBA").save(shadingPath)

    flat = ImageObject(imagePath)
    assert flat.shadedMaterial(shadingPath, scale=0) is None
    assert [flat._pilImage().getpixel((x, 1))[0] for x in range(5)] == [90, 90, 90, 90, 90]

    relieved = ImageObject(imagePath)
    assert relieved.shadedMaterial(shadingPath, scale=10) is None
    assert [relieved._pilImage().getpixel((x, 1))[0] for x in range(5)] == [82, 73, 73, 73, 82]


def test_imageObject_transition_batch(tmpdir):
    sourcePath = pathlib.Path(tmpdir) / "source.png"
    targetPath = pathlib.Path(tmpdir) / "target.png"
    maskPath = pathlib.Path(tmpdir) / "mask.png"
    shadingPath = pathlib.Path(tmpdir) / "shading.png"
    Image.new("RGBA", (18, 14), (220, 40, 80, 255)).save(sourcePath)
    Image.new("RGBA", (18, 14), (40, 160, 220, 255)).save(targetPath)
    Image.new("RGBA", (18, 14), (128, 128, 128, 255)).save(maskPath)
    Image.new("RGBA", (18, 14), (220, 220, 220, 255)).save(shadingPath)

    calls = [
        ("dissolveTransition", (targetPath,), {"time": 0.5}),
        ("swipeTransition", (targetPath,), {"time": 0.5, "width": 8}),
        ("barsSwipeTransition", (targetPath,), {"time": 0.5, "width": 4}),
        ("copyMachineTransition", (targetPath,), {"time": 0.5, "width": 8}),
        ("flashTransition", (targetPath,), {"center": (9, 7), "time": 0.5}),
        ("modTransition", (targetPath,), {"center": (9, 7), "time": 0.5}),
        ("rippleTransition", (targetPath, shadingPath), {"center": (9, 7), "time": 0.5, "width": 6}),
        ("disintegrateWithMaskTransition", (targetPath, maskPath), {"time": 0.5}),
        ("accordionFoldTransition", (targetPath,), {"time": 0.5}),
        ("pageCurlTransition", (targetPath, maskPath, shadingPath), {"time": 0.5}),
        ("pageCurlWithShadowTransition", (targetPath, maskPath), {"time": 0.5}),
    ]
    for methodName, args, kwargs in calls:
        im = ImageObject(sourcePath)
        assert getattr(im, methodName)(*args, **kwargs) is None
        assert im.size() == (18, 14)


def test_imageObject_swipe_transition_color_extent(tmpdir):
    sourcePath = pathlib.Path(tmpdir) / "swipe-source.png"
    targetPath = pathlib.Path(tmpdir) / "swipe-target.png"
    Image.new("RGBA", (6, 3), (255, 0, 0, 255)).save(sourcePath)
    Image.new("RGBA", (6, 3), (0, 0, 255, 255)).save(targetPath)

    im = ImageObject(sourcePath)
    assert im.swipeTransition(
        targetPath,
        extent=(0, 0, 6, 1),
        color=(0, 1, 0, 1),
        time=0.5,
        angle=0,
        width=2,
        opacity=1,
    ) is None
    image = im._pilImage()
    assert [image.getpixel((x, 0)) for x in range(6)] == [
        (0, 0, 255, 255),
        (0, 0, 255, 255),
        (0, 0, 255, 255),
        (0, 255, 0, 255),
        (255, 0, 0, 255),
        (255, 0, 0, 255),
    ]
    assert [image.getpixel((x, 1)) for x in range(6)] == [(255, 0, 0, 255)] * 6


def test_imageObject_flash_transition_extent_and_striations(tmpdir):
    sourcePath = pathlib.Path(tmpdir) / "flash-source.png"
    targetPath = pathlib.Path(tmpdir) / "flash-target.png"
    Image.new("RGBA", (6, 3), (255, 0, 0, 255)).save(sourcePath)
    Image.new("RGBA", (6, 3), (0, 0, 255, 255)).save(targetPath)

    im = ImageObject(sourcePath)
    assert im.flashTransition(
        targetPath,
        center=(0, 0),
        extent=(0, 0, 6, 1),
        color=(0, 0, 0, 1),
        time=1,
        fadeThreshold=0,
    ) is None
    image = im._pilImage()
    assert [image.getpixel((x, 0)) for x in range(6)] == [(0, 0, 255, 255)] * 6
    assert [image.getpixel((x, 1)) for x in range(6)] == [(255, 0, 0, 255)] * 6

    Image.new("RGBA", (7, 7), (0, 0, 0, 255)).save(sourcePath)
    Image.new("RGBA", (7, 7), (0, 0, 0, 255)).save(targetPath)
    smooth = ImageObject(sourcePath)
    assert smooth.flashTransition(
        targetPath,
        center=(3, 3),
        color=(1, 1, 1, 1),
        time=0.5,
        maxStriationRadius=1,
        striationStrength=0,
        striationContrast=1,
        fadeThreshold=0.5,
    ) is None
    striated = ImageObject(sourcePath)
    assert striated.flashTransition(
        targetPath,
        center=(3, 3),
        color=(1, 1, 1, 1),
        time=0.5,
        maxStriationRadius=3,
        striationStrength=1,
        striationContrast=2,
        fadeThreshold=0.5,
    ) is None
    assert smooth._pilImage().tobytes() != striated._pilImage().tobytes()


def test_imageObject_disintegrate_transition_shadow(tmpdir):
    sourcePath = pathlib.Path(tmpdir) / "disintegrate-source.png"
    targetPath = pathlib.Path(tmpdir) / "disintegrate-target.png"
    maskPath = pathlib.Path(tmpdir) / "disintegrate-mask.png"
    Image.new("RGBA", (4, 1), (255, 0, 0, 255)).save(sourcePath)
    Image.new("RGBA", (4, 1), (0, 0, 255, 255)).save(targetPath)
    mask = Image.new("L", (4, 1))
    mask.putdata([0, 85, 170, 255])
    mask.convert("RGBA").save(maskPath)

    noShadow = ImageObject(sourcePath)
    assert noShadow.disintegrateWithMaskTransition(
        targetPath,
        maskPath,
        time=0.5,
        shadowRadius=0,
        shadowDensity=0,
    ) is None
    assert [noShadow._pilImage().getpixel((x, 0)) for x in range(4)] == [
        (0, 0, 255, 255),
        (0, 0, 255, 255),
        (255, 0, 0, 255),
        (255, 0, 0, 255),
    ]

    shadowed = ImageObject(sourcePath)
    assert shadowed.disintegrateWithMaskTransition(
        targetPath,
        maskPath,
        time=0.5,
        shadowRadius=1,
        shadowDensity=1,
        shadowOffset=(1, 0),
    ) is None
    pixels = [shadowed._pilImage().getpixel((x, 0)) for x in range(4)]
    assert pixels[:2] == [(0, 0, 255, 255), (0, 0, 255, 255)]
    assert pixels[2][0] < 255
    assert pixels[3][0] < 255


def test_imageObject_ripple_transition_extent_and_shading(tmpdir):
    sourcePath = pathlib.Path(tmpdir) / "ripple-source.png"
    targetPath = pathlib.Path(tmpdir) / "ripple-target.png"
    shadingPath = pathlib.Path(tmpdir) / "ripple-shading.png"
    Image.new("RGBA", (5, 3), (255, 0, 0, 255)).save(sourcePath)
    target = Image.new("RGBA", (5, 3))
    for y in range(3):
        for x in range(5):
            target.putpixel((x, y), (x * 50, y * 80, 255, 255))
    target.save(targetPath)
    shading = Image.new("L", (5, 3))
    for y in range(3):
        for x in range(5):
            shading.putpixel((x, y), 255 if (x + y) % 2 else 0)
    shading.convert("RGBA").save(shadingPath)

    im = ImageObject(sourcePath)
    assert im.rippleTransition(
        targetPath,
        shadingPath,
        center=(2, 1),
        extent=(0, 0, 3, 3),
        time=0.5,
        width=2,
        scale=20,
    ) is None
    image = im._pilImage()
    assert [image.getpixel((x, 1)) for x in range(3)] == [
        (102, 48, 153, 255),
        (91, 64, 204, 255),
        (100, 80, 255, 255),
    ]
    assert [image.getpixel((x, 1)) for x in range(3, 5)] == [(255, 0, 0, 255)] * 2


def test_imageObject_mod_transition_angle_compression(tmpdir):
    sourcePath = pathlib.Path(tmpdir) / "mod-source.png"
    targetPath = pathlib.Path(tmpdir) / "mod-target.png"
    Image.new("RGBA", (5, 5), (255, 0, 0, 255)).save(sourcePath)
    Image.new("RGBA", (5, 5), (0, 0, 255, 255)).save(targetPath)

    horizontal = ImageObject(sourcePath)
    assert horizontal.modTransition(
        targetPath,
        center=(2, 2),
        time=0.75,
        angle=0,
        radius=4,
        compression=2,
    ) is None
    vertical = ImageObject(sourcePath)
    assert vertical.modTransition(
        targetPath,
        center=(2, 2),
        time=0.75,
        angle=math.pi / 2,
        radius=4,
        compression=2,
    ) is None
    assert [horizontal._pilImage().getpixel((x, 2))[2] for x in range(5)] == [45, 191, 89, 191, 45]
    assert [vertical._pilImage().getpixel((x, 2))[2] for x in range(5)] == [45, 67, 89, 67, 45]

    compressed = ImageObject(sourcePath)
    assert compressed.modTransition(
        targetPath,
        center=(2, 2),
        time=0.75,
        angle=0,
        radius=4,
        compression=4,
    ) is None
    assert [compressed._pilImage().getpixel((x, 2))[2] for x in range(5)] == [128, 129, 89, 129, 128]


def test_imageObject_accordion_fold_transition_parameters(tmpdir):
    sourcePath = pathlib.Path(tmpdir) / "accordion-source.png"
    targetPath = pathlib.Path(tmpdir) / "accordion-target.png"
    Image.new("RGBA", (6, 3), (255, 0, 0, 255)).save(sourcePath)
    Image.new("RGBA", (6, 3), (0, 0, 255, 255)).save(targetPath)

    im = ImageObject(sourcePath)
    assert im.accordionFoldTransition(
        targetPath,
        bottomHeight=1,
        numberOfFolds=3,
        foldShadowAmount=0.5,
        time=0.5,
    ) is None
    image = im._pilImage()
    assert [image.getpixel((x, 0)) for x in range(6)] == [
        (0, 0, 255, 255),
        (0, 0, 255, 255),
        (0, 0, 128, 255),
        (0, 0, 223, 255),
        (0, 0, 255, 255),
        (255, 0, 0, 255),
    ]
    assert [image.getpixel((x, 2)) for x in range(6)] == [(255, 0, 0, 255)] * 6


def test_imageObject_page_curl_transition_images(tmpdir):
    sourcePath = pathlib.Path(tmpdir) / "pagecurl-source.png"
    targetPath = pathlib.Path(tmpdir) / "pagecurl-target.png"
    backsidePath = pathlib.Path(tmpdir) / "pagecurl-backside.png"
    shadingPath = pathlib.Path(tmpdir) / "pagecurl-shading.png"
    Image.new("RGBA", (6, 3), (255, 0, 0, 255)).save(sourcePath)
    Image.new("RGBA", (6, 3), (0, 0, 255, 255)).save(targetPath)
    Image.new("RGBA", (6, 3), (0, 255, 0, 255)).save(backsidePath)
    Image.new("RGBA", (6, 3), (0, 0, 0, 255)).save(shadingPath)

    curl = ImageObject(sourcePath)
    assert curl.pageCurlTransition(
        targetPath,
        backsidePath,
        shadingPath,
        extent=(0, 0, 6, 1),
        time=0.5,
        angle=0,
        radius=2,
    ) is None
    assert [curl._pilImage().getpixel((x, 0)) for x in range(6)] == [
        (0, 0, 255, 255),
        (0, 0, 255, 255),
        (0, 0, 255, 255),
        (0, 140, 0, 255),
        (255, 0, 0, 255),
        (255, 0, 0, 255),
    ]
    assert [curl._pilImage().getpixel((x, 1)) for x in range(6)] == [(255, 0, 0, 255)] * 6

    shadow = ImageObject(sourcePath)
    assert shadow.pageCurlWithShadowTransition(
        targetPath,
        backsidePath,
        extent=(0, 0, 6, 1),
        time=0.5,
        angle=0,
        radius=2,
        shadowSize=0.2,
        shadowAmount=1,
        shadowExtent=(0, 0, 6, 1),
    ) is None
    assert [shadow._pilImage().getpixel((x, 0)) for x in range(6)] == [
        (0, 0, 255, 255),
        (0, 0, 255, 255),
        (0, 0, 237, 255),
        (0, 255, 0, 255),
        (237, 0, 0, 255),
        (255, 0, 0, 255),
    ]
    assert [shadow._pilImage().getpixel((x, 1)) for x in range(6)] == [(255, 0, 0, 255)] * 6


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
    assert db.textOverflow("one two three four five six", (0, 0, 80, 48)) == overflow
    assert db.textBoxBaselines("one two three four five six", (0, 0, 80, 48)) == [
        (0, 28),
        (0, 4),
    ]
    bounds = db.textBoxCharacterBounds("one two three four five six", (0, 0, 80, 48))
    assert len(bounds) == 2
    assert [item.formattedSubString for item in bounds] == ["one two", "three"]
    assert bounds[0].bounds[0] == 0
    assert bounds[0].bounds[1] < bounds[0].baselineOffset
    assert bounds[0].bounds[2] > 0


def test_textBox_hyphenation():
    db = Drawing()
    db.fontSize(20)
    line, rest = db._breakLongWord("supercalifragilistic", 70)
    assert not line.endswith("-")
    db.hyphenation(True)
    line, rest = db._breakLongWord("supercalifragilistic", 70, True)
    assert line.endswith("-")
    assert rest
    db.hyphenation(False)
    assert db._gstate.textStyle.hyphenation is False


def test_writingDirection():
    db = Drawing()
    db.writingDirection("RTL")
    assert db._gstate.textStyle.direction == "rtl"
    assert db._gstate.textStyle.shape("ABC 123").clusters == [6, 5, 4, 3, 2, 1, 0]
    db.writingDirection(None)
    assert db._gstate.textStyle.direction is None


def test_tabs():
    db = Drawing()
    db.fontSize(20)
    db.tabs((50, "left"), (100, "right"), (150, "."))
    assert db._gstate.textStyle.tabs == ((50, "left"), (100, "right"), (150, "."))
    assert db.textSize("A\tB")[0] > 50
    width, runs = db._textLineRuns("A\tB", db._gstate.textStyle)
    assert len(runs) == 2
    assert runs[1][0] == 50
    db.tabs((150, "."))
    width, runs = db._textLineRuns("\t12.3", db._gstate.textStyle)
    decimalX = runs[0][0] + db._gstate.textStyle.shape("12").endPos[0]
    assert decimalX == pytest.approx(150)
    db.tabs(None)
    assert db._gstate.textStyle.tabs is None


def test_textBox_formattedString_returns_overflow():
    db = Drawing()
    db.size(200, 200)
    t = FormattedString(fontSize=20)
    t.fill(1, 0, 0)
    t += "one two "
    t.fill(0, 0, 1)
    t += "three four five six"
    overflow = db.textBox(t, (0, 0, 80, 48))
    assert isinstance(overflow, FormattedString)
    assert str(overflow)
    assert "five" in str(overflow) or "six" in str(overflow)
    assert list(overflow._iterRuns())[-1][1]["fill"] == (255, 0, 0, 255)
    assert str(db.textOverflow(t, (0, 0, 80, 48))) == str(overflow)
    assert len(db.textBoxBaselines(t, (0, 0, 80, 48))) == 2
    bounds = db.textBoxCharacterBounds(t, (0, 0, 80, 48))
    assert len(bounds) >= 2
    assert isinstance(bounds[0].formattedSubString, FormattedString)
    assert str(bounds[0].formattedSubString)
    assert bounds[0].bounds[2] > 0


def test_textBox_formattedString_hyphenation():
    db = Drawing()
    t = FormattedString(fontSize=20)
    t.hyphenation(True)
    fit, rest = db._breakFormattedToken(
        "supercalifragilistic",
        t.textProperties(),
        t,
        70,
        True,
    )
    assert fit.endswith("-")
    assert rest


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
    t.tracking(4)
    t.baselineShift(3)
    t.indent(24)
    t.tailIndent(-12)
    t.firstLineIndent(36)
    t.paragraphTopSpacing(5)
    t.paragraphBottomSpacing(7)
    t.tabs((80, "center"))
    t.hyphenation(True)
    t.underline("single")
    t.strikethrough("double")
    t.url("https://example.com")
    t.writingDirection("RTL")
    t.align("right")
    t += " world"
    runText, runProperties = list(t._iterRuns())[-1]
    assert runText == " world"
    assert runProperties["fill"] == (128, 0, 255, 0)
    assert runProperties["stroke"] == (255, 0, 0, 255)
    assert runProperties["strokeWidth"] == 2
    assert runProperties["tracking"] == 4
    assert runProperties["baselineShift"] == 3
    assert runProperties["indent"] == 24
    assert runProperties["tailIndent"] == -12
    assert runProperties["firstLineIndent"] == 36
    assert runProperties["paragraphTopSpacing"] == 5
    assert runProperties["paragraphBottomSpacing"] == 7
    assert runProperties["tabs"] == ((80, "center"),)
    assert runProperties["hyphenation"] is True
    assert runProperties["underline"] == "single"
    assert runProperties["strikethrough"] == "double"
    assert runProperties["url"] == "https://example.com"
    assert runProperties["direction"] == "rtl"
    assert runProperties["align"] == "right"

    t.cmykStroke(0, 1, 1, 0, 0.5)
    assert t.textProperties()["stroke"] == (128, 255, 0, 0)
    tracked = FormattedString("ABC", fontSize=20, tracking=5)
    untracked = FormattedString("ABC", fontSize=20)
    assert tracked.size()[0] == pytest.approx(untracked.size()[0] + 10)

    t.clear()
    assert str(t) == ""
    assert t.textProperties()["fill"] == (128, 0, 255, 0)
    assert t.textProperties()["stroke"] == (128, 255, 0, 0)
    t.url(None)
    assert t.textProperties()["url"] is None


def test_formattedString_font_info():
    t = FormattedString(fontSize=20)
    assert t.fontContainsCharacters("ABC")
    assert not t.fontContainsCharacters("\u0378")
    assert t.fontContainsGlyph("A")
    assert not t.fontContainsGlyph("notAGlyph")
    glyphNames = t.listFontGlyphNames()
    assert ".notdef" in glyphNames
    assert "A" in glyphNames
    assert t.fontAscender() > 0
    assert t.fontDescender() < 0
    assert t.fontXHeight() >= 0
    assert t.fontCapHeight() >= 0
    assert t.fontLeading() >= 0
    assert t.fontLineHeight() == pytest.approx(24)
    assert t.fontFileFontNumber() == 0
    t.fontNumber(2)
    assert t.fontFileFontNumber() == 2


def test_formattedString_mac_bridge_api_raises_clear_error():
    t = FormattedString("hello")
    with pytest.raises(DrawbotError, match="NSMutableAttributedString"):
        t.getNSObject()


def test_drawing_text_state_properties_and_font_info():
    db = Drawing()
    db.fontSize(20)
    db.tracking(5)
    db.baselineShift(3)
    db.underline("single")
    db.strikethrough("double")
    db.url("https://drawbot.com")
    properties = db.textProperties()
    assert properties["fontSize"] == 20
    assert properties["tracking"] == 5
    assert properties["baselineShift"] == 3
    assert properties["underline"] == "single"
    assert properties["strikethrough"] == "double"
    assert properties["url"] == "https://drawbot.com"

    assert db.fontContainsCharacters("ABC")
    assert not db.fontContainsCharacters("\u0378")
    assert db.fontContainsGlyph("A")
    assert not db.fontContainsGlyph("notAGlyph")
    glyphNames = db.listFontGlyphNames()
    assert ".notdef" in glyphNames
    assert "A" in glyphNames
    assert db.fontAscender() > 0
    assert db.fontDescender() < 0
    assert db.fontXHeight() >= 0
    assert db.fontCapHeight() >= 0
    assert db.fontLeading() >= 0
    assert db.fontLineHeight() == pytest.approx(24)
    assert db.fontFileFontNumber() == 0
    assert db.fontFilePath() is None


def test_formattedString_fallback_font_state():
    sourceSerif = testDir / "fonts" / "SourceSerifPro-Regular.otf"
    arabic = testDir / "fonts" / "IBMPlexSansArabic-Regular.otf"
    t = FormattedString(font=sourceSerif)
    assert not t.fontContainsCharacters("سلام")
    t.fallbackFont(arabic, fontNumber=3)
    assert t.fontContainsCharacters("سلام")
    assert t.textProperties()["fallbackFont"] == arabic
    assert t.textProperties()["fallbackFontNumber"] == 3
    t.fallbackFontNumber(4)
    assert t.textProperties()["fallbackFontNumber"] == 4


def test_drawing_fallback_font_state():
    sourceSerif = testDir / "fonts" / "SourceSerifPro-Regular.otf"
    arabic = testDir / "fonts" / "IBMPlexSansArabic-Regular.otf"
    db = Drawing()
    db.font(sourceSerif)
    assert not db.fontContainsCharacters("سلام")
    db.fallbackFont(arabic, fontNumber=3)
    assert db.fontContainsCharacters("سلام")
    assert db.textProperties()["fallbackFont"] == arabic
    assert db.textProperties()["fallbackFontNumber"] == 3
    db.fallbackFontNumber(4)
    assert db.textProperties()["fallbackFontNumber"] == 4


def test_formattedString_appendGlyph():
    t = FormattedString(fontSize=20)
    t.appendGlyph("A", "ampersand")
    assert str(t) == "A&"
    t.appendGlyph(t.listFontGlyphNames().index("B"))
    assert str(t) == "A&B"
    with pytest.raises(KeyError):
        t.appendGlyph(".notdef")


def test_formattedString_font_feature_queries():
    sourceSerif = testDir / "fonts" / "SourceSerifPro-Regular.otf"
    t = FormattedString(font=sourceSerif)
    features = t.listOpenTypeFeatures()
    assert "smcp" in features
    assert "kern" in features

    mutatorSans = testDir / "fonts" / "MutatorSans.ttf"
    t = FormattedString(font=mutatorSans)
    variations = t.listFontVariations()
    assert set(variations) == {"wdth", "wght"}
    assert variations["wdth"]["name"] == "Width"
    instances = t.listNamedInstances()
    assert "MutatorMathTest-BoldWide" in instances
    assert instances["MutatorMathTest-BoldWide"]["wght"] == 1000.0
    namedInstance = t.fontNamedInstance("MutatorMathTest-BoldWide")
    assert namedInstance == instances["MutatorMathTest-BoldWide"]
    assert t.textProperties()["variations"]["wdth"] == 1000.0
    db = Drawing()
    db.font(mutatorSans)
    assert db.fontNamedInstance("MutatorMathTest-BoldWide") == namedInstance
    assert "smcp" in db.listOpenTypeFeatures(sourceSerif)
    with pytest.raises(KeyError):
        t.fontNamedInstance("notAnInstance")


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


def test_color_space_and_languages():
    db = Drawing()
    assert db.listColorSpaces() == [
        "adobeRGB1998",
        "genericGamma22Gray",
        "genericGray",
        "genericRGB",
        "sRGB",
    ]
    db.colorSpace("sRGB")
    assert db._colorSpace == "sRGB"
    db.colorSpace(None)
    assert db._colorSpace == "genericRGB"
    with pytest.raises(DrawbotError):
        db.colorSpace("notAColorSpace")
    languages = db.listLanguages()
    assert "en" in languages
    assert "en-US" in languages


def test_installed_fonts_and_temp_font_install():
    db = Drawing()
    installed = db.installedFonts()
    assert installed == sorted(installed)
    assert installed
    assert db.installedFonts("A")
    with pytest.raises(DrawbotError):
        db.installedFonts("")

    fontPath = testDir / "fonts" / "MutatorSans.ttf"
    with pytest.warns(UserWarning, match="installFont"):
        fontName = db.installFont(fontPath)
    assert fontName == "MutatorMathTest-LightCondensed"
    assert fontName in db.installedFonts()
    assert fontName in db.installedFonts("A")
    db.font(fontName)
    assert db.fontContainsGlyph("A")
    with pytest.warns(UserWarning, match="uninstallFont"):
        assert db.uninstallFont(fontPath) is None
    assert fontName not in db.installedFonts()


def test_drawing_context_manager(tmpdir):
    db = Drawing()
    firstPath = pathlib.Path(tmpdir) / "first.png"
    secondPath = pathlib.Path(tmpdir) / "second.png"

    with db.drawing():
        db.size(20, 20)
        db.rect(0, 0, 20, 20)
        db.saveImage(firstPath)
        assert db.pageCount() == 1

    assert db.pageCount() == 0
    with db.drawing():
        db.size(10, 10)
        db.rect(0, 0, 10, 10)
        db.saveImage(secondPath)

    assert firstPath.exists()
    assert secondPath.exists()
    assert db.pageCount() == 0


def test_pages_context(tmpdir):
    path = pathlib.Path(tmpdir) / "pages.png"
    db = Drawing()
    db.size(20, 20)
    db.fill(1, 0, 0)
    db.rect(0, 0, 20, 20)
    pages = db.pages()
    assert len(pages) == 1
    assert db.pageCount() == 1
    with pages[0]:
        assert db.width() == 20
        assert db.height() == 20
        db.fill(0, 1, 0)
        db.rect(0, 0, 10, 20)
    db.saveImage(path)
    assert db.imagePixelColor(path, (5, 5)) == (0, 1, 0, 1)
    assert db.imagePixelColor(path, (15, 5)) == (1, 0, 0, 1)


def test_svg_link_annotations(tmpdir):
    path = pathlib.Path(tmpdir) / "links.svg"
    db = Drawing()
    db.size(100, 100)
    db.linkDestination("target", (50, 60))
    db.linkURL("https://drawbot.com", (10, 20, 30, 40))
    db.linkRect("target", (50, 20, 30, 40))
    db.saveImage(path)
    svg = path.read_text(encoding="utf-8")
    assert 'id="target"' in svg
    assert 'href="https://drawbot.com"' in svg
    assert 'href="#target"' in svg
    assert 'x="10" y="40" width="30" height="40"' in svg
    assert 'x="50" y="40" width="30" height="40"' in svg


def test_pdf_link_annotations(tmpdir):
    path = pathlib.Path(tmpdir) / "links.pdf"
    db = Drawing()
    db.size(100, 100)
    db.linkDestination("target", (50, 60))
    db.linkURL("https://drawbot.com", (10, 20, 30, 40))
    db.linkRect("target", (50, 20, 30, 40))
    db.saveImage(path)
    pdf = path.read_bytes()
    assert b"/Subtype /Link" in pdf
    assert b"/Annots [" in pdf
    assert b"/URI (https://drawbot.com)" in pdf
    assert b"/Dest [" in pdf
    assert b"/Rect [10 20 40 60]" in pdf
    assert b"/Rect [50 20 80 60]" in pdf


def test_mac_app_only_apis_raise_clear_errors():
    db = Drawing()
    with pytest.raises(DrawbotError, match="macOS application UI"):
        db.Variable([], {})
    with pytest.raises(DrawbotError, match="PDFKit"):
        db.pdfImage()
    with pytest.raises(DrawbotError, match="print dialog"):
        db.printImage()


def test_opacity(tmpdir):
    path = pathlib.Path(tmpdir) / "opacity.png"
    db = Drawing()
    db.size(20, 20)
    db.fill(1)
    db.rect(0, 0, 20, 20)
    db.opacity(0.5)
    db.fill(1, 0, 0)
    db.rect(0, 0, 20, 20)
    assert db._gstate.fillPaint.opacity == 0.5
    db.saveImage(path)
    with Image.open(path) as image:
        r, g, b, a = image.convert("RGBA").getpixel((10, 10))
    assert r > g
    assert g > 100
    assert a == 255


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


def test_bezier_path_optimizePath():
    path = BezierPath()
    path.moveTo((0, 0))
    path.lineTo((100, 0))
    path.moveTo((200, 200))
    assert path.path.countVerbs() == 3
    assert path.controlPointBounds() == (0.0, 0.0, 200.0, 200.0)
    assert path.optimizePath() is None
    assert path.path.countVerbs() == 2
    assert path.controlPointBounds() == (0.0, 0.0, 100.0, 0.0)
    assert len(path.contours) == 1


def test_bezier_path_intersectionPoints():
    path1 = BezierPath()
    path1.line((0, 0), (100, 100))
    path2 = BezierPath()
    path2.line((0, 100), (100, 0))
    assert path1.intersectionPoints(path2) == [(50.0, 50.0)]

    selfIntersecting = BezierPath()
    selfIntersecting.moveTo((0, 0))
    selfIntersecting.lineTo((100, 100))
    selfIntersecting.lineTo((0, 100))
    selfIntersecting.lineTo((100, 0))
    assert selfIntersecting.intersectionPoints() == [(50.0, 50.0)]

    rectangle = BezierPath()
    rectangle.rect(0, 0, 100, 100)
    assert rectangle.intersectionPoints() == []


def test_bezier_path_mac_bridge_apis_raise_clear_errors():
    path = BezierPath()
    with pytest.raises(DrawbotError, match="NSBezierPath"):
        path.getNSBezierPath()
    with pytest.raises(DrawbotError, match="NSBezierPath"):
        path.setNSBezierPath(None)


@pytest.mark.skipif(
    shutil.which("mkbitmap") is None or shutil.which("potrace") is None,
    reason="traceImage requires mkbitmap and potrace",
)
def test_bezier_path_traceImage(tmpdir):
    imagePath = pathlib.Path(tmpdir) / "trace.png"
    image = Image.new("RGBA", (40, 40), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 30, 30), fill=(0, 0, 0, 255))
    image.save(imagePath)

    path = BezierPath()
    assert path.traceImage(imagePath) is None
    assert path.bounds() == pytest.approx((10, 10, 31, 31))

    offsetPath = BezierPath()
    offsetPath.traceImage(imagePath, offset=(5, 7))
    assert offsetPath.bounds() == pytest.approx((15, 17, 36, 38))


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


def test_bezier_path_textBox_supports_hyphenation():
    unhyphenated = BezierPath()
    plainOverflow = unhyphenated.textBox(
        "supercalifragilistic",
        (0, 0, 60, 24),
        fontSize=20,
    )

    hyphenated = BezierPath()
    hyphenatedOverflow = hyphenated.textBox(
        "supercalifragilistic",
        (0, 0, 60, 24),
        fontSize=20,
        hyphenation=True,
    )

    assert plainOverflow == hyphenatedOverflow == "califragilistic"
    assert unhyphenated.bounds()[2] == pytest.approx(49.794921875)
    assert hyphenated.bounds()[2] == pytest.approx(55.76171875)


def test_bezier_path_textBox_supports_formatted_string():
    text = FormattedString(fontSize=20)
    text.append("one two ", fontSize=20)
    text.append("three four five six", fontSize=12, baselineShift=2)

    path = BezierPath()
    overflow = path.textBox(text, (0, 0, 90, 48))

    assert isinstance(overflow, FormattedString)
    assert str(overflow) == "six"
    assert path.bounds() == pytest.approx(
        (0.134765625, 5.771484375, 72.849609375, 41.37890625)
    )


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
