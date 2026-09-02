"""Create square mark variants and PNG exports for the branding assets."""

from pathlib import Path
import base64
import copy
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont


BRANDING_DIR = Path(__file__).resolve().parent
os.environ.setdefault("FONTCONFIG_FILE", str(BRANDING_DIR / "fonts.conf"))
fontconfig_path = Path("/opt/homebrew/etc/fonts")
if not fontconfig_path.is_dir():
    fontconfig_path = Path("/etc/fonts")
os.environ.setdefault("FONTCONFIG_PATH", str(fontconfig_path))

SQUARE_SIZE = 300
MARK_SCALE = 0.62
MARK_X = (SQUARE_SIZE - 500 * MARK_SCALE) / 2
MARK_Y = (SQUARE_SIZE - 300 * MARK_SCALE) / 2


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def embed_fonts(svg_path: Path) -> None:
    svg = svg_path.read_text(encoding="utf-8")
    for weight, filename in ((400, "SpaceGrotesk-Regular.ttf"), (700, "SpaceGrotesk-Bold.ttf")):
        font_data = base64.b64encode(
            (BRANDING_DIR.parent / "site" / "assets" / "fonts" / filename).read_bytes()
        ).decode("ascii")
        external_url = f"url('../site/assets/fonts/{filename}')"
        embedded_url = f"url(data:font/ttf;base64,{font_data})"
        svg = svg.replace(external_url, embedded_url)
    svg = svg.replace('font-weight="750"', 'font-weight="700"')
    svg_path.write_text(svg, encoding="utf-8")


def restore_text(svg_path: Path) -> None:
    if svg_path.name not in {"LDHS_logo_horizontal.svg", "LDHS_logo_horizontal_dark.svg", "LDHS_banner_light.svg", "LDHS_banner_dark.svg"}:
        return
    tree = ET.parse(svg_path)
    root = tree.getroot()
    namespace = root.tag.split("}", 1)[0].strip("{")
    groups = [
        child for child in root
        if local_name(child.tag) == "g"
        and child.attrib.get("font-size") in {"58", "60"}
        and any(local_name(descendant.tag) in {"path", "text"} for descendant in child.iter())
    ]
    if not groups:
        return
    old_group = groups[0]
    fill = old_group.attrib.get("fill", "#0D1B2A")
    old_index = list(root).index(old_group)
    root.remove(old_group)
    new_group = ET.Element(f"{{{namespace}}}g", {
        "fill": fill,
        "font-family": "Space Grotesk",
        "font-size": "60" if "banner" in svg_path.name else "58",
        "font-weight": "400",
        "letter-spacing": "4" if "banner" in svg_path.name else "5",
    })
    lines = (
        (("500", "205"), ("500", "280")) if "banner" in svg_path.name else
        (("560", "123"), ("560", "195"), ("560", "267"), ("560", "339"))
    )
    words = (("LONDON", "DIGITAL"), ("HUMANITIES", "SEMINARS")) if "banner" in svg_path.name else (("LONDON",), ("DIGITAL",), ("HUMANITIES",), ("SEMINARS",))
    for (x, y), word_parts in zip(lines, words):
        text = ET.SubElement(new_group, f"{{{namespace}}}text", {"x": x, "y": y})
        for part_index, word in enumerate(word_parts):
            initial = ET.SubElement(text, f"{{{namespace}}}tspan", {"font-weight": "700"})
            initial.text = word[0]
            initial.tail = word[1:] + (" " if part_index < len(word_parts) - 1 else "")
    root.insert(old_index, new_group)
    tree.write(svg_path, encoding="utf-8", xml_declaration=True)


def font_for_weight(weight: str) -> Path:
    return BRANDING_DIR.parent / "site" / "assets" / "fonts" / (
        "SpaceGrotesk-Bold.ttf" if int(float(weight or "400")) >= 600 else "SpaceGrotesk-Regular.ttf"
    )


