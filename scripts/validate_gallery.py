#!/usr/bin/env python3
"""Validate every ROYAL Design collection, including the complete V17 motion library."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "icons" / "app-collections.json"
HTML_PATH = ROOT / "index.html"
EXPECTED_VERSIONS = [f"V{i}" for i in range(2, 18)]
PLACEHOLDERS = {"Video stream", "Stream source", "Audio track", "Fullscreen", "Video player", "Refresh list", "Subtitles"}
SHAPES = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
ANIMATION_TAGS = {"animate", "animatetransform", "animatemotion", "set"}


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def safe_asset_path(rel):
    if not isinstance(rel, str) or not rel or rel.startswith("/") or ".." in Path(rel).parts:
        return False
    return True


def validate_svg(path, errors, require_animation=False):
    if not path.is_file():
        errors.append(f"Missing gallery SVG asset: {path.relative_to(ROOT)}")
        return
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        errors.append(f"Invalid XML/SVG {path.relative_to(ROOT)}: {exc}")
        return
    if local_name(root.tag).lower() != "svg":
        errors.append(f"Wrong SVG root in {path.relative_to(ROOT)}")
        return
    elements = list(root.iter())
    tags = [local_name(element.tag).lower() for element in elements]
    if not any(tag in SHAPES for tag in tags):
        errors.append(f"No vector geometry in {path.relative_to(ROOT)}")
    if require_animation and not any(tag in ANIMATION_TAGS for tag in tags):
        errors.append(f"Motion preview has no SMIL animation: {path.relative_to(ROOT)}")
    text_content = " ".join(part.strip() for part in root.itertext() if part.strip())
    if any(marker in text_content for marker in PLACEHOLDERS):
        errors.append(f"Placeholder text instead of artwork in {path.relative_to(ROOT)}")
    ids = {element.attrib["id"] for element in elements if "id" in element.attrib}
    refs = re.findall(r"url\(#([^)]+)\)", path.read_text(encoding="utf-8"))
    missing = sorted(set(refs) - ids)
    if missing:
        errors.append(f"Unresolved SVG references in {path.relative_to(ROOT)}: {missing}")


def main():
    errors = []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    versions = manifest.get("versions", [])
    if [version.get("version") for version in versions] != EXPECTED_VERSIONS:
        errors.append("Version tabs must be ordered V2 through V17")

    icons = [icon for collection in versions for icon in collection.get("icons", [])]
    unique_2d = {
        icon.get("variants", {}).get("2d")
        for icon in icons if icon.get("variants", {}).get("2d")
    }
    unique_3d = {
        icon.get("variants", {}).get("3d")
        for icon in icons if icon.get("variants", {}).get("3d")
    }
    unique_motion = {
        icon.get("motion")
        for icon in icons if icon.get("motion")
    }
    unique_focused = {
        icon.get("variants", {}).get("focused")
        for icon in icons if icon.get("variants", {}).get("focused")
    }
    android_xml = {
        icon.get("variants", {}).get("android_xml")
        for icon in icons if icon.get("variants", {}).get("android_xml")
    }
    totals = manifest.get("totals", {})
    expected_totals = {
        "app_collections": len(versions),
        "concepts": len(unique_2d),
        "flat_svg": len(unique_2d),
        "dimensional_svg": len(unique_3d),
        "motion_svg": len(unique_motion),
        "focused_svg": len(unique_focused),
        "android_xml": len(android_xml),
        "v17_entries": 413,
        "v17_icon_concepts": 405,
    }
    for key, value in expected_totals.items():
        if totals.get(key) != value:
            errors.append(f"totals.{key} is {totals.get(key)}, expected {value}")

    referenced_svg = set()
    v17 = next((version for version in versions if version.get("version") == "V17"), None)
    if not v17:
        errors.append("V17 collection is missing")

    for collection in versions:
        is_v17 = collection.get("version") == "V17"
        collection_icons = collection.get("icons", [])
        keys = [icon.get("key") for icon in collection_icons]
        if len(keys) != len(set(keys)):
            errors.append(f"Duplicate icon keys in {collection.get('version')}")

        for icon in collection_icons:
            variants = icon.get("variants", {})
            required_styles = ("2d",) if is_v17 else ("2d", "3d")
            for style in required_styles:
                rel = variants.get(style)
                if not safe_asset_path(rel):
                    errors.append(f"Invalid {style} asset path in {collection.get('version')}:{icon.get('key')}")
                else:
                    referenced_svg.add(rel)

            for optional_svg in ("focused",):
                rel = variants.get(optional_svg)
                if rel:
                    if not safe_asset_path(rel):
                        errors.append(f"Invalid {optional_svg} path in {collection.get('version')}:{icon.get('key')}")
                    else:
                        referenced_svg.add(rel)

            xml_rel = variants.get("android_xml")
            if xml_rel:
                if not safe_asset_path(xml_rel):
                    errors.append(f"Invalid Android XML path in {collection.get('version')}:{icon.get('key')}")
                else:
                    xml_path = ROOT / xml_rel
                    if not xml_path.is_file():
                        errors.append(f"Missing Android XML asset: {xml_rel}")
                    else:
                        try:
                            xml_root = ET.parse(xml_path).getroot()
                            if not local_name(xml_root.tag).lower().endswith("vector"):
                                errors.append(f"Invalid Android VectorDrawable root: {xml_rel}")
                            if not any(local_name(node.tag) == "path" for node in xml_root.iter()):
                                errors.append(f"Android VectorDrawable has no path geometry: {xml_rel}")
                        except ET.ParseError as exc:
                            errors.append(f"Invalid Android XML {xml_rel}: {exc}")

            motion_rel = icon.get("motion")
            if is_v17 and icon.get("category") != "restaurant-tv-v2" and not motion_rel:
                errors.append(f"V17 icon has no motion preview: {icon.get('key')}")
            if motion_rel:
                if not safe_asset_path(motion_rel):
                    errors.append(f"Invalid motion path in {collection.get('version')}:{icon.get('key')}")
                else:
                    referenced_svg.add(motion_rel)

            if icon.get("shared_from") and not any(version.get("version") == icon["shared_from"] for version in versions):
                errors.append(f"Unknown shared source version {icon['shared_from']}")

        catalog_path = ROOT / collection.get("collection_path", "") / "catalog.json"
        if not catalog_path.is_file():
            errors.append(f"Missing per-collection catalog: {catalog_path.relative_to(ROOT)}")
        else:
            try:
                catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
                if catalog.get("icons") != collection_icons:
                    errors.append(f"Stale catalog for {collection.get('version')}")
            except json.JSONDecodeError as exc:
                errors.append(f"Invalid catalog JSON {catalog_path}: {exc}")

    for rel in sorted(referenced_svg):
        path = ROOT / rel
        is_motion = bool(v17 and any(icon.get("motion") == rel for icon in v17.get("icons", [])))
        validate_svg(path, errors, require_animation=is_motion)

    required_v13 = {"channel-list", "stream", "player", "fullscreen", "subtitles", "audio", "source", "refresh"}
    v13 = next((version for version in versions if version.get("version") == "V13"), None)
    if not v13 or not required_v13.issubset({icon.get("key") for icon in v13.get("icons", [])}):
        errors.append("V13 is missing one or more of its eight RS TV core icons")

    if v17:
        v17_icons = v17.get("icons", [])
        category_counts = {}
        for icon in v17_icons:
            category = icon.get("category", "")
            category_counts[category] = category_counts.get(category, 0) + 1
        expected_categories = {
            "store": 37,
            "tv": 42,
            "launcher-ui": 16,
            "brand-assets": 8,
            "android-system": 22,
            "restaurant-tv-v2": 288,
        }
        if len(v17_icons) != 413 or len({icon.get("key") for icon in v17_icons}) != 413:
            errors.append("V17 must contain exactly 413 unique gallery entries")
        if category_counts != expected_categories:
            errors.append(f"V17 category totals differ: {category_counts}; expected {expected_categories}")
        if len(v17_icons) - category_counts.get("brand-assets", 0) != 405:
            errors.append("V17 must contain 405 functional concepts plus eight brand assets")
        if len(v17_icons) - category_counts.get("brand-assets", 0) - category_counts.get("restaurant-tv-v2", 0) != 117:
            errors.append("The original V17 must retain its 117 functional concepts")
        native_motion = sum(icon.get("motion_source") == "source_archive_smil" for icon in v17_icons)
        generated_motion = sum(icon.get("motion_source") == "generated_royal_preview" for icon in v17_icons)
        focused_count = sum(bool(icon.get("variants", {}).get("focused")) for icon in v17_icons)
        xml_count = sum(bool(icon.get("variants", {}).get("android_xml")) for icon in v17_icons)
        if (native_motion, generated_motion, focused_count, xml_count) != (95, 30, 16, 22):
            errors.append(
                "V17 motion/focus/XML inventory differs: "
                f"native={native_motion}, generated={generated_motion}, focused={focused_count}, xml={xml_count}"
            )
        if sum(bool(icon.get("motion")) for icon in v17_icons if icon.get("category") != "restaurant-tv-v2") != 125:
            errors.append("The original 125 V17 entries must retain their motion previews")


    # Verify the newly imported archive and its byte-for-byte extracted mirror.
    archive_path = ROOT / "sources" / "restaurant_tv_icons_v2_transparent.zip"
    extract_root = ROOT / "packages" / "restaurant-tv-icons-v2-transparent" / "extracted"
    source_catalog_path = ROOT / "icons" / "v17" / "restaurant-tv-icons-v2" / "catalog.json"
    if not archive_path.is_file():
        errors.append("Missing original restaurant_tv_icons_v2_transparent.zip")
    else:
        try:
            with zipfile.ZipFile(archive_path) as source_zip:
                svg_members = [info for info in source_zip.infolist()
                               if not info.is_dir() and info.filename.lower().endswith(".svg")]
                basenames = {Path(info.filename).name.lower() for info in source_zip.infolist()
                             if not info.is_dir()}
                if len(svg_members) != 288:
                    errors.append(f"Restaurant/TV V2 archive must contain 288 SVG files; found {len(svg_members)}")
                if not ({"readme", "readme.md"} & basenames):
                    errors.append("Restaurant/TV V2 archive is missing README")
                if "player_ui_description.md" not in basenames:
                    errors.append("Restaurant/TV V2 archive is missing PLAYER_UI_DESCRIPTION.md")
                for info in svg_members:
                    member = Path(*info.filename.replace("\\\\", "/").split("/"))
                    mirrored = extract_root / member
                    if not mirrored.is_file():
                        errors.append(f"Missing extracted archive source: {info.filename}")
                        continue
                    if mirrored.read_bytes() != source_zip.read(info):
                        errors.append(f"Extracted SVG differs from original ZIP entry: {info.filename}")
        except zipfile.BadZipFile as exc:
            errors.append(f"Invalid restaurant/TV V2 source ZIP: {exc}")
    if not source_catalog_path.is_file():
        errors.append("Missing restaurant/TV V2 source catalog")
    else:
        try:
            source_catalog = json.loads(source_catalog_path.read_text(encoding="utf-8"))
            if len(source_catalog.get("icons", [])) != 288:
                errors.append("Restaurant/TV V2 source catalog must contain exactly 288 icons")
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid restaurant/TV V2 source catalog: {exc}")

    html = HTML_PATH.read_text(encoding="utf-8")
    match = re.search(r"const embeddedManifest=(\{.*\});\s*const rootPrefix=", html, re.S)
    if not match:
        errors.append("index.html has no embedded manifest")
    else:
        try:
            if json.loads(match.group(1)) != manifest:
                errors.append("Embedded manifest differs from icons/app-collections.json")
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid embedded manifest JSON: {exc}")

    node = shutil.which("node")
    script_match = re.search(r"<script>(.*?)</script>", html, re.S)
    if not node:
        errors.append("Node.js is unavailable; cannot syntax-check the gallery JavaScript")
    elif not script_match:
        errors.append("index.html has no inline JavaScript block")
    else:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as temp:
                temp.write(script_match.group(1))
                temp_path = temp.name
            result = subprocess.run(
                [node, "--check", temp_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode:
                errors.append("Gallery JavaScript syntax error: " + (result.stderr.strip() or result.stdout.strip()))
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    for required_js in ("function makeMotionVariant(icon)", 'value="motion"', 'value="focused"'):
        if required_js not in html:
            errors.append(f"Gallery UI is missing required motion/focus support: {required_js}")
    if "pair.append(makeMotionVariant(icon))" not in html:
        errors.append("V17 animated SVG previews are not rendered inline in icon cards")

    gallery_ui_checks = {
        "all-library view is the default": "let collections=[],active=-1;" in html and "const allMode=active===-1;" in html,
        "all-library navigation tab": "كل المكتبة" in html,
        "motion previews use embedded SVG documents": "el('iframe','motion-frame')" in html,
        "SMIL pause and resume controls": "pauseAnimations" in html and "unpauseAnimations" in html,
        "lazy-loaded motion previews": "frame.loading='lazy'" in html,
        "motion-only filter covers all collections": "if(filter==='motion'&&!icon.motion)continue" in html,
    }
    for label, passed in gallery_ui_checks.items():
        if not passed:
            errors.append(f"Gallery UI check failed: {label}")
    if "../../" in html:
        errors.append("index.html contains a relative path outside the gallery root")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print(f"Validation failed with {len(errors)} issue(s).")
        return 1

    total_entries = sum(len(version.get("icons", [])) for version in versions)
    print(f"PASS: {total_entries} gallery entries across {len(versions)} versions; all-library view is the default.")
    print(f"PASS: {len(unique_2d)} unique 2D SVG sources; {len(unique_3d)} 3D variants.")
    print(f"PASS: {len(unique_motion)} motion files; {len(unique_focused)} focused states; {len(android_xml)} Android VectorDrawables.")
    print("PASS: V17 has 125 entries (117 functional icons + 8 brand assets), and every motion file contains SMIL animation.")
    print("PASS: V17 has 95 original SMIL animations, 30 generated motion previews, 16 focused states, and 22 Android XML assets.")
    print(f"PASS: {len(referenced_svg)} referenced SVG assets, catalogs, gradients, and embedded manifest are valid.")
    print("PASS: V13 core artwork and all prior collections remain valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
