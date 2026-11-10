#!/usr/bin/env python3
"""Build the complete ROYAL Design V17 gallery from every approved source archive."""
from __future__ import annotations

import copy
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "icons" / "app-collections.json"
HTML = ROOT / "index.html"
PACKAGE = ROOT / "packages" / "royal-design-shared-icon-package" / "extracted"
COLLECTION = ROOT / "icons" / "v17" / "royal-library"
CATALOG = COLLECTION / "catalog.json"
ANDROID_COLLECTION = ROOT / "icons" / "v17" / "android-system"

ANDROID_ARCHIVE = ROOT / "sources" / "ROYAL_Android_Icons_v2.zip"
THREE_D_ARCHIVE = ROOT / "restaurant_tv_3d_icons.zip"
LAUNCHER_UI_ARCHIVE = ROOT / "restaurant_tv_launcher_ui_icons.zip"
LAUNCHER_UI_BACKUP = ROOT / "restaurant_tv_launcher_ui_icons (1).zip"
BRAND_ARCHIVE = ROOT / "restaurant_tv_launcher_icons.zip"
BRAND_ALT_ARCHIVE = ROOT / "restaurant_tv_launcher_icons (1).zip"

ANDROID_LABELS = {
    "account_circle": ("حساب المستخدم", "Account Circle"),
    "android_device": ("جهاز أندرويد", "Android Device"),
    "apps": ("التطبيقات", "Apps"),
    "arrow_back": ("رجوع", "Arrow Back"),
    "arrow_forward": ("للأمام", "Arrow Forward"),
    "battery_full": ("البطارية", "Battery Full"),
    "bluetooth": ("بلوتوث", "Bluetooth"),
    "cast": ("بث الشاشة", "Cast"),
    "download": ("تنزيل", "Download"),
    "folder": ("المجلدات", "Folder"),
    "help": ("مساعدة", "Help"),
    "info": ("معلومات", "Information"),
    "keyboard": ("لوحة المفاتيح", "Keyboard"),
    "menu": ("القائمة", "Menu"),
    "more_vert": ("المزيد", "More"),
    "notifications_active": ("الإشعارات", "Notifications Active"),
    "qr_code": ("رمز QR", "QR Code"),
    "refresh": ("تحديث", "Refresh"),
    "screen_share": ("مشاركة الشاشة", "Screen Share"),
    "tune": ("الضبط", "Tune"),
    "warning": ("تحذير", "Warning"),
    "wifi": ("واي فاي", "Wi-Fi"),
}

AR_LABELS = {
    "home": "الرئيسية", "offer": "العروض", "add": "إضافة", "settings": "الإعدادات",
    "coffee": "القهوة", "location": "الموقع", "check": "تأكيد", "calendar": "التقويم",
    "trash": "حذف", "edit": "تعديل", "clock": "الساعة", "chat": "المحادثة",
    "back": "رجوع", "menu": "القائمة", "wifi": "واي فاي", "cart": "السلة",
    "profile": "الملف الشخصي", "remove": "إزالة", "table": "الطاولة", "payment": "الدفع",
    "search": "بحث", "logout": "تسجيل الخروج", "food": "الطعام", "heart": "المفضلة",
    "close": "إغلاق", "dessert": "الحلويات", "phone": "الهاتف", "loading": "تحميل",
    "restaurant": "المطعم", "filter": "تصفية", "star": "تقييم", "delivery": "التوصيل",
    "orders": "الطلبات", "drink": "المشروبات", "bell": "التنبيهات", "share": "مشاركة",
    "login": "تسجيل الدخول", "cast": "البث", "channels": "القنوات", "forward": "تقديم",
    "fullscreen": "ملء الشاشة", "grid": "شبكة", "guide": "دليل البرامج", "info": "معلومات",
    "language": "اللغة", "live": "مباشر", "lock": "قفل", "mute": "كتم الصوت",
    "next": "التالي", "pause": "إيقاف مؤقت", "play": "تشغيل", "power": "الطاقة",
    "prev": "السابق", "record": "تسجيل", "refresh": "تحديث", "remote": "التحكم عن بُعد",
    "rewind": "ترجيع", "sleep": "السكون", "source": "المصدر", "stop": "إيقاف",
    "timer": "المؤقت", "volume_down": "خفض الصوت", "volume_up": "رفع الصوت",
    "apps": "التطبيقات", "favorites": "المفضلة", "kids": "الأطفال", "live_tv": "البث المباشر",
    "movies": "الأفلام", "music": "الموسيقى", "notifications": "الإشعارات",
    "recent": "الأخيرة", "series": "المسلسلات", "sports": "الرياضة", "input": "المدخلات",
}

