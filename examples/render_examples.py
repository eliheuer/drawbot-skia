"""Render all checked-in DrawBot example scripts to JPG previews."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


EXAMPLES_ROOT = Path(__file__).resolve().parent
SKIP = {Path(__file__).name}
DEFAULT_PIXEL_SCALE = 2


def iter_example_scripts():
    for path in sorted(EXAMPLES_ROOT.glob("*/*.py")):
        if path.name not in SKIP:
            yield path


def render_examples(output_root: Path | None = None, pixel_scale: float = DEFAULT_PIXEL_SCALE) -> int:
    failures = []
    for script_path in iter_example_scripts():
        if output_root is None:
            output_path = script_path.with_suffix(".jpg")
        else:
            output_path = output_root / script_path.relative_to(EXAMPLES_ROOT).with_suffix(".jpg")
            output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            "-m",
            "drawbot_skia",
            "--pixelScale",
            str(pixel_scale),
            str(script_path),
            str(output_path),
        ]
        print(f"render {script_path.relative_to(EXAMPLES_ROOT)}")
        try:
            subprocess.check_call(command, cwd=EXAMPLES_ROOT.parent)
        except subprocess.CalledProcessError as error:
            failures.append((script_path, error.returncode))
    if failures:
        for script_path, returncode in failures:
            rel_path = script_path.relative_to(EXAMPLES_ROOT)
            print(f"failed {rel_path}: exit {returncode}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Write previews to a mirrored output directory instead of next to the scripts.",
    )
    parser.add_argument(
        "--pixel-scale",
        type=float,
        default=DEFAULT_PIXEL_SCALE,
        help=f"Raster preview scale factor. Defaults to {DEFAULT_PIXEL_SCALE}x.",
    )
    arguments = parser.parse_args(argv)
    return render_examples(arguments.output_root, pixel_scale=arguments.pixel_scale)


if __name__ == "__main__":
    raise SystemExit(main())
