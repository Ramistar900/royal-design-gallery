# تصنيف حزمة ROYAL Design المشتركة

## خريطة التطبيقات

| التطبيق | المجموعة المناسبة | القرار الأولي |
|---|---|---|
| Almalaki | أيقونات المتجر والمقهى | مرشح أساسي؛ لا تستبدل الهوية الخضراء الحالية أو الشعار |
| ROYAL TV | أيقونات التلفاز والقنوات | مرشح أساسي للرموز الوظيفية، لا للشعار |
| RS TV / Sinjar TV | مجموعة التلفاز نفسها | استخدام مشترك دون نسخ الملفات |
| ROYAL+ Launcher | أيقونات الواجهة 16 × 3 حالات | المطابقة الأقوى؛ الحالات الثابتة والمتحركة والمركّزة |
| ROYAL AUDIO | عشرة رموز تحكم بالوسائط | استخدام محدود للتحكم فقط؛ لا توجد مجموعة هوية صوتية مستقلة |
| RAMI Developer | رموز إدارية عامة | استخدام مشترك فقط؛ لا توجد رموز بناء/إصدارات/توقيع خاصة |

## المجموعات ومحتوياتها

- restaurant_tv_3d_icons.zip: 37 رمز متجر × حالتين و42 رمز تلفاز × حالتين؛ أي 158 SVG، إضافة إلى README والمعاينة.
- restaurant_tv_launcher_icons.zip: أربعة ملفات SVG بألوان برتقالية/بنفسجية.
- restaurant_tv_launcher_icons (1).zip: أربعة ملفات SVG بألوان ذهبية/زرقاء؛ هذه نسخة تصميم بديلة وليست نسخة مطابقة.
- restaurant_tv_launcher_ui_icons.zip: 16 رمز واجهة بثلاث حالات، بإجمالي 48 SVG.
- restaurant_tv_launcher_ui_icons (1).zip: 48 ملفاً مطابقاً بايتياً للحزمة السابقة؛ أبقيناها كنسخة مصدر احتياطية.

## الرموز المحددة لكل تطبيق

### Almalaki (37 رمزاً مرشحاً)
- الحالات: static, animated
- add, back, bell, calendar, cart, chat, check, clock, close, coffee, delivery, dessert, drink, edit, filter, food, heart, home, loading, location, login, logout, menu, offer, orders, payment, phone, profile, remove, restaurant, search, settings, share, star, table, trash, wifi
- ملاحظة: The pack uses orange/gold glossy tiles, while Almalaki's current visual identity includes emerald elements. Treat as optional library assets; do not replace the current app logo, banners, or established emerald styling.

### ROYAL TV (42 رمزاً مرشحاً)
- الحالات: static, animated
- add, back, bell, cast, channels, check, clock, close, filter, forward, fullscreen, grid, guide, heart, home, info, language, live, loading, lock, mute, next, pause, play, power, prev, record, refresh, remote, remove, rewind, search, settings, share, sleep, source, star, stop, timer, volume_down, volume_up, wifi
- ملاحظة: Functional icon set only. It is not a verified ROYAL TV brand logo or complete screen design.

### RS TV / Sinjar TV (42 رمزاً مرشحاً)
- الحالات: static, animated
- add, back, bell, cast, channels, check, clock, close, filter, forward, fullscreen, grid, guide, heart, home, info, language, live, loading, lock, mute, next, pause, play, power, prev, record, refresh, remote, remove, rewind, search, settings, share, sleep, source, star, stop, timer, volume_down, volume_up, wifi
- ملاحظة: The pack does not contain a dedicated RS TV / Sinjar brand mark, watermark, or channel-country flag system.

### ROYAL+ Launcher (16 رمزاً مرشحاً)
- الحالات: static, animated, focused
- apps, favorites, guide, home, input, kids, live_tv, movies, music, notifications, profile, recent, search, series, settings, sports
- ملاحظة: This is the strongest direct match in the package. Keep all three states; use focused state for TV remote selection. The duplicate second archive is byte-identical and should be treated as a backup, not a second variant.

### ROYAL AUDIO (10 رمزاً مرشحاً)
- الحالات: static, animated
- play, pause, stop, next, prev, forward, rewind, volume_up, volume_down, mute
- ملاحظة: No dedicated ROYAL AUDIO identity, soundscape artwork, or audio-category icon set is present. These are controls only and do not introduce voice/audio content.

### RAMI Developer (15 رمزاً مرشحاً)
- الحالات: static, animated
- settings, profile, login, logout, bell, search, calendar, clock, check, edit, trash, lock, wifi, refresh, info
- ملاحظة: No dedicated developer, build, release, signing, owner-code, or dashboard icon family is present. Do not present these generic symbols as RAMI branding.

### Shared ROYAL Design (16 رمزاً مرشحاً)
- الحالات: static, animated
- home, back, close, add, remove, check, search, settings, bell, star, heart, clock, filter, share, wifi, loading
- ملاحظة: Reference shared files instead of copying them into each application's asset folder.

## ملاحظات تقنية قبل ربطها بالتطبيقات

- الأيقونات ذات تأثير 3D هي رسومات SVG بتدرجات وظلال ولمعان، وليست ملفات نماذج ثلاثية الأبعاد.
- ملفات animated/ تستخدم SMIL (animate و/أو animateTransform). لا تفترض أن Android سيشغّلها مباشرة.
- ملفات focused/ مناسبة كحالة تحديد لعناصر Android TV، لكن يجب اختبار التباين ومقاس التركيز مع الريموت.
- مجموعة المتجر برتقالية/ذهبية بينما Almalaki لديه عناصر هوية زمردية؛ لا تُفرض هذه الألوان على التطبيق.
- الشعارات واللافتات المرفقة عامة باسم المتجر أو التلفاز، وليست شعارات موثقة للتطبيقات الحالية.

## نتائج الفحص الآلي

- SVG المفحوصة: 262
- محتويات SVG الفريدة ببصمة SHA-256: 212
- مجموعات التكرار المطابق: 50
- ملفات SVG غير الصالحة: 0
- ملفات دون viewBox: 0
- ملفات تحوي مراجع HTTP خارجية: 0
- ملفات تحوي SMIL: 111

التقرير التفصيلي في technical-audit.json، وقواعد التصنيف في classification.json.
هذا تصنيف للأصول فقط؛ لم يتم ربطها بكود أي تطبيق أو اعتمادها كتغيير إنتاجي.
