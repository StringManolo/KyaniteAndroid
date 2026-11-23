#!/usr/bin/env python3
"""Genera la web en 4 idiomas (es, en, ru, zh-CN) a partir de UNA fuente: src/index.src.html

  python3 build_site.py

Produce:  index.html (es) · en/index.html · ru/index.html · zh-CN/index.html · sitemap.xml
  - <html lang>, <title>, descripción, Open Graph / Twitter / JSON-LD, canonical y hreflang de cada página
  - selector de idioma (enlaces reales a cada URL) y, si el idioma del navegador es otro, un aviso discreto (sin redirigir)
  - enlaces de documentación apuntan a la versión del idioma de la página (docs/<idioma>/..., README.<idioma>.md)

Se edita SIEMPRE src/index.src.html (es/en en pares <span lang="es">..</span><span lang="en">..</span>) y se vuelve a
ejecutar este script. Los textos ru y zh-CN están en la tabla TR de abajo: si añades un texto nuevo, el script se
detiene y te dice qué clave falta traducir. No se escribe nada si falta alguna.
"""
import datetime, json, os, re, shutil, sys

SITE = "https://stringmanolo.github.io/KyaniteAndroid/"      # con barra final
SRC = "src/index.src.html"
MARK = "built by build_site.py"
KY = "https://github.com/StringManolo/Kyanite"
APK64 = "https://github.com/StringManolo/KyaniteAndroid/releases/latest/download/Kyanite.apk"
APK32 = "https://github.com/StringManolo/KyaniteAndroid/releases/latest/download/kyanite_v7.apk"
X_DEFAULT = "en"                                              # página para idiomas no cubiertos (hreflang x-default)

LANGS = [  # código, carpeta, nombre nativo, og:locale
    ("es", "", "Español", "es_ES"),
    ("en", "en/", "English", "en_US"),
    ("ru", "ru/", "Русский", "ru_RU"),
    ("zh-CN", "zh-CN/", "中文", "zh_CN"),
]
CODES = [l[0] for l in LANGS]
DIR = {c: d for c, d, _, _ in LANGS}
NAME = {c: n for c, _, n, _ in LANGS}
LOC = {c: o for c, _, _, o in LANGS}

# Anclas dentro de las páginas traducidas (los títulos cambian con el idioma, así que por defecto se enlaza al
# inicio del documento). Ejemplo: ANCHORS[("es", "https://github.com/stringmanolo/kyanite#in-short")] = "#en-resumen"
ANCHORS = {}

META = {
    "es": dict(title="Kyanite para Android | Linux privado en tu móvil",
               desc="Kyanite: un Linux privado y seguro en tu Android. Cifrado, borrado antiforense y bloqueo de red. Sin root.",
               alt="Kyanite para Android: un Linux privado en tu móvil",
               menu="Idioma", suggest="Ver esta página en español", close="Cerrar"),
    "en": dict(title="Kyanite for Android | Private Linux on your phone",
               desc="Kyanite: a private, secure Linux on your Android. Encryption, anti-forensic wipe and a network kill switch. No root.",
               alt="Kyanite for Android: a private Linux on your phone",
               menu="Language", suggest="View this page in English", close="Close"),
    "ru": dict(title="Kyanite для Android | Личный Linux на вашем телефоне",
               desc="Kyanite: приватный и безопасный Linux на вашем Android. Шифрование, антикриминалистическое стирание данных и отключение сети. Без root.",
               alt="Kyanite для Android: личный Linux на вашем телефоне",
               menu="Язык", suggest="Открыть страницу на русском", close="Закрыть"),
    "zh-CN": dict(title="Kyanite 安卓版 | 手机上的私密 Linux",
                  desc="Kyanite：在你的 Android 手机上运行的私密、安全的 Linux。支持加密、反取证擦除和网络断开，无需 root。",
                  alt="Kyanite 安卓版：手机上的私密 Linux",
                  menu="语言", suggest="查看中文版", close="关闭"),
}

