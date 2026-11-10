#!/usr/bin/env python3
"""Audit and classify the extracted ROYAL Design icon package."""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import re
import xml.etree.ElementTree as ET

ROOT = pathlib.Path("packages/royal-design-shared-icon-package")
EXTRACTED = ROOT / "extracted"

APP_MAP = [
    {
        "app": "Almalaki",
        "fit": "primary-candidate",
        "source": "restaurant_tv_3d_icons/icon_pack/store/",
        "scope": "Restaurant and cafe functional icons: menu, food, coffee, cart, orders, delivery, payment, table, profile, and shared controls.",
        "caveat": "The pack uses orange/gold glossy tiles, while Almalaki's current visual identity includes emerald elements. Treat as optional library assets; do not replace the current app logo, banners, or established emerald styling."
    },
    {
        "app": "ROYAL TV",
        "fit": "primary-candidate",
        "source": "restaurant_tv_3d_icons/icon_pack/tv/",
        "scope": "TV playback, channel navigation, live, guide, remote, cast, source, volume, mute, lock, timer, and common TV controls.",
        "caveat": "Functional icon set only. It is not a verified ROYAL TV brand logo or complete screen design."
    },
    {
        "app": "RS TV / Sinjar TV",
        "fit": "primary-candidate",
        "source": "restaurant_tv_3d_icons/icon_pack/tv/",
        "scope": "Reuse the same TV controls as ROYAL TV through shared references; do not make a second copy of the source files.",
        "caveat": "The pack does not contain a dedicated RS TV / Sinjar brand mark, watermark, or channel-country flag system."
    },
    {
        "app": "ROYAL+ Launcher",
        "fit": "primary",
        "source": "restaurant_tv_launcher_ui_icons/launcher_ui_pack/",
        "scope": "16 launcher navigation/content icons, each supplied as static, animated, and focused states.",
        "caveat": "This is the strongest direct match in the package. Keep all three states; use focused state for TV remote selection. The duplicate second archive is byte-identical and should be treated as a backup, not a second variant."
    },
    {
        "app": "ROYAL AUDIO",
        "fit": "limited-reuse",
        "source": "restaurant_tv_3d_icons/icon_pack/tv/",
        "scope": "Only the media-control subset: play, pause, stop, next, previous, forward, rewind, volume up/down, and mute.",
        "caveat": "No dedicated ROYAL AUDIO identity, soundscape artwork, or audio-category icon set is present. These are controls only and do not introduce voice/audio content."
    },
    {
        "app": "RAMI Developer",
        "fit": "shared-controls-only",
        "source": "restaurant_tv_3d_icons/icon_pack/store/ and icon_pack/tv/",
        "scope": "Potential generic admin controls: settings, profile, login/logout, notifications, search, calendar, clock, check, edit, delete, lock, network, and status controls.",
        "caveat": "No dedicated developer, build, release, signing, owner-code, or dashboard icon family is present. Do not present these generic symbols as RAMI branding."
    },
    {
        "app": "Shared ROYAL Design",
        "fit": "shared",
        "source": "store/ and tv/ static icon folders",
        "scope": "Common actions such as home, back, close, add/remove, check, search, settings, profile, bell, star, heart, calendar, clock, filter, share, wifi, and loading.",
        "caveat": "Reference shared files instead of copying them into each application's asset folder."
    }
]

SOURCE_SETS = [
    {
        "archive": "restaurant_tv_3d_icons.zip",
        "contents": "158 SVGs plus source README and preview page: 37 store icons x 2 states and 42 TV icons x 2 states.",
        "classification": "Store/cafe functional icons and TV functional icons."
    },
    {
        "archive": "restaurant_tv_launcher_icons.zip",
        "contents": "4 SVGs: store and TV app icons plus 320x180 TV banners.",
        "classification": "Orange store + purple TV presentation variant."
    },
    {
        "archive": "restaurant_tv_launcher_icons (1).zip",
        "contents": "4 SVGs: store and TV app icons plus 320x180 TV banners.",
        "classification": "Gold store + blue TV presentation variant; not identical to the other brand pack."
    },
    {
        "archive": "restaurant_tv_launcher_ui_icons.zip",
        "contents": "48 SVGs: 16 launcher symbols x static, animated, and focused states.",
        "classification": "Canonical launcher UI set."
    },
    {
        "archive": "restaurant_tv_launcher_ui_icons (1).zip",
        "contents": "48 SVGs byte-identical to the canonical launcher UI set.",
        "classification": "Exact duplicate backup; retained for provenance."
    }
]

def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]

