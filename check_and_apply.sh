#!/usr/bin/env bash
# Comprueba qué parches de arm32 ya están aplicados y aplica los que faltan.
# Ejecutar en la raíz de KyaniteAndroid, con (como mucho) estos archivos en esa carpeta:
#   arm32.patch  apk-names.patch  patch_index.py
# Es seguro repetirlo: lo que ya está aplicado no se toca.
set -u

Y=.github/workflows/android.yml
A=.github/actions/prepare-assets/action.yml
K=app/src/main/java/io/github/stringmanolo/KyaniteAndroid

die(){ printf '\nERROR: %s\n' "$1" >&2; exit 1; }
[ -d .git ] && [ -f app/build.gradle ] || die "ejecútalo en la raíz del repo KyaniteAndroid"

# --- comprobaciones (cada una mira el contenido real de los archivos) ---------
c_gradle()  { grep -q targetAbi app/build.gradle; }
c_paths()   { grep -q 'object Abi' $K/Paths.kt; }
c_termux()  { grep -q TERMUX_ARCH bash/termux_fetch.py; }
c_rootfs()  { grep -q KYANITE_ARCH bash/fetch-rootfs.sh; }
c_action()  { grep -q 'inputs.arch' $A; }
c_matrix()  { grep -q 'arch: armv7' $Y && grep -q -- '-PtargetAbi' $Y; }
c_names()   { grep -q 'release_apk: Kyanite.apk' $Y && grep -q 'release_apk: kyanite_v7.apk' $Y; }
c_updater() { grep -q 'contains("v7", true)' $K/Updater.kt; }
c_index()   { [ -f index.html ] && grep -q data-apk-note index.html; }

line() { # line "descripción" función
  if "$2"; then printf '  [OK]    %s\n' "$1"; else printf '  [FALTA] %s\n' "$1"; fi
}
status() {
  echo "arm32.patch (6 piezas):"
  line "build.gradle: -PtargetAbi"              c_gradle
  line "Paths.kt: objeto Abi"                   c_paths
  line "termux_fetch.py: TERMUX_ARCH"           c_termux
  line "fetch-rootfs.sh: KYANITE_ARCH"          c_rootfs
  line "prepare-assets/action.yml: input arch"  c_action
  line "android.yml: matriz con armv7"          c_matrix
  echo "apk-names.patch:"
  line "android.yml: nombres Kyanite.apk / kyanite_v7.apk" c_names
  line "Updater.kt: elige APK por 'v7'"         c_updater
  echo "Web:"
  line "index.html: detección de 32 bits"       c_index
}

echo "===== ESTADO ACTUAL ====="
status

# --- 1) arm32.patch --------------------------------------------------------------
n=0
for f in c_gradle c_paths c_termux c_rootfs c_action c_matrix; do "$f" && n=$((n+1)); done
echo
echo "===== APLICANDO LO QUE FALTA ====="
if [ "$n" = 0 ]; then
  [ -f arm32.patch ] || die "arm32.patch no está aplicado y no lo encuentro en esta carpeta"
  git apply --check arm32.patch || die "arm32.patch no aplica limpio"
  git apply arm32.patch && echo "  [HECHO] arm32.patch"
elif [ "$n" != 6 ]; then
  die "arm32.patch está a medias ($n de 6 piezas). No toco nada: pégame esta salida."
else
  echo "  [OK]    arm32.patch ya estaba aplicado"
fi

# --- 2) nombres de APK en android.yml (sin parche: se normaliza el valor) ---------
python3 - <<'PY'
import re
p = '.github/workflows/android.yml'
s = open(p, encoding='utf-8').read(); o = s
s = re.sub(r'release_apk: (app-release\.apk|KyaniteAndroid-release-arm64-v8a\.apk)', 'release_apk: Kyanite.apk', s)
s = s.replace('release_apk: KyaniteAndroid-armeabi-v7a.apk', 'release_apk: kyanite_v7.apk')
if s != o:
    open(p, 'w', encoding='utf-8').write(s)
    print('  [HECHO] android.yml: nombres de APK -> Kyanite.apk / kyanite_v7.apk')
else:
    print('  [OK]    android.yml: nombres de APK sin cambios')
PY

# --- 3) Updater.kt (solo esa parte de apk-names.patch) ------------------------------
if c_updater; then
  echo "  [OK]    Updater.kt ya estaba actualizado"
else
  [ -f apk-names.patch ] || die "falta apk-names.patch en esta carpeta"
  git apply --include='*Updater.kt' --check apk-names.patch || die "Updater.kt no coincide con lo esperado"
  git apply --include='*Updater.kt' apk-names.patch && echo "  [HECHO] Updater.kt"
fi

# --- 4) index.html ---------------------------------------------------------------------
if c_index; then
  echo "  [OK]    index.html ya tenía la detección"
else
  [ -f index.html ]     || die "no hay index.html en esta carpeta"
  [ -f patch_index.py ] || die "falta patch_index.py en esta carpeta"
  python3 patch_index.py index.html || die "patch_index.py falló (index.html no se ha tocado)"
fi

echo
echo "===== ESTADO FINAL ====="
status
echo
if c_gradle && c_paths && c_termux && c_rootfs && c_action && c_matrix && c_names && c_updater && c_index; then
  echo "TODO OK. El android.yml descargado ya no hace falta: el tuyo ya es equivalente."
  echo
  echo "Para subirlo (sin incluir los .patch ni patch_index.py, que no están trackeados):"
  echo "  git add -u && git commit -m 'arm32 build, APK names and 32-bit detection' && git push"
else
  echo "Queda algo en [FALTA]: pégame esta salida completa."
fi
