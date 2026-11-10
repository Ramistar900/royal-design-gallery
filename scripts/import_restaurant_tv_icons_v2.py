#!/usr/bin/env python3
"""Import the original 288-SVG restaurant/TV package into V17 without altering source artwork."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_URL = "https://raw.githubusercontent.com/Ramistar900/royal-design/main/restaurant_tv_icons_v2_transparent.zip"
EXPECTED_GIT_BLOB_SHA = "0dffbc757d0146aad7d17f9498b9b711743afe9a"
ARCHIVE_PATH = ROOT / "sources" / "restaurant_tv_icons_v2_transparent.zip"
EXTRACT_ROOT = ROOT / "packages" / "restaurant-tv-icons-v2-transparent" / "extracted"
MANIFEST_PATH = ROOT / "icons" / "app-collections.json"
V17_CATALOG_PATH = ROOT / "icons" / "v17" / "royal-library" / "catalog.json"
SOURCE_CATALOG_PATH = ROOT / "icons" / "v17" / "restaurant-tv-icons-v2" / "catalog.json"
HTML_PATH = ROOT / "index.html"
README_PATH = ROOT / "README.md"
SOURCE_NOTE_PATH = ROOT / "sources" / "V17_IMPORT_SOURCE.md"
EXPECTED_SVG_COUNT = 288
SHAPE_TAGS = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
ANIMATION_TAGS = {"animate", "animatetransform", "animatemotion", "set"}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def fetch_verified_archive() -> bytes:
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"User-Agent": "ROYAL-Design-Gallery-Importer/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    git_blob = hashlib.sha1(
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()
    if git_blob != EXPECTED_GIT_BLOB_SHA:
        raise SystemExit(
            "Source ZIP changed or downloaded incorrectly: "
            f"Git blob SHA {git_blob}, expected {EXPECTED_GIT_BLOB_SHA}"
        )
    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_PATH.write_bytes(data)
    return data


def main() -> None:
    archive_data = fetch_verified_archive()
    if EXTRACT_ROOT.exists():
        shutil.rmtree(EXTRACT_ROOT)
    EXTRACT_ROOT.mkdir(parents=True, exist_ok=True)

    icons = []
    archive_svg_paths = []
    archive_doc_names = set()
    seen_keys = set()
    native_motion = 0

    try:
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(archive_data)) as archive:
            bad_member = archive.testzip()
            if bad_member:
                raise SystemExit(f"Corrupt ZIP member: {bad_member}")
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                member = PurePosixPath(name)
                if member.is_absolute() or not member.parts or ".." in member.parts:
                    raise SystemExit(f"Unsafe path in source ZIP: {name}")
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    raise SystemExit(f"Symbolic links are not allowed in source ZIP: {name}")

                data = archive.read(info)
                target = EXTRACT_ROOT.joinpath(*member.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

                basename = member.name.lower()
                if basename in {"readme", "readme.md"}:
                    archive_doc_names.add("README")
                if basename == "player_ui_description.md":
                    archive_doc_names.add("PLAYER_UI_DESCRIPTION.md")

                if member.suffix.lower() != ".svg":
                    continue

                try:
                    root = ET.fromstring(data)
                except ET.ParseError as exc:
                    raise SystemExit(f"Invalid SVG {name}: {exc}")
                if local_name(root.tag) != "svg":
                    raise SystemExit(f"Unexpected SVG root in {name}: {root.tag}")
                tags = {local_name(node.tag) for node in root.iter()}
                if not tags.intersection(SHAPE_TAGS):
                    raise SystemExit(f"SVG has no vector geometry: {name}")

                archive_svg_paths.append(name)
                relative = (Path("packages") / "restaurant-tv-icons-v2-transparent"
                            / "extracted" / Path(*member.parts)).as_posix()
                slug = re.sub(r"[^a-z0-9]+", "-", member.with_suffix("").as_posix().lower()).strip("-")
                key = "restaurant-tv-v2-" + (slug or hashlib.sha1(name.encode("utf-8")).hexdigest()[:12])
                if key in seen_keys:
                    raise SystemExit(f"Duplicate generated icon key: {key}")
                seen_keys.add(key)

                stem = member.stem
                label_en = re.sub(r"[_-]+", " ", stem).strip().title() or stem
                icon = {
                    "key": key,
                    "label_ar": "أيقونة مطعم وتلفاز · " + label_en,
                    "label_en": label_en,
                    "category": "restaurant-tv-v2",
                    "source_group": "/".join(member.parts[:-1]) or "root",
                    "source_archive": "sources/restaurant_tv_icons_v2_transparent.zip",
                    "source_archive_path": name,
                    "variants": {"2d": relative},
                    "rights": {
                        "origin": "uploaded_royal_package",
                        "license": "ROYAL_SOURCE_PACKAGE",
                        "authoring_note": "Original SVG bytes preserved from restaurant_tv_icons_v2_transparent.zip; no tracing or artwork replacement."
                    },
                    "status": "source_original_svg"
                }
                if tags.intersection(ANIMATION_TAGS):
                    icon["motion"] = relative
                    icon["motion_source"] = "source_archive_smil_restaurant_tv_v2"
                    icon["motion_note"] = "Native source animation preserved unchanged."
                    native_motion += 1
                icons.append(icon)
    except zipfile.BadZipFile as exc:
        raise SystemExit(f"Invalid source ZIP: {exc}")

    if len(archive_svg_paths) != EXPECTED_SVG_COUNT:
        raise SystemExit(
            f"Expected exactly {EXPECTED_SVG_COUNT} original SVG files, found {len(archive_svg_paths)}"
        )
    if archive_doc_names != {"README", "PLAYER_UI_DESCRIPTION.md"}:
        raise SystemExit(
            "Source documentation is incomplete: "
            + ", ".join(sorted(archive_doc_names))
        )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    versions = manifest.get("versions", [])
    collection = next((item for item in versions if item.get("version") == "V17"), None)
    if not collection:
        raise SystemExit("V17 collection not found; refusing to create an orphaned import.")
    base_icons = [
        item for item in collection.get("icons", [])
        if item.get("category") != "restaurant-tv-v2"
    ]
    if len(base_icons) != 125:
        raise SystemExit(
            f"Expected the preserved 125 original V17 entries before this import, found {len(base_icons)}"
        )
    if len({item.get("key") for item in base_icons}) != 125:
        raise SystemExit("Original V17 contains duplicate keys; import stopped.")

    icons.sort(key=lambda item: item["source_archive_path"].lower())
    collection_icons = base_icons + icons
    if len(collection_icons) != 413 or len({item["key"] for item in collection_icons}) != 413:
        raise SystemExit("Combined V17 catalog must contain 413 unique entries.")

    collection["icons"] = collection_icons
    collection["description_ar"] = (
        "413 بطاقة: 125 بطاقة V17 الأصلية، إضافة إلى 288 ملف SVG أصلياً لمكتبة المطاعم والتلفاز؛ "
        "الحركة محفوظة فقط عندما تكون موجودة فعلياً في المصدر"
    )
    collection["source_archives"] = list(collection.get("source_archives", []))
    if "sources/restaurant_tv_icons_v2_transparent.zip" not in collection["source_archives"]:
        collection["source_archives"].append("sources/restaurant_tv_icons_v2_transparent.zip")
    notes = collection.setdefault("source_archive_notes", {})
    notes["restaurant_tv_icons_v2_transparent.zip"] = (
        "288 original SVG icon files plus README and PLAYER_UI_DESCRIPTION.md. "
        "All paths and SVG bytes are preserved under packages/restaurant-tv-icons-v2-transparent/extracted/."
    )
    totals = collection.get("asset_totals", {})
    totals.update({
        "gallery_entries": 413,
        "functional_icon_concepts": 405,
        "brand_assets": 8,
        "native_smil_motion_previews": 95,
        "generated_motion_previews": 30,
        "focused_states": 16,
        "android_vector_drawables": 22,
        "source_archive_svg_files": 524,
        "restaurant_tv_v2_svg_files": 288,
        "restaurant_tv_v2_native_smil_previews": native_motion,
        "motion_previews_total": sum(bool(item.get("motion")) for item in collection_icons),
        "duplicate_ui_backup_archives": 1
    })
    collection["asset_totals"] = totals

    V17_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    V17_CATALOG_PATH.write_text(
        json.dumps(collection, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    SOURCE_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_CATALOG_PATH.write_text(
        json.dumps({
            "version": "V17",
            "slug": "restaurant-tv-icons-v2",
            "name_ar": "أيقونات المطاعم والتلفاز · الحزمة الثانية",
            "description_ar": "288 ملف SVG أصلياً مع ملفات README ووصف واجهة المشغل",
            "source_archive": "sources/restaurant_tv_icons_v2_transparent.zip",
            "extracted_root": "packages/restaurant-tv-icons-v2-transparent/extracted",
            "icons": icons
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    unique_2d = {
        item["variants"]["2d"]
        for version in versions for item in version.get("icons", [])
        if item.get("variants", {}).get("2d")
    }
    unique_3d = {
        item["variants"]["3d"]
        for version in versions for item in version.get("icons", [])
        if item.get("variants", {}).get("3d")
    }
    unique_motion = {
        item["motion"]
        for version in versions for item in version.get("icons", [])
        if item.get("motion")
    }
    unique_focused = {
        item["variants"]["focused"]
        for version in versions for item in version.get("icons", [])
        if item.get("variants", {}).get("focused")
    }
    unique_xml = {
        item["variants"]["android_xml"]
        for version in versions for item in version.get("icons", [])
        if item.get("variants", {}).get("android_xml")
    }
    manifest.setdefault("totals", {}).update({
        "app_collections": len(versions),
        "concepts": len(unique_2d),
        "flat_svg": len(unique_2d),
        "dimensional_svg": len(unique_3d),
        "motion_svg": len(unique_motion),
        "focused_svg": len(unique_focused),
        "android_xml": len(unique_xml),
        "v17_entries": 413,
        "v17_icon_concepts": 405
    })
    manifest["title"] = "ROYAL Design · V2–V17 Complete Icon Collections"
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    html = HTML_PATH.read_text(encoding="utf-8")
    embedded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
    html, replaced = re.subn(
        r"const embeddedManifest=(\{.*\});\s*const rootPrefix=",
        lambda match: "const embeddedManifest=" + embedded + ";\nconst rootPrefix=",
        html, count=1, flags=re.S
    )
    if replaced != 1:
        raise SystemExit("Could not refresh the embedded gallery manifest.")
    html, replaced = re.subn(
        r"<p>مكتبة ROYAL Design.*?</p>",
        "<p>مكتبة ROYAL Design تضم 16 إصداراً. يحتوي V17 على 413 بطاقة: 125 بطاقة أصلية محفوظة و288 أيقونة SVG أصلية للمطاعم والتلفاز. تظهر الحركة فقط للأصول التي تتضمن حركة أصلية؛ وتبقى بقية الرسومات ثابتة دون تعديل.</p>",
        html, count=1, flags=re.S
    )
    if replaced != 1:
        raise SystemExit("Could not update the gallery introduction.")
    HTML_PATH.write_text(html, encoding="utf-8")

    readme = README_PATH.read_text(encoding="utf-8")
    readme = re.sub(
        r"(?m)^- \*\*V17:\*\*.*$",
        "- **V17:** المكتبة الملكية الكاملة — 413 بطاقة، تشمل 125 بطاقة أصلية و288 أيقونة SVG أصلية للمطاعم والتلفاز، مع وصف واجهة المشغل وملفات المصدر.",
        readme
    )
    readme = re.sub(
        r"(?m)^- 125 بطاقة في V17:.*$",
        "- 413 بطاقة في V17: 405 مفاهيم وظيفية (117 من المكتبة السابقة و288 من حزمة المطاعم والتلفاز) و8 أصول هوية ولافتات.",
        readme
    )
    if "restaurant_tv_icons_v2_transparent.zip" not in readme:
        readme += (
            "\n\n## حزمة المطاعم والتلفاز V2\n\n"
            "- المصدر الأصلي: sources/restaurant_tv_icons_v2_transparent.zip.\n"
            "- 288 ملف SVG أصلياً محفوظة دون تعديل في packages/restaurant-tv-icons-v2-transparent/extracted/.\n"
            "- ملفا README وPLAYER_UI_DESCRIPTION.md محفوظان بمساريهما الأصليين داخل مجلد الاستخراج.\n"
            "- فهرس الحزمة: icons/v17/restaurant-tv-icons-v2/catalog.json.\n"
            "- لا تُنشأ حركة اصطناعية لهذه الأيقونات؛ تُعرض الحركة فقط عند وجود SMIL أصلي.\n"
        )
    README_PATH.write_text(readme, encoding="utf-8")

    source_note = SOURCE_NOTE_PATH.read_text(encoding="utf-8")
    addition = (
        "\n\n## Restaurant / TV icons V2 source\n\n"
        "- sources/restaurant_tv_icons_v2_transparent.zip: original archive, verified against its Git blob SHA.\n"
        "- Exactly 288 SVG files are preserved under packages/restaurant-tv-icons-v2-transparent/extracted/ with archive-relative paths.\n"
        "- The original README and PLAYER_UI_DESCRIPTION.md are preserved in the extracted tree.\n"
        "- Gallery catalog: icons/v17/restaurant-tv-icons-v2/catalog.json; all 288 assets are also included in the main V17 catalog.\n"
        "- Native SMIL is exposed only when present in the source. Static SVGs are never given fabricated motion.\n"
    )
    if "## Restaurant / TV icons V2 source" not in source_note:
        source_note += addition
    SOURCE_NOTE_PATH.write_text(source_note, encoding="utf-8")

    print("Restaurant/TV V2 import verified:")
    print(f"  original SVG files: {len(icons)}")
    print(f"  native SMIL previews: {native_motion}")
    print(f"  documentation: {', '.join(sorted(archive_doc_names))}")
    print(f"  combined V17 cards: {len(collection_icons)}")
    print("  original SVG bytes and archive-relative paths preserved")


if __name__ == "__main__":
    main()