# aria-label bilingües o solo-es del origen -> texto por idioma
ATTRS = [
    ('aria-label="Principal"', {"es": "Principal", "en": "Main", "ru": "Главное меню", "zh-CN": "主导航"}),
    ('aria-label="Abrir menú"', {"es": "Abrir menú", "en": "Open menu", "ru": "Открыть меню", "zh-CN": "打开菜单"}),
    ('aria-label="Ver todas las funciones / See all features"',
     {"es": "Ver todas las funciones", "en": "See all features", "ru": "Посмотреть все возможности", "zh-CN": "查看全部功能"}),
    ('aria-label="Cerrar / Close"', {"es": "Cerrar", "en": "Close", "ru": "Закрыть", "zh-CN": "关闭"}),
]
BADGE_ALT = {"ru": "Доступно на GitHub", "zh-CN": "在 GitHub 上获取"}

# Traducciones: clave = texto en inglés normalizado ({a32}/{a64} = enlaces a los APK) -> (ru, zh-CN)
TR = {
    "Skip to content": ("Перейти к содержимому", "跳到正文"),
    "Home": ("Главная", "首页"),
    "User guide": ("Руководство пользователя", "用户指南"),
    "Security": ("Безопасность", "安全"),
    "Report a bug": ("Сообщить об ошибке", "报告问题"),
    "Download": ("Скачать", "下载"),
    'Your own<br><span class="accent">private Linux on your Android</span>':
        ('Ваш собственный<br><span class="accent">приватный Linux на вашем Android</span>',
         '你自己的<br><span class="accent">Android 私密 Linux</span>'),
    "Create a separate Linux environment on your phone, with encryption, anti-forensic wipe and a network kill switch. No root needed.":
        ("Создайте отдельную среду Linux на телефоне: с шифрованием, антикриминалистическим стиранием данных и отключением сети одним переключателем. Root не нужен.",
         "在手机上创建一个独立的 Linux 环境，支持加密、反取证擦除和网络一键断开。无需 root。"),
    "Download APK": ("Скачать APK", "下载 APK"),
    'Won’t install on your phone? <a href="{a32}">Try the version for older phones</a>.':
        ('Не устанавливается на вашем телефоне? <a href="{a32}">Попробуйте версию для старых телефонов</a>.',
         '无法在你的手机上安装？<a href="{a32}">试试适用于旧手机的版本</a>。'),
    'We picked the version that fits your phone. Won’t install? <a href="{a64}">Try the other one</a>.':
        ('Мы выбрали версию, подходящую вашему телефону. Не устанавливается? <a href="{a64}">Попробуйте другую</a>.',
         '我们为你的手机选择了合适的版本。无法安装？<a href="{a64}">试试另一个版本</a>。'),
    "A Linux of just 10 MB": ("Linux всего на 10 МБ", "只有 10 MB 的 Linux"),
    "Kyanite is built from Rust components, a language that rules out whole classes of memory bugs. Small, light and safer from the ground up.":
        ("Kyanite собран из компонентов на Rust — языке, который исключает целые классы ошибок работы с памятью. Маленький, лёгкий и более безопасный с самого основания.",
         "Kyanite 由 Rust 组件构成，这门语言从根本上杜绝了整类内存错误。体积小、轻量，从底层起就更安全。"),
    "All of Debian, one command away": ("Весь Debian — одной командой", "整个 Debian，一条命令即可获取"),
    "Install thousands of packages with kpkg or the apt commands you already know. Nothing new to learn.":
        ("Устанавливайте тысячи пакетов через kpkg или привычные команды apt. Ничего нового учить не нужно.",
         "用 kpkg 或你熟悉的 apt 命令安装数以千计的软件包，无需学习任何新东西。"),
    "Normal, ephemeral or virtual machine": ("Обычный, временный или виртуальная машина", "普通、临时或虚拟机模式"),
    "Keep your work, start fresh every session, or boot a virtual machine (on RAM) that writes nothing to your phone’s storage.":
        ("Сохраняйте свою работу, начинайте с чистого листа в каждом сеансе или запускайте виртуальную машину (в ОЗУ), которая ничего не записывает в память телефона.",
         "保留你的工作成果，每次会话都从头开始，或启动一台在内存中运行、不向手机存储写入任何内容的虚拟机。"),
    "Encrypted and locked": ("Зашифровано и под замком", "加密并上锁"),
    "Your systems are stored encrypted with AES-256 and the app locks behind a PIN. Add a duress PIN that wipes everything.":
        ("Ваши системы хранятся в зашифрованном виде (AES-256), а приложение защищено PIN-кодом. Добавьте PIN под принуждением, который стирает всё.",
         "你的系统以 AES-256 加密存储，应用需 PIN 码解锁。还可设置胁迫 PIN，输入后清除全部数据。"),
    "Anti-forensic wipe": ("Антикриминалистическое стирание", "反取证擦除"),
    "Triggers after wrong PINs, a long time without opening the app, or when USB debugging gets turned on. It destroys the key, overwrites the data and deletes everything.":
        ("Срабатывает после неверных PIN-кодов, при долгом неоткрытии приложения или при включении отладки по USB. Уничтожает ключ, перезаписывает данные и удаляет всё.",
         "在多次输错 PIN、长时间未打开应用或开启 USB 调试时触发：销毁密钥、覆写数据并删除一切。"),
    "Network off with one switch": ("Сеть отключается одним переключателем", "一键断网"),
    "A local VPN with no exit cuts internet for the app and everything running inside it. No connection, no surprises.":
        ("Локальный VPN без выхода в сеть отключает интернет для приложения и всего, что в нём запущено. Нет соединения — нет сюрпризов.",
         "一个没有出口的本地 VPN 会切断应用及其内部所有程序的网络。没有连接，就没有意外。"),
    "Floating window": ("Плавающее окно", "悬浮窗口"),
    "Move, resize, rotate and fade the terminal so you can use it on top of any other app.":
        ("Перемещайте, изменяйте размер, поворачивайте и делайте терминал прозрачным, чтобы пользоваться им поверх любого другого приложения.",
         "可移动、缩放、旋转并调节终端透明度，让你在任何其他应用之上使用它。"),
    "All your systems": ("Все ваши системы", "你的所有系统"),
    "Import or download Alpine, Ubuntu Base and Arch Linux ARM, and keep snapshots to roll back whenever you want.":
        ("Импортируйте или скачивайте Alpine, Ubuntu Base и Arch Linux ARM и храните снимки, чтобы откатиться в любой момент.",
         "导入或下载 Alpine、Ubuntu Base 和 Arch Linux ARM，并保留快照，随时回滚。"),
    "Your private Linux. On your phone.": ("Ваш личный Linux. На вашем телефоне.", "你的私密 Linux，就在你的手机上。"),
    "Based on DebianLiveCD4Android": ("На основе DebianLiveCD4Android", "基于 DebianLiveCD4Android"),
    "Product &amp; help": ("Продукт и помощь", "产品与帮助"),
    "Official download": ("Официальная загрузка", "官方下载"),
    "Kyanite, the distro": ("Kyanite — дистрибутив", "Kyanite 发行版"),
    "Get in touch": ("Связаться", "联系方式"),
    "Security policy": ("Политика безопасности", "安全策略"),
    "Third-party licenses": ("Лицензии сторонних компонентов", "第三方许可证"),
    "Download Kyanite": ("Скачать Kyanite", "下载 Kyanite"),
    "Choose a download option.": ("Выберите вариант загрузки.", "请选择下载方式。"),
}