def main() -> None:
    if not EXTRACTED.exists():
        raise SystemExit(f"Missing extracted package directory: {EXTRACTED}")

    svg_files = sorted(EXTRACTED.rglob("*.svg"))
    records = []
    invalid = []
    missing_viewbox = []
    external_refs = []
    active_content = []
    animated = []
    state_counts = collections.Counter()
    digest_paths = collections.defaultdict(list)
    archive_counts = collections.Counter()
    colors = collections.Counter()

    for path in svg_files:
        data = path.read_bytes()
        rel = path.relative_to(ROOT).as_posix()
        digest = hashlib.sha256(data).hexdigest()
        digest_paths[digest].append(rel)
        archive = rel.split("/", 1)[1].split("/", 1)[0]
        archive_counts[archive] += 1

        try:
            root = ET.fromstring(data)
        except ET.ParseError as exc:
            invalid.append({"path": rel, "error": str(exc)})
            continue

        if local_name(root.tag) != "svg":
            invalid.append({"path": rel, "error": f"root element is {local_name(root.tag)}, expected svg"})

        viewbox = root.attrib.get("viewBox") or root.attrib.get("viewbox")
        if not viewbox:
            missing_viewbox.append(rel)

        elements = list(root.iter())
        tags = [local_name(node.tag).lower() for node in elements]
        smil_tags = [tag for tag in tags if tag in {"animate", "animatetransform", "animatemotion", "set"}]
        if smil_tags:
            animated.append({"path": rel, "smil_elements": len(smil_tags), "types": sorted(set(smil_tags))})

        if any(tag in {"script", "foreignobject"} for tag in tags):
            active_content.append(rel)

        refs = []
        for node in elements:
            for attr, value in node.attrib.items():
                if local_name(attr).lower() == "href" and re.match(r"^\s*https?://", value, re.I):
                    refs.append(value.strip())
        if refs:
            external_refs.append({"path": rel, "urls": sorted(set(refs))})

        for node in elements:
            for attr, value in node.attrib.items():
                if local_name(attr).lower() in {"fill", "stroke", "stop-color"}:
                    if re.fullmatch(r"#[0-9a-fA-F]{6}", value.strip()):
                        colors[value.upper()] += 1

        parts = path.parts
        state = next((part for part in ("static", "animated", "focused") if part in parts), "brand")
        state_counts[state] += 1

        records.append({
            "path": rel,
            "archive": archive,
            "sha256": digest,
            "bytes": len(data),
            "viewBox": viewbox,
            "width": root.attrib.get("width"),
            "height": root.attrib.get("height"),
            "state": state,
            "smil_animation": bool(smil_tags),
            "element_count": len(elements)
        })

    duplicate_groups = [
        {"sha256": digest, "count": len(paths), "files": paths}
        for digest, paths in digest_paths.items() if len(paths) > 1
    ]
    unique_contents = len(digest_paths)

    audit = {
        "package": "ROYAL Design - Shared Icon Package",
        "svg_count": len(svg_files),
        "unique_svg_contents": unique_contents,
        "duplicate_content_groups": len(duplicate_groups),
        "state_counts": dict(sorted(state_counts.items())),
        "archive_counts": dict(sorted(archive_counts.items())),
        "smil_animated_svg_count": len(animated),
        "invalid_svg": invalid,
        "missing_viewBox": missing_viewbox,
        "external_references": external_refs,
        "active_content": active_content,
        "common_hex_colors": colors.most_common(20),
        "files": records,
        "duplicate_groups": duplicate_groups
    }

    classification = {
        "package": "ROYAL Design - Shared Icon Package",
        "review_status": "classified-by-content-and-source; application integration not yet approved",
        "principles": [
            "Keep the original archives and extracted source trees unchanged.",
            "Use one shared source asset through references rather than duplicating files across apps.",
            "Do not replace established app logos, watermarks, or brand colors with generic pack icons.",
            "Animated SVG uses SMIL; Android apps should use a tested raster/vector/Lottie conversion rather than assuming native SVG animation support."
        ],
        "source_sets": SOURCE_SETS,
        "application_map": APP_MAP,
        "shared_control_candidates": [
            "home", "back", "close", "add", "remove", "check", "search",
            "settings", "profile", "bell", "star", "heart", "calendar",
            "clock", "filter", "share", "wifi", "loading"
        ],
        "royal_audio_media_control_candidates": [
            "play", "pause", "stop", "next", "prev", "forward",
            "rewind", "volume_up", "volume_down", "mute"
        ],
        "launcher_ui_states": {
            "static": "normal idle state",
            "animated": "SMIL motion/pulse state; browser preview only until converted and tested for Android",
            "focused": "focus/selection state for TV remote navigation"
        },
        "brand_variants": {
            "restaurant_tv_launcher_icons.zip": "orange store and purple TV palette",
            "restaurant_tv_launcher_icons (1).zip": "gold store and blue TV palette",
            "note": "These are alternate color treatments, not byte-identical duplicate archives."
        }
    }

    (ROOT / "technical-audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "classification.json").write_text(json.dumps(classification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# تصنيف حزمة ROYAL Design المشتركة",
        "",
        "## خريطة التطبيقات",
        "",
        "| التطبيق | المجموعة المناسبة | القرار الأولي |",
        "|---|---|---|",
        "| Almalaki | أيقونات المتجر والمقهى | مرشح أساسي؛ لا تستبدل الهوية الخضراء الحالية أو الشعار |",
        "| ROYAL TV | أيقونات التلفاز والقنوات | مرشح أساسي للرموز الوظيفية، لا للشعار |",
        "| RS TV / Sinjar TV | مجموعة التلفاز نفسها | استخدام مشترك دون نسخ الملفات |",
        "| ROYAL+ Launcher | أيقونات الواجهة 16 × 3 حالات | المطابقة الأقوى؛ الحالات الثابتة والمتحركة والمركّزة |",
        "| ROYAL AUDIO | عشرة رموز تحكم بالوسائط | استخدام محدود للتحكم فقط؛ لا توجد مجموعة هوية صوتية مستقلة |",
        "| RAMI Developer | رموز إدارية عامة | استخدام مشترك فقط؛ لا توجد رموز بناء/إصدارات/توقيع خاصة |",
        "",
        "## المجموعات ومحتوياتها",
        "",
        "- restaurant_tv_3d_icons.zip: 37 رمز متجر × حالتين و42 رمز تلفاز × حالتين؛ أي 158 SVG، إضافة إلى README والمعاينة.",
        "- restaurant_tv_launcher_icons.zip: أربعة ملفات SVG بألوان برتقالية/بنفسجية.",
        "- restaurant_tv_launcher_icons (1).zip: أربعة ملفات SVG بألوان ذهبية/زرقاء؛ هذه نسخة تصميم بديلة وليست نسخة مطابقة.",
        "- restaurant_tv_launcher_ui_icons.zip: 16 رمز واجهة بثلاث حالات، بإجمالي 48 SVG.",
        "- restaurant_tv_launcher_ui_icons (1).zip: 48 ملفاً مطابقاً بايتياً للحزمة السابقة؛ أبقيناها كنسخة مصدر احتياطية.",
        "",
        "## ملاحظات تقنية قبل ربطها بالتطبيقات",
        "",
        "- الأيقونات ذات تأثير 3D هي رسومات SVG بتدرجات وظلال ولمعان، وليست ملفات نماذج ثلاثية الأبعاد.",
        "- ملفات animated/ تستخدم SMIL (animate و/أو animateTransform). لا تفترض أن Android سيشغّلها مباشرة.",
        "- ملفات focused/ مناسبة كحالة تحديد لعناصر Android TV، لكن يجب اختبار التباين ومقاس التركيز مع الريموت.",
        "- مجموعة المتجر برتقالية/ذهبية بينما Almalaki لديه عناصر هوية زمردية؛ لا تُفرض هذه الألوان على التطبيق.",
        "- الشعارات واللافتات المرفقة عامة باسم المتجر أو التلفاز، وليست شعارات موثقة للتطبيقات الحالية.",
        "",
        "## نتائج الفحص الآلي",
        "",
        f"- SVG المفحوصة: {len(svg_files)}",
        f"- محتويات SVG الفريدة ببصمة SHA-256: {unique_contents}",
        f"- مجموعات التكرار المطابق: {len(duplicate_groups)}",
        f"- ملفات SVG غير الصالحة: {len(invalid)}",
        f"- ملفات دون viewBox: {len(missing_viewbox)}",
        f"- ملفات تحوي مراجع HTTP خارجية: {len(external_refs)}",
        f"- ملفات تحوي SMIL: {len(animated)}",
        "",
        "التقرير التفصيلي في technical-audit.json، وقواعد التصنيف في classification.json.",
        "هذا تصنيف للأصول فقط؛ لم يتم ربطها بكود أي تطبيق أو اعتمادها كتغيير إنتاجي.",
        ""
    ]
    (ROOT / "CLASSIFICATION_AR.md").write_text("\n".join(md), encoding="utf-8")

    print(f"SVG audited: {len(svg_files)}")
    print(f"Unique SVG contents: {unique_contents}")
    print(f"Duplicate-content groups: {len(duplicate_groups)}")
    print(f"SMIL animated SVG: {len(animated)}")
    print(f"Invalid SVG: {len(invalid)}")
    print(f"Missing viewBox: {len(missing_viewbox)}")
    print(f"External references: {len(external_refs)}")
    print(f"Active content: {len(active_content)}")

    if invalid or missing_viewbox or external_refs or active_content:
        raise SystemExit("SVG audit found blocking issues; see technical-audit.json")

if __name__ == "__main__":
    main()
