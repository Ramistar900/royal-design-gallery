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
EXPECTED_VERSIONS = [f"V{i}" for i in range(2, 17)]
PLACEHOLDERS = {"Video stream", "Stream source", "Audio track", "Fullscreen", "Video player", "Refresh list", "Subtitles"}
SHAPES = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}

def main():
    errors = []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    versions = manifest.get("versions", [])
    if [v.get("version") for v in versions] != EXPECTED_VERSIONS:
        errors.append("Version tabs must be ordered V2 through V15")

    icons = [icon for collection in versions for icon in collection.get("icons", [])]
    unique_2d = {icon.get("variants", {}).get("2d") for icon in icons}
    unique_3d = {icon.get("variants", {}).get("3d") for icon in icons}
    concepts = len(unique_2d)
    totals = manifest.get("totals", {})
    expected = {
        "app_collections": len(versions),
        "concepts": concepts,
        "flat_svg": len(unique_2d),
        "dimensional_svg": len(unique_3d),
    }
    for key, value in expected.items():
        if totals.get(key) != value:
            errors.append(f"totals.{key} is {totals.get(key)}, expected {value}")
    if None in unique_2d or None in unique_3d or len(unique_2d) != len(unique_3d):
        errors.append("Every unique concept must have one 2D and one 3D variant")

    referenced = set()
    for collection in versions:
        keys = [icon.get("key") for icon in collection.get("icons", [])]
        if len(keys) != len(set(keys)):
            errors.append(f"Duplicate icon keys in {collection.get('version')}")
        for icon in collection.get("icons", []):
            variants = icon.get("variants", {})
            for style in ("2d", "3d"):
                rel = variants.get(style)
                if not rel or rel.startswith("/") or ".." in Path(rel).parts:
                    errors.append(f"Invalid {style} asset path in {collection.get('version')}:{icon.get('key')}")
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
        if not root.tag.endswith("svg"):
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
    print(f"PASS: {len(versions)} versions; {concepts} unique concepts; {len(unique_2d)} 2D and {len(unique_3d)} 3D SVGs.")
    print(f"PASS: {len(referenced)} referenced SVGs, motion assets, and per-app catalogs exist and validate.")
    print("PASS: V13 core artwork, SVG geometry, gradient references and embedded manifest are valid.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