EXTRA_CSS = """
/* --- añadido por build_site.py: selector de idioma, aviso de idioma y ajustes ru / zh-CN --- */
.lang-menu{position:relative}
.lang-menu>summary{list-style:none;cursor:pointer}
.lang-menu>summary::-webkit-details-marker{display:none}
.lang-menu>ul{position:absolute;right:0;top:calc(100% - 2px);margin:0;padding:6px;list-style:none;min-width:150px;background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:0 12px 30px #0f1f4a1f;z-index:30}
.lang-menu li a{display:block;padding:9px 12px;border-radius:8px;font-size:14px;line-height:1.4;color:var(--ink);white-space:nowrap}
.lang-menu li a:hover,.lang-menu li a[aria-current]{background:#f1f4fa;color:var(--accent)}
.lang-suggest{display:flex;align-items:center;justify-content:center;gap:12px;padding:8px 14px;background:var(--accent);color:#fff;font-size:14px;line-height:1.4;text-align:center}
.lang-suggest a{color:#fff;text-decoration:underline;text-underline-offset:3px;font-weight:600}
.lang-suggest button{border:0;background:transparent;color:#fff;font-size:22px;line-height:1;padding:4px 8px;min-width:32px;min-height:32px}
html[lang="zh-CN"]{--font:Inter,-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Noto Sans SC","Segoe UI",sans-serif}
html[lang="zh-CN"] :is(h1,h2,h3,p,a,span,.brand){letter-spacing:0!important}
html[lang="ru"] .product-wide .product-copy h2{font-size:clamp(30px,3.4vw,40px)}
"""

