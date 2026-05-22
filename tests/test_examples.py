from pathlib import Path
import re

from PIL import Image

from examples.render_examples import (
    DEFAULT_PIXEL_SCALE,
    iter_example_scripts,
    render_examples,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CATEGORIES = {
    "canvas",
    "colors",
    "images",
    "quick_reference",
    "shapes",
    "showcase",
    "text",
    "variables",
}


def test_render_examples_to_output_root(tmp_path):
    assert render_examples(tmp_path) == 0

    scripts = list(iter_example_scripts())
    assert scripts
    for script_path in scripts:
        output_path = tmp_path / script_path.relative_to(script_path.parents[1]).with_suffix(".jpg")
        output_paths = [output_path]
        if not output_path.exists():
            output_paths = sorted(output_path.parent.glob(f"{output_path.stem}_*.jpg"))
        assert output_paths
        for path in output_paths:
            assert path.exists()
            assert path.stat().st_size > 0
        first_output = output_paths[0]
        with Image.open(first_output) as image:
            assert image.width >= DEFAULT_PIXEL_SCALE
            assert image.height >= DEFAULT_PIXEL_SCALE


def test_example_categories_have_source_and_preview():
    examples_root = ROOT / "examples"
    categories = {
        path.name for path in examples_root.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }
    assert categories == EXAMPLE_CATEGORIES

    for category in sorted(EXAMPLE_CATEGORIES):
        scripts = sorted((examples_root / category).glob("*.py"))
        assert scripts, f"{category} has no example scripts"
        for script_path in scripts:
            preview_path = script_path.with_suffix(".jpg")
            preview_paths = [preview_path]
            if not preview_path.exists():
                preview_paths = sorted(preview_path.parent.glob(f"{preview_path.stem}_*.jpg"))
            assert preview_paths, f"{script_path.relative_to(ROOT)} has no preview JPG"


def test_docs_example_links_resolve():
    docs_root = ROOT / "docs"
    local_link_pattern = re.compile(r"\]\((\.\./examples/[^)]+)\)")

    links = []
    for markdown_path in sorted(docs_root.glob("*.md")):
        for link in local_link_pattern.findall(markdown_path.read_text(encoding="utf-8")):
            links.append((markdown_path, link))

    assert links
    for markdown_path, link in links:
        target = (markdown_path.parent / link).resolve()
        assert target.exists(), f"{markdown_path.relative_to(ROOT)} points to missing {link}"