SHAPE_TAGS = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
ANIMATION_TAGS = {"animate", "animatetransform", "animatemotion", "set"}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def read_archive(path: Path) -> dict[str, bytes]:
    if not path.is_file():
        raise SystemExit(f"Missing source archive: {path.relative_to(ROOT)}")
    with zipfile.ZipFile(path) as archive:
        return {
            name: archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/")
        }


def verify_archive_mirror(entries: dict[str, bytes], archive_prefix: str, extracted_folder: str) -> None:
    for name, data in entries.items():
        if not name.lower().endswith((".svg", ".xml")):
            continue
        if not name.startswith(archive_prefix):
            raise SystemExit(f"Unexpected archive path: {name}")
        mirror = PACKAGE / extracted_folder / name
        if not mirror.is_file():
            raise SystemExit(f"Missing extracted source matching {name}: {mirror.relative_to(ROOT)}")
        if mirror.read_bytes() != data:
            raise SystemExit(f"Extracted source differs from archive entry: {name}")


def validate_svg(data: bytes, label: str, require_animation: bool = False) -> None:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise SystemExit(f"Invalid SVG {label}: {exc}")
    if local_name(root.tag).lower() != "svg":
        raise SystemExit(f"SVG has unexpected root in {label}: {root.tag}")
    tags = {local_name(node.tag).lower() for node in root.iter()}
    if not tags.intersection(SHAPE_TAGS):
        raise SystemExit(f"SVG contains no vector geometry: {label}")
    if require_animation and not tags.intersection(ANIMATION_TAGS):
        raise SystemExit(f"Animated SVG has no SMIL animation: {label}")


def make_motion_svg(source: bytes, label: str) -> bytes:
    text = source.decode("utf-8-sig")
    root_open = re.search(r"<svg\b[^>]*>", text, re.IGNORECASE)
    root_close = re.search(r"</svg>\s*$", text, re.IGNORECASE)
    if not root_open or not root_close or root_open.end() >= root_close.start():
        raise SystemExit(f"Cannot safely add motion wrapper to {label}")
    body = text[root_open.end():root_close.start()]
    if re.search(r"<(?:animate|animateTransform|animateMotion|set)\b", body, re.IGNORECASE):
        raise SystemExit(f"Refusing to wrap an already animated source: {label}")
    wrapper = (
        "\n<g>\n"
        '<animateTransform attributeName="transform" type="translate" values="0 0;0 -1.5;0 0" dur="2.8s" repeatCount="indefinite"/>\n'
        '<animate attributeName="opacity" values="0.96;1;0.96" dur="2.8s" repeatCount="indefinite"/>\n'
        + body +
        "\n</g>\n"
    )
    animated = (text[:root_open.end()] + wrapper + text[root_close.start():]).encode("utf-8")
    validate_svg(animated, label + " generated motion", require_animation=True)
    return animated


def write_generated_motion(source_path: Path, key: str, group: str) -> str:
    if not source_path.is_file():
        raise SystemExit(f"Missing static SVG for generated motion: {source_path.relative_to(ROOT)}")
    out_rel = f"icons/v17/royal-library/motion/{group}/{key}.svg"
    out_path = ROOT / out_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(make_motion_svg(source_path.read_bytes(), key))
    return out_rel