# ---------------------------------------------------------------------------------------------------------------------

OPEN = re.compile(r'<span lang="(es|en)">')
TOK = re.compile(r'<span\b|</span>')


def die(msg):
    sys.exit("ERROR: " + msg)


def read_block(s, pos):
    m = OPEN.match(s, pos)
    if not m:
        return None
    depth, i = 1, m.end()
    while True:
        t = TOK.search(s, i)
        if not t:
            die("<span lang=...> sin cerrar cerca de: %r" % s[pos:pos + 80])
        depth += 1 if t.group(0) != "</span>" else -1
        if depth == 0:
            return m.group(1), s[m.end():t.start()], t.end()
        i = t.end()


def span_pairs(s):
    pairs, pos = [], 0
    while True:
        m = OPEN.search(s, pos)
        if not m:
            return pairs
        lang1, in1, end1 = read_block(s, m.start())
        p2 = re.compile(r"\s*").match(s, end1).end()
        b2 = read_block(s, p2)
        if lang1 != "es" or not b2 or b2[0] != "en":
            die("<span lang=...> sin pareja es+en cerca de: %r" % s[m.start():m.start() + 90])
        pairs.append((m.start(), b2[2], in1, b2[1]))
        pos = b2[2]


def norm(x):
    x = x.replace(APK32, "{a32}").replace(APK64, "{a64}")
    return re.sub(r"\s+", " ", x).strip()


def page_url(code):
    return SITE + DIR[code]


def rel(from_code, to_code):
    a, b = DIR[from_code], DIR[to_code]
    up = "../" if a else ""
    if a == b:
        return "./"
    return up + b


def localize(url, code):
    if code == "en":
        return url
    m = re.match(r"(?i)https://github\.com/stringmanolo/kyanite/blob/main/docs/([a-z0-9._-]+\.md)(#.*)?$", url)
    if m:
        return "%s/blob/main/docs/%s/%s%s" % (KY, code, m.group(1), ANCHORS.get((code, url), ""))
    if re.match(r"(?i)https://github\.com/stringmanolo/kyanite#.+$", url):
        return "%s/blob/main/README.%s.md%s" % (KY, code, ANCHORS.get((code, url), ""))
    return url


