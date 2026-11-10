#!/usr/bin/env python3
"""Validate the public ROYAL Design icon gallery without third-party packages."""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "icons" / "app-collections.json"
HTML_PATH = ROOT / "index.html"
EXPECTED_VERSIONS = [f"V{i}" for i in range(2, 18)]
PLACEHOLDERS = {"Video stream", "Stream source", "Audio track", "Fullscreen", "Video player", "Refresh list", "Subtitles"}
SHAPES = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}

def main():
    errors = []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    versions = manifest.get("versions", [])
    if [v.get("version") for v in versions] != EXPECTED_VERSIONS:
        errors.append("Version tabs must be ordered V2 through V17")

    icons = [icon for collection in versions for icon in collection.get("icons", [])]
    unique_2d = {icon.get("variants", {}).get("2d") for icon in icons if icon.get("variants", {}).get("2d")}
    unique_3d = {icon.get("variants", {}).get("3d") for icon in icons if icon.get("variants", {}).get("3d")}
    android_xml = {icon.get("variants", {}).get("android_xml") for icon in icons if icon.get("variants", {}).get("android_xml")}
    totals = manifest.get("totals", {})
    expected = {
        "app_collections": len(versions),
        "concepts": len(unique_2d),
        "flat_svg": len(unique_2d),
        "dimensional_svg": len(unique_3d),
    }
    for key, value in expected.items():
        if totals.get(key) != value:
            errors.append(f"totals.{key} is {totals.get(key)}, expected {value}")

    referenced = set()
    for collection in versions:
        is_v17 = collection.get("version") == "V17"
        keys = [icon.get("key") for icon in collection.get("icons", [])]
        if len(keys) != len(set(keys)):
            errors.append(f"Duplicate icon keys in {collection.get('version')}")
        for icon in collection.get("icons", []):
            variants = icon.get("variants", {})
            required_styles = ("2d", "android_xml") if is_v17 else ("2d", "3d")
            for style in required_styles:
                rel = variants.get(style)
                if not rel or rel.startswith("/") or ".." in Path(rel).parts:
                    errors.append(f"Invalid {style} asset path in {collection.get('version')}:{icon.get('key')}")
                elif style == "android_xml":
                    path = ROOT / rel
                    if not path.is_file():
                        errors.append(f"Missing Android XML asset: {rel}")
                    else:
                        try:
                            root = ET.parse(path).getroot()
                            if not root.tag.lower().endswith("vector"):
                                errors.append(f"Invalid Android VectorDrawable root: {rel}")
                            if not any(el.tag.rsplit("}", 1)[-1] == "path" and el.attrib.get("pathData") for el in root.iter()):
                                errors.append(f"Android VectorDrawable has no pathData: {rel}")
                        except ET.ParseError as exc:
                            errors.append(f"Invalid Android XML {rel}: {exc}")
                else:
                    referenced.add(rel)
            if icon.get("motion"):
                referenced.add(icon["motion"])
            if icon.get("shared_from") and not any(v.get("version") == icon["shared_from"] for v in versions):
                errors.append(f"Unknown shared source version {icon['shared_from']}")

        catalog_path = ROOT / collection.get("collection_path", "") / "catalog.json"
        if not catalog_path.is_file():
            errors.append(f"Missing per-collection catalog: {catalog_path.relative_to(ROOT)}")
        else:
            try:
                catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
                if catalog.get("icons") != collection.get("icons"):
                    errors.append(f"Stale catalog for {collection.get('version')}")
            except json.JSONDecodeError as exc:
                errors.append(f"Invalid catalog JSON {catalog_path}: {exc}")

    for rel in sorted(referenced):
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"Missing gallery asset: {rel}")
            continue
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            errors.append(f"Invalid XML/SVG {rel}: {exc}")
            continue
        if not root.tag.lower().endswith("svg"):
            errors.append(f"Wrong SVG root in {rel}")
        tags = [element.tag.rsplit("}", 1)[-1] for element in root.iter()]
        if not any(tag in SHAPES for tag in tags):
            errors.append(f"No vector geometry in {rel}")
        text_content = " ".join(part.strip() for part in root.itertext() if part.strip())
        if any(marker in text_content for marker in PLACEHOLDERS):
            errors.append(f"Placeholder text instead of artwork in {rel}")
        ids = {element.attrib["id"] for element in root.iter() if "id" in element.attrib}
        refs = re.findall(r"url\(#([^)]+)\)", path.read_text(encoding="utf-8"))
        missing = sorted(set(refs) - ids)
        if missing:
            errors.append(f"Unresolved SVG references in {rel}: {missing}")

    required_v13 = {"channel-list", "stream", "player", "fullscreen", "subtitles", "audio", "source", "refresh"}
    v13 = next((v for v in versions if v.get("version") == "V13"), None)
    if not v13 or not required_v13.issubset({i.get("key") for i in v13.get("icons", [])}):
        errors.append("V13 is missing one or more of its eight RS TV core icons")
    v17 = next((v for v in versions if v.get("version") == "V17"), None)
    if not v17 or len(v17.get("icons", [])) != 22 or len(android_xml) < 22:
        errors.append("V17 must contain all 22 SVG/Android XML source pairs")

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
    if "../../" in html:
        errors.append("index.html contains a relative path outside the gallery root")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print(f"Validation failed with {len(errors)} issue(s).")
        return 1
    print(f"PASS: {len(versions)} versions; {len(unique_2d)} SVG concepts; {len(unique_3d)} 3D SVGs; {len(android_xml)} Android VectorDrawables.")
    print(f"PASS: {len(referenced)} referenced SVGs, motion assets, and per-app catalogs exist and validate.")
    print("PASS: V13 core artwork, V17 Android XML, SVG geometry, gradient references and embedded manifest are valid.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
