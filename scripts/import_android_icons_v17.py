#!/usr/bin/env python3
"""Import the approved ROYAL Android icon archive as gallery V17."""
import json
import re
import subprocess
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "sources" / "ROYAL_Android_Icons_v2.zip"
MANIFEST = ROOT / "icons" / "app-collections.json"
HTML = ROOT / "index.html"
COLLECTION = ROOT / "icons" / "v17" / "android-system"
CATALOG = COLLECTION / "catalog.json"
LABELS = {
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

def key_for(path):
    stem = Path(path).stem.lower()
    if stem.startswith("royal_"):
        stem = stem[len("royal_"):]
    return re.sub(r"[^a-z0-9]+", "_", stem).strip("_")

def main():
    if not ARCHIVE.is_file():
        raise SystemExit(f"Missing source archive: {ARCHIVE}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if any(v.get("version") == "V17" for v in manifest.get("versions", [])):
        print("V17 already imported; validating the existing generated collection.")
        return
    with zipfile.ZipFile(ARCHIVE) as archive:
        entries = [n for n in archive.namelist() if not n.endswith("/")]
        svg_entries = [n for n in entries if n.lower().endswith(".svg")]
        xml_entries = [n for n in entries if n.lower().endswith(".xml")]
        if len(svg_entries) != 22 or len(xml_entries) != 22:
            raise SystemExit(f"Expected 22 SVG and 22 Android XML files; found {len(svg_entries)} SVG and {len(xml_entries)} XML.")
        svg_by_key = {key_for(n): n for n in svg_entries}
        xml_by_key = {key_for(n): n for n in xml_entries}
        if set(svg_by_key) != set(xml_by_key) or len(svg_by_key) != 22 or len(xml_by_key) != 22:
            print("SVG entries:", svg_entries)
            print("XML entries:", xml_entries)
            print("SVG keys:", sorted(svg_by_key))
            print("XML keys:", sorted(xml_by_key))
            raise SystemExit("SVG/XML filenames do not form 22 unique matching icon pairs.")
        icons = []
        for key in sorted(svg_by_key):
            svg_name, xml_name = svg_by_key[key], xml_by_key[key]
            svg_data, xml_data = archive.read(svg_name), archive.read(xml_name)
            try:
                svg_root = ET.fromstring(svg_data)
                xml_root = ET.fromstring(xml_data)
            except ET.ParseError as exc:
                raise SystemExit(f"Invalid source vector for {key}: {exc}")
            if not svg_root.tag.lower().endswith("svg"):
                raise SystemExit(f"SVG source has unexpected root for {key}: {svg_root.tag}")
            if not xml_root.tag.lower().endswith("vector"):
                raise SystemExit(f"Android source is not a VectorDrawable for {key}: {xml_root.tag}")
            if not any(el.tag.rsplit("}", 1)[-1] == "path" for el in svg_root.iter()):
                raise SystemExit(f"SVG has no path geometry: {key}")
            if not any(el.tag.rsplit("}", 1)[-1] == "path" and any(name.endswith("pathData") for name in el.attrib) for el in xml_root.iter()):
                raise SystemExit(f"Android VectorDrawable has no pathData: {key}")
            svg_rel = f"icons/v17/android-system/svg/{key}.svg"
            xml_rel = f"icons/v17/android-system/drawable/{key}.xml"
            svg_out, xml_out = ROOT / svg_rel, ROOT / xml_rel
            svg_out.parent.mkdir(parents=True, exist_ok=True)
            xml_out.parent.mkdir(parents=True, exist_ok=True)
            svg_out.write_bytes(svg_data)
            xml_out.write_bytes(xml_data)
            label_ar, label_en = LABELS.get(key, (key.replace("_", " ").title(), key.replace("_", " ").title()))
            icons.append({
                "key": key,
                "label_ar": label_ar,
                "label_en": label_en,
                "variants": {"2d": svg_rel, "android_xml": xml_rel},
                "rights": {
                    "origin": "uploaded_royal_package",
                    "license": "ROYAL_SOURCE_PACKAGE",
                    "authoring_note": "Original SVG and Android VectorDrawable assets preserved from the user's approved ROYAL_Android_Icons_v2.zip archive."
                },
                "status": "android_vector_preview"
            })
    collection = {
        "version": "V17",
        "slug": "android-system",
        "application": "Android · تطبيقات ROYAL",
        "name_ar": "أيقونات أندرويد",
        "description_ar": "حزمة النظام الجديدة؛ معاينة SVG وملفات Android VectorDrawable الأصلية",
        "dimension_styles": ["2d", "android_xml"],
        "collection_path": "icons/v17/android-system",
        "status": "source_package_preview",
        "accent_policy": "Original source artwork preserved without relabeling Android XML as 3D",
        "palette": {"primary": "#D7B96D", "secondary": "#168B79", "highlight": "#FFF0B8", "surface": "#35434A"},
        "used_by": ["Almalaki", "ROYAL TV", "ROYAL+ Launcher", "RS TV", "RAMI Developer"],
        "icons": icons
    }
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps({
        "version": "V17",
        "slug": "android-system",
        "name_ar": collection["name_ar"],
        "description_ar": collection["description_ar"],
        "source_archive": "sources/ROYAL_Android_Icons_v2.zip",
        "source_svg_files": len(icons),
        "source_android_xml_files": len(icons),
        "icons": icons
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["versions"].append(collection)
    unique_2d = {i["variants"]["2d"] for v in manifest["versions"] for i in v["icons"]}
    unique_3d = {i["variants"]["3d"] for v in manifest["versions"] for i in v["icons"] if i["variants"].get("3d")}
    manifest.setdefault("totals", {}).update({
        "app_collections": len(manifest["versions"]),
        "concepts": len(unique_2d),
        "flat_svg": len(unique_2d),
        "dimensional_svg": len(unique_3d)
    })
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    html, count = re.subn(r"const embeddedManifest=(\{.*\});\s*const rootPrefix=", "const embeddedManifest=" + json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + ";\nconst rootPrefix=", html, count=1, flags=re.S)
    if count != 1:
        raise SystemExit("Could not update embedded manifest in index.html.")
    html = html.replace("معرض ROYAL Design من V2 إلى V15", "معرض ROYAL Design من V2 إلى V17")
    html = html.replace("المكتبات المشتركة V2–V9 والمجموعات الخاصة بالتطبيقات V10–V15", "المكتبات المشتركة V2–V9 والمجموعات الخاصة بالتطبيقات V10–V17")
    html = html.replace('<option value="3d">3D فقط</option>', '<option value="3d">3D فقط</option><option value="android_xml">Android XML فقط</option>')
    html = html.replace(".variant img{width:100%;height:104px;object-fit:contain;display:block}", ".variant img{width:100%;height:104px;object-fit:contain;display:block}.xml-preview{height:104px;display:grid;place-items:center;color:#dfbd65;font:750 17px ui-monospace,monospace;direction:ltr;letter-spacing:1px}")
    html = html.replace(".variant img{height:84px}", ".variant img,.xml-preview{height:84px}")
    html = html.replace("لكل إصدار لوحة ألوان مستقلة، وتظهر نسختا 2D و3D جنباً إلى جنب. معاينات الحركة اختيارية ولا تستبدل الأيقونات الثابتة. الأصول أصلية ضمن ترخيص ROYAL_ORIGINAL؛ يلزم اختبارها داخل التطبيق قبل اعتماد ربطها الإنتاجي.", "لكل إصدار لوحة ألوان مستقلة. تعرض الإصدارات V2–V16 نسختي 2D و3D، بينما يعرض V17 معاينة SVG وملف Android VectorDrawable XML الأصلي دون تسميته 3D. معاينات الحركة اختيارية. أصول V2–V16 ضمن ROYAL_ORIGINAL، وأصول V17 محفوظة من الحزمة المعتمدة بترخيص ROYAL_SOURCE_PACKAGE.")
    html = html.replace("مسارات 2D و3D محفوظة كملفات SVG مستقلة وقابلة للتكبير. ترخيص الأصول الداخلية: ROYAL_ORIGINAL. احتفظ ببيانات المنشأ عند نقل الأيقونات إلى تطبيقات ROYAL.", "ملفات SVG قابلة للتكبير، وملفات Android VectorDrawable الأصلية متاحة للتنزيل في V17. أصول V2–V16 ضمن ROYAL_ORIGINAL، وأصول V17 ضمن ROYAL_SOURCE_PACKAGE؛ احتفظ ببيانات المنشأ عند إعادة الاستخدام.")
    html = html.replace("function appVersionIsV16(icon){return icon.status==='source_package_preview'}", "function appVersionIsV16(icon){return icon.status==='source_package_preview'}\nfunction makeAndroidXml(icon){const path=icon.variants.android_xml;const box=el('div','variant');const link=el('a');link.href=assetUrl(path);link.download=path.split('/').pop();link.setAttribute('aria-label','تحميل Android VectorDrawable XML');link.append(el('div','xml-preview','<vector>'));link.append(el('div','variant-name','Android XML · VectorDrawable'));box.append(link);return box}")
    html = html.replace("const img=el('img');img.src=assetUrl(path);", "const img=el('img');img.src=assetUrl(path);")
    old = "if(styleFilter.value!=='3d')pair.append(makeVariant(icon,'2d'));if(styleFilter.value!=='2d')pair.append(makeVariant(icon,'3d'));"
    new = "if(app.version==='V17'){if(styleFilter.value==='all'||styleFilter.value==='2d')pair.append(makeVariant(icon,'2d'));if(styleFilter.value==='all'||styleFilter.value==='android_xml')pair.append(makeAndroidXml(icon))}else{if(styleFilter.value!=='3d'&&styleFilter.value!=='android_xml')pair.append(makeVariant(icon,'2d'));if(styleFilter.value!=='2d'&&styleFilter.value!=='android_xml')pair.append(makeVariant(icon,'3d'))}"
    if old not in html:
        raise SystemExit("Could not locate gallery card rendering block.")
    html = html.replace(old, new)
    html = html.replace("new Set(collections.flatMap(a=>a.icons.map(i=>i.variants['3d']))).size+' نسخة 3D'", "new Set(collections.flatMap(a=>a.icons.filter(i=>i.variants['3d']).map(i=>i.variants['3d']))).size+' نسخة 3D',new Set(collections.flatMap(a=>a.icons.filter(i=>i.variants.android_xml).map(i=>i.variants.android_xml))).size+' Android XML'")
    HTML.write_text(html, encoding="utf-8")
    readme = ROOT / "README.md"
    readme_text = readme.read_text(encoding="utf-8")
    readme_text = readme_text.replace("- **V15:** ROYAL AUDIO — المؤثرات الطبيعية وأدوات مشغل الصوت، دون أصوات بشرية.", "- **V15:** ROYAL AUDIO — المؤثرات الطبيعية وأدوات مشغل الصوت، دون أصوات بشرية.\n- **V16:** حزمة أيقونات ROYAL المتقدمة للمتجر والتلفاز وواجهة المشغّل.\n- **V17:** أيقونات أندرويد — معاينات SVG وملفات Android VectorDrawable الأصلية.")
    readme_text = readme_text.replace("14 إصداراً من V2 إلى V15.", "16 إصداراً من V2 إلى V17.")
    readme_text = readme_text.replace("227 مفهوماً فريداً.", f"{len(unique_2d)} مفهوماً فريداً.")
    readme_text = readme_text.replace("227 ملف 2D و227 ملف 3D فريد.", f"{len(unique_2d)} ملف SVG للمعاينة، و{len(unique_3d)} ملف 3D، و{len(icons)} ملف Android XML.")
    readme_text = readme_text.replace("- لكل مفهوم نسختان **2D** و **3D** متجاورتان.", "- إصدارات V2–V16 تعرض نسختي **2D** و **3D** متجاورتين.\\n- V17 تعرض معاينة **SVG** وملف **Android VectorDrawable XML** الأصلي.")
    readme_text = readme_text.replace("الأصول أصلية ضمن مكتبة **ROYAL Design** وتحمل ترخيص **ROYAL_ORIGINAL**.", "أصول V2–V16 أصلية ضمن مكتبة **ROYAL Design** وتحمل ترخيص **ROYAL_ORIGINAL**. أصول V17 محفوظة من الحزمة المعتمدة وتحمل ترخيص **ROYAL_SOURCE_PACKAGE**.")
    readme.write_text(readme_text, encoding="utf-8")
    print(f"Imported V17: {len(icons)} matched SVG + Android VectorDrawable pairs.")
    
if __name__ == "__main__":
    main()
