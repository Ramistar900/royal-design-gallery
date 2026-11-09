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
EXPECTED_VERSIONS = [f"V{i}" for i in range(2, 16)]
PLACEHOLDERS = {
    "Video stream", "Stream source", "Audio track", "Fullscreen",
    "Video player", "Refresh list", "Subtitles",
}
SHAPES = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}

def fail(message):
    print(f"FAIL: {message}")
    return False

def main():
    errors = []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    versions = manifest.get("versions", [])
    actual_versions = [item.get("version") for item in versions]
    if actual_versions != EXPECTED_VERSIONS:
        errors.append(f"Expected ordered versions {EXPECTED_VERSIONS}, got {actual_versions}")

    concepts = sum(len(item.get("icons", [])) for item in versions)
    totals = manifest.get("totals", {})
    for key in ("concepts", "flat_svg", "dimensional_svg"):
        if totals.get(key) != concepts:
            errors.append(f"totals.{key}={totals.get(key)} but manifest contains {concepts} concepts")
    if totals.get("app_collections") != len(versions):
        errors.append("totals.app_collections does not match the number of versions")

    referenced = set()
    for collection in versions:
        for icon in collection.get("icons", []):
            variants = icon.get("variants", {})
            for style in ("2d", "3d"):
                rel = variants.get(style)
                if not rel:
                    errors.append(f"{collection.get('version')}:{icon.get('key')} missing {style} path")
                    continue
                if rel.startswith("/") or ".." in Path(rel).parts:
                    errors.append(f"Unsafe asset path: {rel}")
                    continue
                referenced.add(rel)
            motion = icon.get("motion")
            if motion:
                referenced.add(motion)

    for rel in sorted(referenced):
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"Missing gallery asset: {rel}")
            continue
        try:
            tree = ET.parse(path)
            root = tree.getroot()
        except ET.ParseError as exc:
            errors.append(f"Invalid XML/SVG {rel}: {exc}")
            continue
        if not root.tag.endswith("svg"):
            errors.append(f"Wrong root element in {rel}")
        local_tags = [element.tag.rsplit("}", 1)[-1] for element in root.iter()]
        if not any(tag in SHAPES for tag in local_tags):
            errors.append(f"No drawable vector geometry in {rel}")
        text_content = " ".join(part.strip() for part in root.itertext() if part.strip())
        if any(marker in text_content for marker in PLACEHOLDERS):
            errors.append(f"Placeholder text instead of artwork in {rel}")
        ids = {element.attrib["id"] for element in root.iter() if "id" in element.attrib}
        refs = re.findall(r"url\(#([^)]+)\)", path.read_text(encoding="utf-8"))
        missing_refs = sorted(set(refs) - ids)
        if missing_refs:
            errors.append(f"Unresolved SVG paint/filter references in {rel}: {missing_refs}")

    # Check every V13 icon specifically: this collection previously contained blank text placeholders.
    v13 = next((v for v in versions if v.get("version") == "V13"), None)
    if not v13 or len(v13.get("icons", [])) != 8:
        errors.append("V13 must contain all eight RS TV icon concepts")

    html = HTML_PATH.read_text(encoding="utf-8")
    match = re.search(r"const embeddedManifest=(\{.*\});\s*const rootPrefix=", html, re.S)
    if not match:
        errors.append("index.html is missing the embedded gallery manifest")
    else:
        try:
            embedded = json.loads(match.group(1))
            if embedded != manifest:
                errors.append("Embedded manifest in index.html differs from icons/app-collections.json")
        except json.JSONDecodeError as exc:
            errors.append(f"Embedded manifest is invalid JSON: {exc}")
    if "../../icons/" in html or "../../" in html:
        errors.append("index.html contains a relative path that points outside the public gallery")

    if errors:
        for item in errors:
            fail(item)
        print(f"Validation failed with {len(errors)} issue(s).")
        return 1

    print(f"PASS: {len(versions)} versions, {concepts} concepts, {concepts * 2} paired SVG variants.")
    print(f"PASS: {len(referenced)} referenced SVG assets exist, parse, contain vector geometry and resolve all paint references.")
    print("PASS: V13 placeholders removed; manifest, page embed and gallery paths agree.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