def seo_block(code, verif):
    m = META[code]
    url = page_url(code)
    esc = lambda t: t.replace("&", "&amp;").replace('"', "&quot;")
    img = SITE + "assets/og.png"
    L = [verif] if verif else []
    L += ["<!-- seo:start -->",
          '<meta property="og:type" content="website">',
          '<meta property="og:site_name" content="Kyanite">',
          '<meta property="og:title" content="%s">' % esc(m["title"]),
          '<meta property="og:description" content="%s">' % esc(m["desc"]),
          '<meta property="og:image" content="%s">' % img,
          '<meta property="og:image:alt" content="%s">' % esc(m["alt"]),
          '<meta property="og:locale" content="%s">' % LOC[code]]
    L += ['<meta property="og:locale:alternate" content="%s">' % LOC[c] for c in CODES if c != code]
    L += ['<meta name="twitter:card" content="summary_large_image">',
          '<meta name="twitter:title" content="%s">' % esc(m["title"]),
          '<meta name="twitter:description" content="%s">' % esc(m["desc"]),
          '<meta name="twitter:image" content="%s">' % img,
          '<link rel="canonical" href="%s">' % url,
          '<meta property="og:url" content="%s">' % url]
    L += ['<link rel="alternate" hreflang="%s" href="%s">' % (c, page_url(c)) for c in CODES]
    L += ['<link rel="alternate" hreflang="x-default" href="%s">' % page_url(X_DEFAULT)]
    ld = {"@context": "https://schema.org", "@type": "SoftwareApplication", "name": "Kyanite",
          "applicationCategory": "UtilitiesApplication", "operatingSystem": "Android",
          "description": m["desc"], "inLanguage": code, "image": img,
          "downloadUrl": "https://github.com/StringManolo/KyaniteAndroid/releases/latest",
          "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
          "sameAs": ["https://github.com/StringManolo/KyaniteAndroid", KY], "url": url}
    L += ['<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"),
          "<!-- seo:end -->"]
    return "\n".join(L)


def lang_menu(code, svg):
    items = []
    for c in CODES:
        cur = ' aria-current="true"' if c == code else ""
        items.append('<li><a href="%s" hreflang="%s" lang="%s"%s>%s</a></li>' % (rel(code, c), c, c, cur, NAME[c]))
    return ('<details class="lang-menu"><summary class="language" aria-label="%s">%s<span>%s</span></summary><ul>%s</ul></details>'
            % (META[code]["menu"], svg, NAME[code], "".join(items)))


def lang_js(code):
    links = {c: {"t": META[c]["suggest"], "c": META[c]["close"], "u": rel(code, c)} for c in CODES}
    return """  /* idioma: no se redirige; si el navegador usa otro idioma se ofrece la versión correspondiente */
  var LANG_LINKS = %s;
  var LANG_KEY = 'kyanite-lang-dismissed';
  function browserLang(){
    var list = (navigator.languages && navigator.languages.length) ? navigator.languages : [navigator.language || ''];
    for (var i = 0; i < list.length; i++){
      var l = String(list[i]).toLowerCase();
      if (/^es(-|$)/.test(l)) return 'es';
      if (/^en(-|$)/.test(l)) return 'en';
      if (/^ru(-|$)/.test(l)) return 'ru';
      if (/^zh(-|$)/.test(l)) return 'zh-CN';
    }
    return null;
  }
  function rememberLang(){ try { localStorage.setItem(LANG_KEY, '1'); } catch (e) {} }
  var wantLang = browserLang();
  var langDismissed = false;
  try { langDismissed = localStorage.getItem(LANG_KEY) === '1'; } catch (e) {}
  if (wantLang && wantLang !== html.getAttribute('lang') && !langDismissed && LANG_LINKS[wantLang]) {
    var bar = document.createElement('div');
    bar.className = 'lang-suggest';
    bar.setAttribute('lang', wantLang);
    var go = document.createElement('a');
    go.href = LANG_LINKS[wantLang].u;
    go.textContent = LANG_LINKS[wantLang].t;
    go.addEventListener('click', rememberLang);
    var x = document.createElement('button');
    x.type = 'button';
    x.setAttribute('aria-label', LANG_LINKS[wantLang].c);
    x.textContent = '\\u00d7';
    x.addEventListener('click', function(){ rememberLang(); if (bar.parentNode) bar.parentNode.removeChild(bar); });
    bar.appendChild(go);
    bar.appendChild(x);
    document.body.insertBefore(bar, document.body.firstChild);
  }
  var langMenu = document.querySelector('.lang-menu');
  if (langMenu) {
    langMenu.addEventListener('click', function(e){ if (e.target.closest && e.target.closest('a')) rememberLang(); });
    document.addEventListener('click', function(e){ if (!langMenu.contains(e.target)) langMenu.removeAttribute('open'); });
    document.addEventListener('keydown', function(e){ if (e.key === 'Escape') langMenu.removeAttribute('open'); });
  }

""" % json.dumps(links, ensure_ascii=False)