def copy_original_android_assets(android_entries: dict[str, bytes]) -> list[dict]:
    prefix = "ROYAL_Android_Icons_v2/"
    svg_entries = {
        name: data for name, data in android_entries.items()
        if name.startswith(prefix) and name.lower().endswith(".svg")
    }
    xml_entries = {
        name: data for name, data in android_entries.items()
        if name.startswith(prefix) and name.lower().endswith(".xml")
    }
    if len(svg_entries) != 22 or len(xml_entries) != 22:
        raise SystemExit(
            f"Android archive must contain 22 SVG + 22 XML files; "
            f"found {len(svg_entries)} SVG and {len(xml_entries)} XML."
        )

    def key_for(path: str) -> str:
        stem = Path(path).stem.lower()
        return stem.removeprefix("royal_")

    svg_by_key = {key_for(name): (name, data) for name, data in svg_entries.items()}
    xml_by_key = {key_for(name): (name, data) for name, data in xml_entries.items()}
    if len(svg_by_key) != 22 or len(xml_by_key) != 22 or set(svg_by_key) != set(xml_by_key):
        raise SystemExit("Android SVG/XML filenames do not form 22 unique matching pairs.")

    icons = []
    for key in sorted(svg_by_key):
        svg_name, svg_data = svg_by_key[key]
        xml_name, xml_data = xml_by_key[key]
        validate_svg(svg_data, svg_name)
        try:
            xml_root = ET.fromstring(xml_data)
        except ET.ParseError as exc:
            raise SystemExit(f"Invalid Android VectorDrawable {xml_name}: {exc}")
        if not local_name(xml_root.tag).lower().endswith("vector"):
            raise SystemExit(f"Android source is not a VectorDrawable: {xml_name}")
        if not any(local_name(node.tag) == "path" for node in xml_root.iter()):
            raise SystemExit(f"Android VectorDrawable has no path geometry: {xml_name}")

        svg_rel = f"icons/v17/android-system/svg/{key}.svg"
        xml_rel = f"icons/v17/android-system/drawable/{key}.xml"
        (ROOT / svg_rel).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / xml_rel).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / svg_rel).write_bytes(svg_data)
        (ROOT / xml_rel).write_bytes(xml_data)

        label_ar, label_en = ANDROID_LABELS.get(
            key, (key.replace("_", " ").title(), key.replace("_", " ").title())
        )
        motion_rel = write_generated_motion(ROOT / svg_rel, key, "android-system")
        icons.append({
            "key": key,
            "label_ar": label_ar,
            "label_en": label_en,
            "category": "android-system",
            "source_archive": "sources/ROYAL_Android_Icons_v2.zip",
            "variants": {"2d": svg_rel, "android_xml": xml_rel},
            "motion": motion_rel,
            "motion_source": "generated_royal_preview",
            "motion_note": "Subtle SMIL motion wrapper generated from the approved static Android SVG; the original SVG and Android XML remain unchanged.",
            "rights": {
                "origin": "uploaded_royal_package",
                "license": "ROYAL_SOURCE_PACKAGE",
                "authoring_note": "Original SVG and Android VectorDrawable assets preserved from the approved ROYAL_Android_Icons_v2.zip archive."
            },
            "status": "android_vector_motion_preview"
        })
    return icons