def outline_text(svg_path: Path) -> Path:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    parents = {
        child: parent
        for parent in root.iter()
        for child in list(parent)
    }

    def inherited(element: ET.Element, attribute: str, default: str) -> str:
        current = element
        while current is not None:
            if attribute in current.attrib:
                return current.attrib[attribute]
            current = parents.get(current)
        return default

    fonts = {}
    cmap = {}
    glyph_sets = {}
    metrics = {}
    for weight in ("400", "700"):
        font = TTFont(font_for_weight(weight))
        fonts[weight] = font
        cmap[weight] = font.getBestCmap()
        glyph_sets[weight] = font.getGlyphSet()
        metrics[weight] = (font["head"].unitsPerEm, font["hmtx"].metrics)

    for text_element in list(root.iter()):
        if local_name(text_element.tag) != "text":
            continue
        parent = parents.get(text_element)
        if parent is None:
            continue
        font_size = float(inherited(text_element, "font-size", "16"))
        letter_spacing = float(inherited(text_element, "letter-spacing", "0"))
        cursor_x = float(text_element.attrib.get("x", "0"))
        baseline_y = float(text_element.attrib.get("y", "0"))
        generated = []
        runs = []
        if text_element.text:
            runs.append((text_element, text_element.text))
        for child in list(text_element):
            if local_name(child.tag) == "tspan" and child.text:
                runs.append((child, child.text))
            if child.tail:
                runs.append((text_element, child.tail))
        for run_element, text in runs:
            weight = "700" if int(float(inherited(run_element, "font-weight", "400"))) >= 600 else "400"
            font = fonts[weight]
            units_per_em, hmtx = metrics[weight]
            scale = font_size / units_per_em
            for character in text:
                glyph_name = cmap[weight].get(ord(character), ".notdef")
                pen = SVGPathPen(glyph_sets[weight])
                glyph_sets[weight][glyph_name].draw(pen)
                if pen.getCommands():
                    generated.append(ET.Element("path", {
                        "d": pen.getCommands(),
                        "transform": f"translate({cursor_x:g} {baseline_y:g}) scale({scale:g} {-scale:g})",
                    }))
                cursor_x += hmtx[glyph_name][0] * scale + letter_spacing
        index = list(parent).index(text_element)
        parent.remove(text_element)
        for offset, path in enumerate(generated):
            parent.insert(index + offset, path)

    temporary = Path(tempfile.mkstemp(suffix=".svg")[1])
    tree.write(temporary, encoding="utf-8", xml_declaration=True)
    return temporary


def make_square_mark(source_path: Path) -> Path:
    source_root = ET.parse(source_path).getroot()
    background = next(
        element for element in source_root if local_name(element.tag) == "rect"
    )
    source_group = next(
        element for element in source_root if local_name(element.tag) == "g"
    )

    root = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": "0 0 300 300",
            "role": "img",
            "aria-labelledby": "title",
        },
    )
    title = ET.SubElement(root, "title", {"id": "title"})
    dark_suffix = " (dark)" if source_path.stem.endswith("_dark") else ""
    title.text = f"London Digital Humanities Seminars square logo mark{dark_suffix}"
    ET.SubElement(
        root,
        "rect",
        {"width": "300", "height": "300", "fill": background.attrib["fill"]},
    )
    artwork = ET.SubElement(
        root,
        "g",
        {"transform": f"translate({MARK_X:g} {MARK_Y:g}) scale({MARK_SCALE:g})"},
    )
    for child in source_group:
        artwork.append(copy.deepcopy(child))

    output_path = BRANDING_DIR / f"{source_path.stem}_square.svg"
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
    return output_path


def make_transparent_mark(source_path: Path) -> Path:
    source_root = ET.parse(source_path).getroot()
    source_group = next(
        element for element in source_root if local_name(element.tag) == "g"
    )
    root = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": "0 0 500 300",
            "role": "img",
            "aria-labelledby": "title",
        },
    )
    title = ET.SubElement(root, "title", {"id": "title"})
    dark_suffix = " (dark)" if source_path.stem.endswith("_dark") else ""
    title.text = f"London Digital Humanities Seminars transparent logo mark{dark_suffix}"
    root.append(copy.deepcopy(source_group))
    output_path = BRANDING_DIR / f"{source_path.stem}_transparent.svg"
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
    return output_path


def main() -> None:
    for source_name in ("LDHS_logo_mark.svg", "LDHS_logo_mark_dark.svg"):
        source_path = BRANDING_DIR / source_name
        make_square_mark(source_path)
        make_transparent_mark(source_path)

    for svg_path in sorted(BRANDING_DIR.glob("*.svg")):
        restore_text(svg_path)
        source_copy = Path(tempfile.mkstemp(suffix=".svg")[1])
        source_copy.write_bytes(svg_path.read_bytes())
        embed_fonts(source_copy)
        outlined_path = outline_text(source_copy)
        try:
            subprocess.run(
                ["rsvg-convert", str(outlined_path), "-o", str(svg_path.with_suffix(".png"))],
                check=True,
                env=os.environ.copy(),
            )
        finally:
            outlined_path.unlink(missing_ok=True)
            source_copy.unlink(missing_ok=True)
        print(f"Rendered {svg_path.name} -> {svg_path.with_suffix('.png').name}")


if __name__ == "__main__":
    main()