def build_page(src, code, missing):
    s = src
    m = META[code]
    # 1) metas de verificación (Google, Bing, ...) se conservan fuera del bloque generado
    verif = "\n".join(re.findall(r'<meta name="[^"]*(?:verification|msvalidate)[^"]*"[^>]*>', s))
    s, n = re.subn(r"<!-- seo:start -->.*?<!-- seo:end -->\n?", "@@SEO@@\n", s, count=1, flags=re.S)
    if n != 1:
        die("no encuentro el bloque <!-- seo:start --> ... <!-- seo:end --> en %s" % SRC)
    s = re.sub(r'<meta name="[^"]*(?:verification|msvalidate)[^"]*"[^>]*>\n?', "", s)
    s = s.replace("@@SEO@@", seo_block(code, verif))
    # 2) idioma, título y descripción
    if '<html lang="es">' not in s:
        die('el origen debe empezar con <html lang="es">')
    s = s.replace('<html lang="es">', '<html lang="%s">' % code, 1)
    s = re.sub(r"<title>.*?</title>", lambda _: "<title>%s</title>" % m["title"], s, count=1, flags=re.S)
    s = re.sub(r'<meta name="description" content=".*?">', lambda _: '<meta name="description" content="%s">' % m["desc"], s, count=1, flags=re.S)
    s = s.replace("<head>", "<head>\n<!-- %s from %s: edit the source, not this file -->" % (MARK, SRC), 1)
    # 3) selector de idioma (sustituye al botón) y bloque JS de idioma
    btn = re.search(r'<button class="language" id="lang".*?</button>', s, re.S)
    if not btn:
        die('no encuentro <button class="language" id="lang"> en el origen')
    svg = re.search(r"<svg.*?</svg>", btn.group(0), re.S).group(0)
    s = s.replace(btn.group(0), lang_menu(code, svg), 1)
    a, b = s.find("  /* idioma */"), s.find("  /* menú hamburguesa")
    if a < 0 or b < a:
        die("no encuentro el bloque JS '/* idioma */' en el origen")
    s = s[:a] + lang_js(code) + s[b:]
    s = re.sub(r"\n  var langBtn = document\.getElementById\('lang'\);\n  var label = document\.getElementById\('lang-label'\);", "", s)
    s = re.sub(r'html\[lang="es"\] \[lang="en"\],\s*html\[lang="en"\] \[lang="es"\]\{display:none\}', "", s)
    # 4) enlaces a la documentación en el idioma de la página
    s = re.sub(r'(<a href=")https://github\.com/StringManolo/Kyanite("[^>]*>\s*<span lang="es">Kyanite, la distro)', r"\1@@README@@\2", s)
    s = s.replace("@@README@@", "%s/blob/main/README%s.md" % (KY, "" if code == "en" else "." + code))
    s = re.sub(r'href="(https://github\.com/[^"]+)"', lambda mm: 'href="%s"' % localize(mm.group(1), code), s)
    # 5) atributos con texto
    for old, per in ATTRS:
        if old not in s:
            die("no encuentro %s en el origen" % old)
        s = s.replace(old, 'aria-label="%s"' % per[code])
    # 6) insignias de GitHub (img es/en)
    def badge(mm):
        if code == "es":
            return '<img src="%s" alt="%s" width="%s" height="%s">' % (mm["s1"], mm["a1"], mm["w"], mm["h"])
        if code == "en":
            return '<img src="%s" alt="%s" width="%s" height="%s">' % (mm["s2"], mm["a2"], mm["w"], mm["h"])
        cand = mm["s2"].replace("-en.svg", "-%s.svg" % code)
        src_img = cand if os.path.exists(cand) else mm["s2"]
        return '<img src="%s" alt="%s" width="%s" height="%s">' % (src_img, BADGE_ALT[code], mm["w"], mm["h"])
    s = re.sub(r'<img lang="es" src="(?P<s1>[^"]+)" alt="(?P<a1>[^"]*)" width="(?P<w>\d+)" height="(?P<h>\d+)">\s*'
               r'<img lang="en" src="(?P<s2>[^"]+)" alt="(?P<a2>[^"]*)" width="\d+" height="\d+">', badge, s)
    # 7) pares <span lang="es"> / <span lang="en">
    out, last = [], 0
    for start, end, in_es, in_en in span_pairs(s):
        if code == "es":
            txt = in_es
        elif code == "en":
            txt = in_en
        else:
            key = norm(in_en)
            if key not in TR:
                missing.add(key)
                txt = in_en
            else:
                txt = TR[key][0 if code == "ru" else 1].replace("{a32}", APK32).replace("{a64}", APK64)
        out.append(s[last:start]); out.append(txt); last = end
    out.append(s[last:])
    s = "".join(out)
    # 8) CSS extra y rutas relativas
    s = s.replace("</style>", EXTRA_CSS + "</style>", 1)
    if DIR[code]:
        s = s.replace('src="assets/', 'src="../assets/').replace('href="assets/', 'href="../assets/')
    if re.search(r'<(span|img)[^>]* lang="(es|en)"', s):
        # solo debe quedar el selector de idioma, que usa <a lang=...>
        die("quedan elementos <span>/<img lang=...> sin convertir en la página %s" % code)
    return s


