import pathlib
import subprocess
import sys
from PIL import Image


testDir = pathlib.Path(__file__).resolve().parent
testScript = testDir / "apitests" / "oval.py"


def test_runner_app(tmpdir):
    outputPath = pathlib.Path(tmpdir / "test.png")
    assert not outputPath.exists()
    # assert 0, outputPath
    args = [sys.executable, "-m", "drawbot_skia", testScript, outputPath]
    subprocess.check_output(args)
    assert outputPath.exists()


def test_runner_pixel_scale(tmpdir):
    outputPath = pathlib.Path(tmpdir / "test.png")
    args = [
        sys.executable,
        "-m",
        "drawbot_skia",
        "--pixelScale",
        "2",
        testScript,
        outputPath,
    ]
    subprocess.check_output(args)
    with Image.open(outputPath) as image:
        assert image.size == (400, 400)
