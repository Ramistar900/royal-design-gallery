#!/usr/bin/env python3
"""Create and verify the complete source index for the restaurant/TV V2 ZIP."""
from __future__ import annotations

import argparse
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "sources" / "restaurant_tv_icons_v2_transparent.zip"
EXTRACT = ROOT / "packages" / "restaurant-tv-icons-v2-transparent" / "extracted"
INDEX = EXTRACT / "INDEX.txt"

EXPECTED_GROUPS = {
    "store/static": 37,
    "store/animated": 37,
    "tv/static": 42,
    "tv/animated": 42,
    "launcher_ui/static": 16,
    "launcher_ui/animated": 16,
    "launcher_ui/focused": 16,
    "player/music/static": 21,
    "player/music/animated": 21,
    "player/video/static": 20,
    "player/video/animated": 20,
}
EXPECTED_SVG = 288
EXPECTED_DOCS = {"README.md", "PLAYER_UI_DESCRIPTION.md"}


def read_inventory() -> tuple[list[str], dict[str, bytes]]:
    if not ARCHIVE.is_file():
        raise SystemExit(f"Missing source ZIP: {ARCHIVE.relative_to(ROOT)}")
    with zipfile.ZipFile(ARCHIVE) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise SystemExit(f"Corrupt ZIP member: {bad_member}")
        entries: dict[str, bytes] = {}
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            path = PurePosixPath(name)
            if path.is_absolute() or not path.parts or ".." in path.parts:
                raise SystemExit(f"Unsafe path in ZIP: {name}")
            if name in entries:
                raise SystemExit(f"Duplicate ZIP path: {name}")
            entries[name] = archive.read(info)
    names = sorted(entries)
    if len(names) != 290:
        raise SystemExit(f"Source ZIP must contain 290 files; found {len(names)}")
    svg_names = [name for name in names if name.lower().endswith(".svg")]
    if len(svg_names) != EXPECTED_SVG:
        raise SystemExit(f"Expected {EXPECTED_SVG} SVGs; found {len(svg_names)}")
    docs = {PurePosixPath(name).name for name in names if not name.lower().endswith(".svg")}
    if docs != EXPECTED_DOCS:
        raise SystemExit(f"Expected only README.md and PLAYER_UI_DESCRIPTION.md; found {sorted(docs)}")

    group_counts = Counter(
        PurePosixPath(name).parent.as_posix()
        for name in svg_names
    )
    if dict(group_counts) != EXPECTED_GROUPS:
        raise SystemExit(
            "Source group inventory mismatch: "
            f"found {dict(sorted(group_counts.items()))}; "
            f"expected {dict(sorted(EXPECTED_GROUPS.items()))}"
        )
    return names, entries


def render_index(names: list[str]) -> str:
    lines = [
        "ROYAL DESIGN — RESTAURANT / TV ICONS V2",
        "Source: restaurant_tv_icons_v2_transparent.zip",
        "",
        "VERIFIED SOURCE INVENTORY",
        "ZIP files: 290",
        "SVG files: 288",
        "Documentation files: 2",
        "",
        "SVG COUNTS BY GROUP",
    ]
    lines.extend(f"{group}: {count}" for group, count in EXPECTED_GROUPS.items())
    lines.extend([
        "",
        "DOCUMENTATION",
        "- README.md",
        "- PLAYER_UI_DESCRIPTION.md",
        "",
        "COMPLETE SOURCE FILE LIST",
    ])
    lines.extend(f"- {name}" for name in names)
    lines.extend([
        "",
        "This INDEX.txt is generated from the verified ZIP inventory.",
        "The original ZIP contains 290 files; the extracted repository folder",
        "contains those 290 files plus this generated index (291 files total).",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write the generated index")
    parser.add_argument("--check", action="store_true", help="verify the committed index")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")

    names, entries = read_inventory()
    for name, data in entries.items():
        mirror = EXTRACT.joinpath(*PurePosixPath(name).parts)
        if not mirror.is_file():
            raise SystemExit(f"Missing extracted source file: {name}")
        if mirror.read_bytes() != data:
            raise SystemExit(f"Extracted file differs from ZIP source: {name}")

    expected_index = render_index(names)
    if args.write:
        INDEX.parent.mkdir(parents=True, exist_ok=True)
        INDEX.write_text(expected_index, encoding="utf-8")
    elif not INDEX.is_file() or INDEX.read_text(encoding="utf-8") != expected_index:
        raise SystemExit("INDEX.txt is missing or does not match the verified ZIP inventory.")

    expected_files = set(names) | {"INDEX.txt"}
    actual_files = {
        path.relative_to(EXTRACT).as_posix()
        for path in EXTRACT.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        missing = sorted(expected_files - actual_files)
        extra = sorted(actual_files - expected_files)
        raise SystemExit(f"Extracted file set mismatch; missing={missing}, extra={extra}")

    print("PASS: source ZIP has 290 files (288 SVG + 2 documentation files).")
    print("PASS: all 288 SVG group counts match the approved inventory.")
    print("PASS: all 290 original files are extracted byte-for-byte.")
    print("PASS: generated INDEX.txt is present and matches the ZIP inventory.")
    print("PASS: extracted folder contains exactly 291 files including INDEX.txt (290 ZIP files + 1 generated index).")


if __name__ == "__main__":
    main()