def sitemap():
    today = datetime.date.today().isoformat()
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for c in CODES:
        rows.append("  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>" % (page_url(c), today))
        rows += ['    <xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (x, page_url(x)) for x in CODES]
        rows.append('    <xhtml:link rel="alternate" hreflang="x-default" href="%s"/>\n  </url>' % page_url(X_DEFAULT))
    rows.append("</urlset>\n")
    return "\n".join(rows)


def main():
    if not os.path.exists(SRC):
        if os.path.exists("index.html") and MARK not in open("index.html", encoding="utf-8").read():
            os.makedirs("src", exist_ok=True)
            shutil.copy("index.html", SRC)
            print("primera ejecución: copiado index.html -> %s (a partir de ahora se edita ese archivo)" % SRC)
        else:
            die("no encuentro %s ni un index.html original" % SRC)
    src = open(SRC, encoding="utf-8").read()
    missing, pages = set(), {}
    for code in CODES:
        pages[code] = build_page(src, code, missing)
    if missing:
        print("Faltan traducciones (añádelas a TR en build_site.py, clave -> (ru, zh-CN)):", file=sys.stderr)
        for k in sorted(missing):
            print("  %r" % k, file=sys.stderr)
        sys.exit(1)
    for code in CODES:
        path = DIR[code] + "index.html"
        if DIR[code]:
            os.makedirs(DIR[code], exist_ok=True)
        open(path, "w", encoding="utf-8").write(pages[code])
        print("escrito", path)
    open("sitemap.xml", "w", encoding="utf-8").write(sitemap())
    print("escrito sitemap.xml")


if __name__ == "__main__":
    main()