def update_gallery_html(manifest: dict, collection: dict) -> None:
    html = HTML.read_text(encoding="utf-8")
    embedded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
    html, count = re.subn(
        r"const embeddedManifest=(\{.*\});\s*const rootPrefix=",
        lambda match: "const embeddedManifest=" + embedded + ";\nconst rootPrefix=",
        html,
        count=1,
        flags=re.S
    )
    if count != 1:
        raise SystemExit("Could not refresh the embedded manifest in index.html.")

    html, count = re.subn(
        r"<p>معرض ROYAL Design.*?</p>",
        "<p>معرض ROYAL Design من V2 إلى V17. تضم V17 مكتبة كاملة من 125 بطاقة، وتظهر معاينة الحركة داخل البطاقة مباشرة.</p>",
        html,
        count=1,
        flags=re.S
    )
    if count != 1:
        raise SystemExit("Could not update the gallery introduction.")

    html, count = re.subn(
        r'<select id="styleFilter".*?</select>',
        '<select id="styleFilter" aria-label="تصفية النمط">'
        '<option value="all">عرض جميع النسخ المتاحة</option>'
        '<option value="2d">الأصل الثابت · 2D</option>'
        '<option value="3d">3D · للإصدارات السابقة</option>'
        '<option value="motion">الحركة فقط</option>'
        '<option value="focused">حالة التركيز</option>'
        '<option value="android_xml">Android XML فقط</option>'
        '</select>',
        html,
        count=1,
        flags=re.S
    )
    if count != 1:
        raise SystemExit("Could not update gallery style filters.")

    old_variant = re.compile(r"function makeVariant\(icon,style\)\{.*?\}\nfunction render\(\)\{", re.S)
    new_variant = """function makeVariant(icon,style){const path=icon.variants[style];const box=el('div','variant');const link=el('a');link.href=assetUrl(path);link.target='_blank';link.rel='noopener';const img=el('img');img.src=assetUrl(path);img.alt=icon.label_ar+' — '+style.toUpperCase();img.loading='lazy';img.onerror=()=>{img.alt='تعذرت معاينة الأصل';img.style.opacity='.25'};link.append(img);const label=style==='focused'?'حالة التركيز · Focused':(appVersionIsV16(icon)?(style==='2d'?'ثابت · Static':'متحرك · Animated'):(style==='2d'?'2D · ثابت':style.toUpperCase()));link.append(el('div','variant-name',label));box.append(link);return box}
function makeMotionVariant(icon){const path=icon.motion;const box=el('div','variant');const link=el('a');link.href=assetUrl(path);link.target='_blank';link.rel='noopener';const img=el('img');img.src=assetUrl(path);img.alt=icon.label_ar+' — motion';img.loading='lazy';img.onerror=()=>{img.alt='تعذرت معاينة الحركة';img.style.opacity='.25'};link.append(img);link.append(el('div','variant-name',icon.motion_source==='generated_royal_preview'?'حركة ROYAL خفيفة':'حركة أصلية · SMIL'));box.append(link);return box}
function render(){"""
    html, count = old_variant.subn(lambda match: new_variant, html, count=1)
    if count != 1:
        raise SystemExit("Could not install inline SVG motion preview renderer.")

    render_pattern = re.compile(r"function render\(\)\{.*?\}\nfunction init\(\)\{", re.S)
    render_replacement = """function render(){
const app=collections[active];if(!app)return;
const isV17=app.version==='V17';
for(const option of styleFilter.options){if(option.value==='3d')option.hidden=isV17;if(['motion','focused','android_xml'].includes(option.value))option.hidden=!isV17}
if(isV17&&styleFilter.value==='3d')styleFilter.value='all';
if(!isV17&&['motion','focused','android_xml'].includes(styleFilter.value))styleFilter.value='all';
title.textContent=app.version+' · '+app.name_ar;
description.textContent=app.application+' — '+app.description_ar+' · ضمن: '+(app.used_by||[]).join('، ');
status.textContent=isV17?'ROYAL DESIGN · '+app.icons.length+' بطاقة · 117 أيقونة وظيفية':'ROYAL ORIGINAL · '+app.icons.length+' مفاهيم';
palette.innerHTML='';const paletteLabels={primary:'أساسي',secondary:'مساند',highlight:'إضاءة',surface:'خلفية'};
Object.entries(app.palette||{}).forEach(([role,color])=>{const item=el('span','swatch');const dot=el('span','swatch-dot');dot.style.background=color;const label=el('span','',paletteLabels[role]||role);item.append(dot,label);item.title=color;palette.append(item)});
grid.innerHTML='';let count=0;const q=search.value.trim().toLocaleLowerCase();
for(const icon of app.icons){
const searchable=(icon.key+' '+icon.label_ar+' '+icon.label_en).toLocaleLowerCase();if(q&&!searchable.includes(q))continue;
count++;const card=el('article','card');const heading=el('div','card-title');heading.append(el('div','label',icon.label_ar+' · '+icon.label_en));heading.append(el('div','key',icon.key+(icon.shared_from?' · '+icon.shared_from+' مشترك':'')));card.append(heading);
const pair=el('div',isV17?'pair v17':'pair');
if(isV17){
pair.style.gridTemplateColumns='repeat(auto-fit,minmax(105px,1fr))';
const filter=styleFilter.value;
if(filter==='all'||filter==='2d')pair.append(makeVariant(icon,'2d'));
if(icon.motion&&(filter==='all'||filter==='motion'))pair.append(makeMotionVariant(icon));
if(icon.variants.focused&&(filter==='all'||filter==='focused'))pair.append(makeVariant(icon,'focused'));
if(icon.variants.android_xml&&(filter==='all'||filter==='android_xml'))pair.append(makeAndroidXml(icon));
}else{
if(styleFilter.value!=='3d'&&styleFilter.value!=='android_xml')pair.append(makeVariant(icon,'2d'));
if(styleFilter.value!=='2d'&&styleFilter.value!=='android_xml')pair.append(makeVariant(icon,'3d'));
}
card.append(pair);const actions=el('div','actions');const copy=el('button','','نسخ المفتاح');copy.type='button';copy.addEventListener('click',()=>copyText(icon.key,copy));actions.append(copy);
if(icon.motion){const motion=el('a','',isV17?'فتح ملف الحركة':'معاينة الحركة');motion.href=assetUrl(icon.motion);motion.target='_blank';motion.rel='noopener';actions.append(motion)}
const details=el('a','','ملف الفهرس');details.href=assetUrl(app.collection_path+'/catalog.json');details.target='_blank';details.rel='noopener';actions.append(details);card.append(actions);grid.append(card)
}
empty.hidden=count!==0
}
function init(){"""
    html, count = render_pattern.subn(lambda match: render_replacement, html, count=1)
    if count != 1:
        raise SystemExit("Could not update gallery renderer.")

    stats_pattern = re.compile(
        r"\[collections\.length\+' إصداراً'.*?' Android XML'\]"
    )
    stats_replacement = (
        "[collections.length+' إصداراً',total+' بطاقة',"
        "new Set(collections.flatMap(a=>a.icons.map(i=>i.variants['2d']))).size+' أصل 2D',"
        "new Set(collections.flatMap(a=>a.icons.filter(i=>i.variants['3d']).map(i=>i.variants['3d']))).size+' نسخة 3D',"
        "new Set(collections.flatMap(a=>a.icons.filter(i=>i.motion).map(i=>i.motion))).size+' ملف حركة',"
        "new Set(collections.flatMap(a=>a.icons.filter(i=>i.variants.android_xml).map(i=>i.variants.android_xml))).size+' Android XML']"
    )
    html, count = stats_pattern.subn(lambda match: stats_replacement, html, count=1)
    if count != 1:
        raise SystemExit("Could not update gallery totals.")
    HTML.write_text(html, encoding="utf-8")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    versions = manifest.get("versions", [])
    v16 = next((item for item in versions if item.get("version") == "V16"), None)
    old_v17 = next((item for item in versions if item.get("version") == "V17"), None)
    if not v16 or len(v16.get("icons", [])) != 99:
        raise SystemExit("Expected the preserved V16 source collection with 99 entries.")
    if not old_v17 or len(old_v17.get("icons", [])) != 22:
        raise SystemExit("Expected the original V17 Android collection with 22 entries.")

    android_entries = read_archive(ANDROID_ARCHIVE)
    three_d_entries = read_archive(THREE_D_ARCHIVE)
    ui_entries = read_archive(LAUNCHER_UI_ARCHIVE)
    ui_backup_entries = read_archive(LAUNCHER_UI_BACKUP)
    brand_entries = read_archive(BRAND_ARCHIVE)
    brand_alt_entries = read_archive(BRAND_ALT_ARCHIVE)

    verify_archive_mirror(three_d_entries, "icon_pack/", "restaurant_tv_3d_icons")
    verify_archive_mirror(ui_entries, "launcher_ui_pack/", "restaurant_tv_launcher_ui_icons")
    verify_archive_mirror(brand_entries, "launcher_pack/", "restaurant_tv_launcher_icons")
    verify_archive_mirror(brand_alt_entries, "launcher_pack/", "restaurant_tv_launcher_icons_1")

    ui_svg = {name: data for name, data in ui_entries.items() if name.lower().endswith(".svg")}
    ui_backup_svg = {name: data for name, data in ui_backup_entries.items() if name.lower().endswith(".svg")}
    if ui_svg != ui_backup_svg:
        raise SystemExit("The launcher UI backup ZIP differs from the canonical source; review before import.")

    three_d_svg = {name: data for name, data in three_d_entries.items() if name.lower().endswith(".svg")}
    expected_three_d = {
        "store/static": 37, "store/animated": 37,
        "tv/static": 42, "tv/animated": 42
    }
    actual_three_d = {
        group: sum(name.startswith("icon_pack/" + group + "/") for name in three_d_svg)
        for group in expected_three_d
    }
    if len(three_d_svg) != 158 or actual_three_d != expected_three_d:
        raise SystemExit(f"TV/store archive inventory changed: {actual_three_d}")

    ui_states = {
        state: [name for name in ui_svg if name.startswith(f"launcher_ui_pack/{state}/")]
        for state in ("static", "animated", "focused")
    }
    if len(ui_svg) != 48 or any(len(files) != 16 for files in ui_states.values()):
        raise SystemExit("Launcher UI archive must contain 16 icons in each of static/animated/focused states.")

    if len([name for name in brand_entries if name.lower().endswith(".svg")]) != 4:
        raise SystemExit("Canonical launcher brand archive must contain four SVG assets.")
    if len([name for name in brand_alt_entries if name.lower().endswith(".svg")]) != 4:
        raise SystemExit("Alternate launcher brand archive must contain four SVG assets.")

    # V16 already contains 79 store/TV icons, 16 launcher UI icons and four canonical brand assets.
    # Reuse the exact source files; only expose the states accurately in the richer V17 catalog.
    icons = []
    source_icons = v16.get("icons", [])
    source_by_key = {item.get("key"): item for item in source_icons}
    if len(source_by_key) != 99:
        raise SystemExit("V16 contains duplicate keys; refusing to create a partial V17 catalog.")

    category_counts = Counter()
    for original in source_icons:
        icon = copy.deepcopy(original)
        key = icon["key"]
        variants = icon.get("variants", {})
        static_path = variants.get("2d")
        animated_path = variants.get("3d")

        if key.startswith("icon-pack-store-"):
            category = "store"
            archive = "restaurant_tv_3d_icons.zip"
        elif key.startswith("icon-pack-tv-"):
            category = "tv"
            archive = "restaurant_tv_3d_icons.zip"
        elif key.startswith("launcher-ui-pack-"):
            category = "launcher-ui"
            archive = "restaurant_tv_launcher_ui_icons.zip"
        elif key.startswith("launcher-"):
            category = "brand-assets"
            archive = "restaurant_tv_launcher_icons.zip"
        else:
            raise SystemExit(f"Unclassified V16 source entry: {key}")

        if not static_path or not (ROOT / static_path).is_file():
            raise SystemExit(f"Missing static V16 source for {key}: {static_path}")

        icon["category"] = category
        icon["source_archive"] = archive
        icon["variants"] = {"2d": static_path}

        if category in {"store", "tv"}:
            if not animated_path or not (ROOT / animated_path).is_file():
                raise SystemExit(f"Missing original animated SVG for {key}: {animated_path}")
            validate_svg((ROOT / animated_path).read_bytes(), key + " native motion", require_animation=True)
            icon["motion"] = animated_path
            icon["motion_source"] = "source_archive_smil"
            icon.pop("focus_state_source", None)
        elif category == "launcher-ui":
            focused_path = original.get("motion")
            if not animated_path or not (ROOT / animated_path).is_file():
                raise SystemExit(f"Missing original launcher animation for {key}: {animated_path}")
            if not focused_path or not (ROOT / focused_path).is_file():
                raise SystemExit(f"Missing focused launcher state for {key}: {focused_path}")
            validate_svg((ROOT / animated_path).read_bytes(), key + " native motion", require_animation=True)
            validate_svg((ROOT / focused_path).read_bytes(), key + " focused state")
            icon["variants"]["focused"] = focused_path
            icon["motion"] = animated_path
            icon["motion_source"] = "source_archive_smil"
        else:
            motion_rel = write_generated_motion(ROOT / static_path, key, "brand-assets")
            icon["motion"] = motion_rel
            icon["motion_source"] = "generated_royal_preview"
            icon["motion_note"] = "Subtle SMIL motion wrapper generated from the approved static brand SVG; the original brand artwork remains unchanged."

        icon["status"] = "complete_motion_preview"
        category_counts[category] += 1
        icons.append(icon)

    # Include the alternate gold/blue brand and banner treatment as separate source assets.
    alt_root = "packages/royal-design-shared-icon-package/extracted/restaurant_tv_launcher_icons_1/launcher_pack"
    alt_labels = {
        "store/app_icon.svg": ("شعار المتجر · ذهبي وأزرق", "Store App Icon · Gold/Blue"),
        "store/tv_banner_320x180.svg": ("لافتة المتجر للتلفاز · ذهبي وأزرق", "Store TV Banner · Gold/Blue"),
        "tv/app_icon.svg": ("شعار التلفاز · ذهبي وأزرق", "TV App Icon · Gold/Blue"),
        "tv/tv_banner_320x180.svg": ("لافتة التلفاز · ذهبي وأزرق", "TV Banner · Gold/Blue"),
    }
    for rel, (label_ar, label_en) in alt_labels.items():
        source_rel = f"{alt_root}/{rel}"
        source_path = ROOT / source_rel
        if not source_path.is_file():
            raise SystemExit(f"Missing alternate launcher brand asset: {source_rel}")
        validate_svg(source_path.read_bytes(), source_rel)
        key = (
            "launcher-alt-store-" if rel.startswith("store/") else "launcher-alt-tv-"
        ) + ("app-icon" if rel.endswith("app_icon.svg") else "tv-banner")
        motion_rel = write_generated_motion(source_path, key, "brand-assets")
        icons.append({
            "key": key,
            "label_ar": label_ar,
            "label_en": label_en,
            "category": "brand-assets",
            "source_archive": "restaurant_tv_launcher_icons (1).zip",
            "variants": {"2d": source_rel},
            "motion": motion_rel,
            "motion_source": "generated_royal_preview",
            "motion_note": "Subtle SMIL motion wrapper generated from the approved alternate gold/blue brand SVG; original artwork remains unchanged.",
            "rights": {
                "origin": "uploaded_royal_package",
                "license": "ROYAL_SOURCE_PACKAGE",
                "authoring_note": "Alternate gold/blue ROYAL launcher brand asset preserved from the approved alternate launcher icon ZIP archive."
            },
            "status": "complete_motion_preview"
        })
        category_counts["brand-assets"] += 1

    icons.extend(copy_original_android_assets(android_entries))
    category_counts["android-system"] = 22

    expected_counts = {
        "store": 37, "tv": 42, "launcher-ui": 16,
        "brand-assets": 8, "android-system": 22
    }
    if dict(category_counts) != expected_counts:
        raise SystemExit(f"V17 category totals differ from reviewed ZIP inventories: {dict(category_counts)}")
    if len(icons) != 125 or len({icon["key"] for icon in icons}) != 125:
        raise SystemExit("V17 must contain 125 unique gallery entries.")
    if sum(category_counts.values()) - category_counts["brand-assets"] != 117:
        raise SystemExit("V17 must contain 117 functional icon concepts plus eight brand assets.")
    if any(not icon.get("motion") for icon in icons):
        raise SystemExit("Every V17 entry must have a motion preview.")

    native_motion_count = sum(icon.get("motion_source") == "source_archive_smil" for icon in icons)
    generated_motion_count = sum(icon.get("motion_source") == "generated_royal_preview" for icon in icons)
    focused_count = sum(bool(icon.get("variants", {}).get("focused")) for icon in icons)
    android_xml_count = sum(bool(icon.get("variants", {}).get("android_xml")) for icon in icons)
    if (native_motion_count, generated_motion_count, focused_count, android_xml_count) != (95, 30, 16, 22):
        raise SystemExit("V17 motion/focus/XML counts differ from the verified archive inventory.")

    collection = {
        "version": "V17",
        "slug": "complete-royal-library",
        "application": "ROYAL Design · جميع تطبيقات ROYAL",
        "name_ar": "المكتبة الملكية الكاملة",
        "description_ar": "125 بطاقة تشمل 117 أيقونة وظيفية و8 أصول هوية ولافتات؛ مع الحركة وحالات التركيز وملفات Android الأصلية حيث تتوفر",
        "dimension_styles": ["2d", "motion", "focused", "android_xml"],
        "collection_path": "icons/v17/royal-library",
        "status": "complete_source_archive_library",
        "accent_policy": "Original static SVGs and native SMIL assets are preserved; generated motion wrappers never alter source artwork.",
        "palette": {
            "primary": "#D7B96D",
            "secondary": "#168B79",
            "highlight": "#FFF0B8",
            "surface": "#35434A"
        },
        "used_by": ["Almalaki", "ROYAL TV", "ROYAL+ Launcher", "RS TV", "RAMI Developer", "ROYAL AUDIO"],
        "source_archives": [
            "sources/ROYAL_Android_Icons_v2.zip",
            "restaurant_tv_3d_icons.zip",
            "restaurant_tv_launcher_ui_icons.zip",
            "restaurant_tv_launcher_icons.zip",
            "restaurant_tv_launcher_icons (1).zip"
        ],
        "source_archive_notes": {
            "restaurant_tv_3d_icons.zip": "79 concepts: 37 store and 42 TV icons, each with static and native SMIL animated SVG.",
            "restaurant_tv_launcher_ui_icons.zip": "16 launcher concepts with static, animated and focused states.",
            "restaurant_tv_launcher_ui_icons (1).zip": "Byte-identical backup of the canonical launcher UI archive; verified and not duplicated.",
            "restaurant_tv_launcher_icons.zip": "Four original orange/purple store and TV brand assets.",
            "restaurant_tv_launcher_icons (1).zip": "Four alternate gold/blue store and TV brand assets.",
            "ROYAL_Android_Icons_v2.zip": "22 matching original SVG and Android VectorDrawable XML pairs; subtle motion previews are generated without changing the original files."
        },
        "asset_totals": {
            "gallery_entries": 125,
            "functional_icon_concepts": 117,
            "brand_assets": 8,
            "native_smil_motion_previews": 95,
            "generated_motion_previews": 30,
            "motion_previews_total": 125,
            "focused_states": 16,
            "android_vector_drawables": 22,
            "source_archive_svg_files": 236,
            "unique_source_svg_contents": 212,
            "duplicate_ui_backup_archives": 1
        },
        "icons": icons
    }

    android_icons = [icon for icon in icons if icon.get("category") == "android-system"]
    (ANDROID_COLLECTION / "catalog.json").write_text(
        json.dumps({
            "version": "V17",
            "slug": "android-system",
            "name_ar": "أيقونات Android",
            "description_ar": "المجموعة الفرعية الأصلية المكونة من 22 أيقونة مع VectorDrawable وحركة ROYAL خفيفة",
            "source_archive": "sources/ROYAL_Android_Icons_v2.zip",
            "icons": android_icons
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    COLLECTION.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    versions = [item for item in versions if item.get("version") != "V17"]
    versions.append(collection)
    manifest["title"] = "ROYAL Design · V2–V17 Complete Icon Collections"
    manifest["versions"] = versions

    unique_2d = {
        icon["variants"]["2d"]
        for version in versions for icon in version.get("icons", [])
        if icon.get("variants", {}).get("2d")
    }
    unique_3d = {
        icon["variants"]["3d"]
        for version in versions for icon in version.get("icons", [])
        if icon.get("variants", {}).get("3d")
    }
    unique_motion = {
        icon["motion"]
        for version in versions for icon in version.get("icons", [])
        if icon.get("motion")
    }
    unique_focused = {
        icon["variants"]["focused"]
        for version in versions for icon in version.get("icons", [])
        if icon.get("variants", {}).get("focused")
    }
    unique_android_xml = {
        icon["variants"]["android_xml"]
        for version in versions for icon in version.get("icons", [])
        if icon.get("variants", {}).get("android_xml")
    }
    manifest.setdefault("totals", {}).update({
        "app_collections": len(versions),
        "concepts": len(unique_2d),
        "flat_svg": len(unique_2d),
        "dimensional_svg": len(unique_3d),
        "motion_svg": len(unique_motion),
        "focused_svg": len(unique_focused),
        "android_xml": len(unique_android_xml),
        "v17_entries": len(icons),
        "v17_icon_concepts": 117
    })
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    update_gallery_html(manifest, collection)

    readme = ROOT / "README.md"
    readme_text = readme.read_text(encoding="utf-8")
    readme_text = readme_text.replace(
        "- **V17:** أيقونات أندرويد — معاينات SVG وملفات Android VectorDrawable الأصلية.",
        "- **V17:** المكتبة الملكية الكاملة — 125 بطاقة تشمل 117 أيقونة وظيفية و8 أصول هوية ولافتات، مع معاينات الحركة داخل البطاقات."
    )
    readme_text = readme_text.replace(
        "- V17 تعرض معاينة **SVG** مع ملف **Android VectorDrawable XML** الأصلي للتنزيل؛ ولا تصنّف XML على أنه 3D.",
        "- V17 تعرض الأصل الثابت والحركة داخل البطاقة، وحالات التركيز للواجهة، وملفات Android VectorDrawable XML للأيقونات الـ22؛ ولا تصنّف XML على أنه 3D."
    )
    readme_text = readme_text.replace(
        "- معاينات حركة V9 اختيارية؛ النسخة الثابتة هي الافتراضية.",
        "- معاينة الحركة في V17 ظاهرة مباشرة بجانب الأصل الثابت. ملفات SMIL الأصلية محفوظة، والحركات الإضافية للأيقونات النظامية والهوية هي طبقة حركة خفيفة لا تغيّر الأصل."
    )
    readme_text = readme_text.replace(
        "- 16 إصداراً من V2 إلى V17.\n- 348 مفهوماً فريداً.\n- 348 ملف SVG للمعاينة، و326 ملف 3D، و22 ملف Android XML.",
        "- 16 إصداراً من V2 إلى V17.\n- 125 بطاقة في V17: 117 مفهوماً وظيفياً و8 أصول هوية ولافتات.\n- 95 حركة أصلية من الأرشيفات، و30 معاينة حركة ROYAL مشتقة، و16 حالة تركيز، و22 ملف Android VectorDrawable.\n- أعداد المسارات الفريدة في الفهرس محسوبة آلياً مع إعادة استخدام الملفات المشتركة دون نسخها."
    )
    readme.write_text(readme_text, encoding="utf-8")

    source_note = ROOT / "sources" / "V17_IMPORT_SOURCE.md"
    source_note.write_text(
        "# ROYAL Design V17 source\n\n"
        "V17 is assembled from the complete reviewed source set in this repository:\n\n"
        "- sources/ROYAL_Android_Icons_v2.zip: 22 matching SVG and Android VectorDrawable XML pairs.\n"
        "- restaurant_tv_3d_icons.zip: 37 store + 42 TV icon concepts, each with static and native SMIL animated SVG states (158 SVG files).\n"
        "- restaurant_tv_launcher_ui_icons.zip: 16 launcher UI concepts with static, animated and focused states (48 SVG files).\n"
        "- restaurant_tv_launcher_icons.zip: four original orange/purple brand and banner assets.\n"
        "- restaurant_tv_launcher_icons (1).zip: four alternate gold/blue brand and banner assets.\n"
        "- restaurant_tv_launcher_ui_icons (1).zip: byte-identical backup of the canonical UI archive; verified and not duplicated.\n\n"
        "V17 contains 125 gallery entries: 117 functional icon concepts plus eight brand/banner assets. Every entry has an inline motion preview. The 95 source animations remain unchanged; subtle ROYAL SMIL wrappers are generated for 22 Android system icons and eight static brand assets. The launcher UI retains all 16 focused states. Original source SVG/XML files are never overwritten by generated motion copies.\n",
        encoding="utf-8"
    )

    print("V17 archive inventory verified:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}")
    print("  functional icon concepts: 117")
    print("  brand/banner assets: 8")
    print("  total entries with motion previews: 125")
    print(f"  native source SMIL animations: {native_motion_count}")
    print(f"  generated ROYAL motion previews: {generated_motion_count}")
    print(f"  focused states: {focused_count}")
    print(f"  Android VectorDrawable XML files: {android_xml_count}")
    print("  duplicate launcher UI backup: verified byte-identical; not duplicated")
    print("  original V2-V16 collections preserved")


if __name__ == "__main__":
    main()
