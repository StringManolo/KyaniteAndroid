#!/usr/bin/env python3
"""Añade a index.html la detección automática de móviles de 32 bits (descarga de kyanite_v7.apk).

Uso:  python3 patch_index.py [index.html]      (guarda una copia en index.html.bak)
Es idempotente: si ya está aplicado, no hace nada. Si el HTML no coincide con lo esperado, aborta sin tocar nada.
"""
import shutil, sys

path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
s = open(path, encoding="utf-8").read()
if "data-apk-note" in s:
    sys.exit("ya aplicado: no hago nada")

APK32 = "https://github.com/StringManolo/KyaniteAndroid/releases/latest/download/kyanite_v7.apk"
APK64 = "https://github.com/StringManolo/KyaniteAndroid/releases/latest/download/Kyanite.apk"

CSS = """.product-hero-actions{margin-top:30px;margin-bottom:14px}
/* nota bajo los botones de descarga (versión para móviles de 32 bits) */
.apk-note{max-width:416px;margin:0 0 6px;font-size:13px;line-height:1.6;color:var(--muted)}
.apk-note a{color:var(--accent);text-decoration:underline;text-underline-offset:3px}
.apk-note a:hover{color:var(--accent-dark)}
@media(max-width:700px){.apk-note{max-width:360px;margin-inline:auto;text-align:center}.download-dialog .apk-note{text-align:left;margin-inline:0}}
"""

NOTE = """      <p class="apk-note" data-apk-note>
        <span data-state="default">
          <span lang="es">¿No se instala en tu móvil? <a href="%(a32)s">Prueba la versión para móviles antiguos</a>.</span>
          <span lang="en">Won’t install on your phone? <a href="%(a32)s">Try the version for older phones</a>.</span>
        </span>
        <span data-state="v7" hidden>
          <span lang="es">Hemos elegido la versión que encaja con tu móvil. ¿No se instala? <a href="%(a64)s">Prueba la otra</a>.</span>
          <span lang="en">We picked the version that fits your phone. Won’t install? <a href="%(a64)s">Try the other one</a>.</span>
        </span>
      </p>
""" % {"a32": APK32, "a64": APK64}

JS = """
  /* descarga: elige el APK según el móvil (arm64 por defecto, 32 bits si se detecta) */
  var APK_32 = '%s';
  var apkLinks = document.querySelectorAll('[data-apk]');
  function is32bitPhone(){
    if (!/Android/i.test(navigator.userAgent || '')) return Promise.resolve(false);
    /* navegadores antiguos: navigator.platform decía "Linux armv7l"; hoy Chrome y Firefox lo congelan en "Linux armv81" */
    var legacy = /armv[567]/i.test(navigator.platform || '');
    var uad = navigator.userAgentData;
    if (!uad || !uad.getHighEntropyValues) return Promise.resolve(legacy);
    return uad.getHighEntropyValues(['architecture', 'bitness']).then(function(v){
      if (!v || !v.bitness) return legacy;
      return /arm/i.test(v.architecture || '') && String(v.bitness) === '32';
    }, function(){ return legacy; });
  }
  function use32(){
    Array.prototype.forEach.call(apkLinks, function(a){ a.href = APK_32; });
    Array.prototype.forEach.call(document.querySelectorAll('[data-apk-note] [data-state]'), function(el){
      el.hidden = el.getAttribute('data-state') !== 'v7';
    });
  }
  is32bitPhone().then(function(is32){ if (is32) use32(); });
""" % APK32

def once(text, old, new, count=1):
    n = text.count(old)
    if n != count:
        sys.exit("no encuentro lo esperado (%d coincidencias, esperaba %d) para: %r" % (n, count, old[:70]))
    return text.replace(old, new)

s = once(s, ".product-hero-actions{margin-top:30px;margin-bottom:14px}\n", CSS)
s = once(s, 'class="button download-option-direct" href=', 'class="button download-option-direct" data-apk href=', 2)
# hero: nota justo después del bloque de botones, dentro de .product-copy
s = once(s, '      </div>\n    </div>\n    <div class="product-art product-art-real-phone">',
            '      </div>\n' + NOTE + '    </div>\n    <div class="product-art product-art-real-phone">')
# diálogo de descarga
s = once(s, '    </div>\n  </div>\n</dialog>', '    </div>\n' + NOTE.replace("      <p", "    <p").replace("\n        ", "\n      ").replace("\n      </p>", "\n    </p>") + '  </div>\n</dialog>')
s = once(s, '})();\n</script>', JS + '})();\n</script>')

shutil.copy(path, path + ".bak")
open(path, "w", encoding="utf-8").write(s)
print("hecho. Copia de seguridad:", path + ".bak")
