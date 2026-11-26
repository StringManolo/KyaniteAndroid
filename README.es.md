🇺🇸 [English](README.md) | 🇪🇸 Español | 🇷🇺 [Русский](README.ru.md) | 🇨🇳 [简体中文](README.zh-CN.md)

# KyaniteAndroid

Una alternativa a Termux para usuarios avanzados: [**Kyanite**](https://github.com/StringManolo/Kyanite), un pequeño rootfs con seguridad de memoria, escrito en Rust, que incluye `kpkg` y Brush, funcionando en Android. Está construido a partir de [KotlinApkTemplate](https://github.com/StringManolo/KotlinApkTemplate) y compilado íntegramente mediante GitHub Actions. Es un fork de [DebianLiveCD4Android](https://github.com/StringManolo/DebianLiveCD4Android).

🌐 **[Sitio web oficial](https://stringmanolo.github.io/KyaniteAndroid/)** · Introducción para usuarios, capturas de pantalla, características y guía de descarga.

📱 **[Descargar Kyanite para Android](https://github.com/StringManolo/KyaniteAndroid/releases/latest/download/Kyanite.apk)**

- Kyanite funciona mediante **proot** (el fork de `termux/proot`), no dentro de un prefijo al estilo de Termux.
- El rootfs de Kyanite es el archivo firmado `kyanite-rootfs-aarch64.tar.xz` de las releases de Kyanite, incluido dentro del APK (unos 8 MB). CI verifica su SHA-256 y su firma Ed25519 antes de empaquetarlo (véase Build).
- El software instalado posteriormente procede de `kpkg` / `apt` dentro de Kyanite; la aplicación no depende del contenido del rootfs.
- La emulación de terminal reutiliza `terminal-emulator` / `terminal-view` de Termux, con una barra adicional de teclas especiales (ESC, TAB, CTRL, ALT, HOME, END, PGUP, PGDN y flechas; tocar un modificador lo activa una vez, mantenerlo pulsado lo bloquea).
- `targetSdk 28` de forma intencionada: los targets más recientes no pueden ejecutar binarios desde el directorio de datos de la aplicación (W^X).

## Primer inicio, entornos y modos (botón ⚙, siempre disponible)

No se instala ni se inicia nada hasta que lo elijas. El primer inicio abre la pantalla de ajustes.

| | **Normal** | **Efímero** | **VM** |
|---|---|---|---|
| **System** | proot sobre tu Kyanite instalado | proot sobre una copia temporal, eliminada al salir | QEMU, sistema instalado transferido a la RAM del invitado |
| **LiveCD** | proot sobre una extracción persistente | extracción nueva en cada inicio, eliminada al salir | QEMU, imagen incluida transferida a la RAM del invitado |

**Los modos nunca interfieren con el almacenamiento de los demás.**

- Cada **System** reside en `files/systems/<id>/` y solo se modifica mediante System + Normal cuando está seleccionado. Los sistemas se crean, importan o descargan explícitamente desde Ajustes > Systems; no se instala nada automáticamente.
- La persistencia de **LiveCD** (`files/systems/livecd/`) solo se modifica mediante LiveCD + Normal.
- **Efímero** utiliza `files/eph/*` y lo elimina al salir (y en el siguiente inicio si la aplicación fue terminada).
- **VM** no escribe nada en disco. System + Efímero/VM solo lee el System instalado y se niega a ejecutarse si no está instalado (nunca lo instala).
- El único acceso cruzado explícito: una sesión LiveCD en modo proot puede montar el System instalado en `/mnt/system` (lectura y escritura, opcional en ajustes), como un LiveCD que monta el disco duro para repararlo o hacer una copia de seguridad. No está disponible en modo VM.

**Efímero utiliza disco, no RAM**: el almacenamiento flash (F2FS y nivelación de desgaste) puede conservar restos de datos.

**VM es el único modo sin rastros en disco**: `qemu-system-aarch64` en modo TCG (sin KVM para las aplicaciones) arranca un pequeño initramfs que recibe el rootfs a través de un puerto virtio-console y lo carga en un tmpfs. Es mucho más lento que proot; puedes elegir la RAM y el número de núcleos en los ajustes.

El modo VM es opcional durante la compilación (`with-vm` en el workflow). Si no está disponible, la pantalla de ajustes explica qué falta y muestra un bloque de diagnóstico.

## Ventana y apariencia

- **Pantalla completa** o **ventana flotante** (requiere el permiso «Mostrar sobre otras aplicaciones»). La ventana flotante se puede arrastrar a cualquier lugar (incluso parcialmente fuera de la pantalla), redimensionar libremente (esquina ◢), rotar (↻: 90°, mantener pulsado para 15°), fijar (PIN bloquea posición, tamaño y rotación, y se recuerda), hacer transparente (control deslizante ◐) y minimizar (—). Al minimizarla, la ventana desaparece y la notificación ofrece las opciones *Restaurar*, *Ajustes* y *Salir*. Toca el terminal para mostrar el teclado; toca fuera para liberarlo. Las rotaciones que no son múltiplos de 90° dejan esquinas transparentes que siguen capturando toques (limitación de Android).
- **Apariencia** (se aplica al instante, sin reiniciar): esquema de colores (Dark, Solarized, Dracula, Nord, Gruvbox, Matrix, Light), tamaño de fuente y negrita. El gesto de pellizcar para ampliar también cambia el tamaño de fuente.

## Ajustes (pestañas)

- **Entorno**: System / LiveCD, modo (VM es **experimental**), RAM y núcleos de VM, modo de ventana, bloqueo de activación (desactivado por defecto), acceso opcional al almacenamiento compartido (`/sdcard`, `~/storage/shared`; requiere el permiso de Android, similar a `termux-setup-storage`, pero se solicita bajo demanda).
- **Systems**: varios sistemas simultáneamente; crear desde el Kyanite incluido, importar (tar, tar.gz, tar.xz, `.kya`), descargar (última release de Kyanite, catálogo de Alpine, Ubuntu Base y Arch Linux ARM con verificación de checksum cuando el proyecto original lo proporciona, o cualquier URL con SHA-256 opcional), renombrar, duplicar, eliminar (opcionalmente con sobrescritura aleatoria), exportar (tar.gz / tar.xz / `.kya`), crear snapshots y restaurarlos.
- **Apariencia**: 28 esquemas de colores (incluidos algunos inspirados en Vim), paleta completamente personalizable, tamaño de fuente y negrita.
- **Seguridad**:
  - Bloqueo mediante PIN (+ tiempo de bloqueo automático, + PIN de coacción, + bloqueo tras PIN incorrectos).
  - Compresión y cifrado AES-256-GCM **en reposo**: un sistema que no está en uso se almacena como archivo comprimido y solo se descomprime mientras hay una sesión activa. La clave se genera mediante la aplicación (Android Keystore) o se deriva de una frase de contraseña. Se puede volver a proteger con otra clave, rotar (volviendo a cifrarlo todo) o eliminar en cualquier momento.
  - Privacidad: bloquear capturas de pantalla / ocultar en Recientes, ocultar el contenido de las notificaciones, bloquear el portapapeles, borrarlo al salir y finalizar la sesión cuando se apaga la pantalla.
  - **Borrado programado**: después de N horas sin abrir la aplicación, en una fecha determinada, tras N PIN incorrectos, al introducir el PIN de coacción o cuando se activa la depuración USB. Primero destruye la clave (borrado criptográfico), sobrescribe los archivos con datos CSPRNG, los elimina y puede llenar el espacio libre con archivos aleatorios (antiforense). Las condiciones se comprueban aproximadamente cada 30 minutos.
- **Red**: interruptor general. Desactivado = una VPN local sin salida bloquea todo el tráfico de la aplicación (y de todos sus procesos internos), la VM no recibe interfaz de red y la aplicación no descarga archivos ni abre el navegador.
- **Actualizaciones**: ninguna / manual (abre la página de releases) / automática (por defecto, cada 8 horas: comprobar, descargar y ofrecer la instalación).

### Notas sobre VM

El invitado arranca un kernel Alpine `linux-virt` arm64 bajo QEMU TCG (emulación por software, sin KVM), ya que Kyanite todavía no tiene un kernel propio. En un teléfono, espera aproximadamente entre 10 y 40 segundos hasta llegar al prompt, incluso con un rootfs pequeño como Kyanite; la transferencia del rootfs solo tarda unos segundos.

Si la consola se queda durante minutos en un mensaje `[kya]`, algo ha fallado. El shell de rescate o el último mensaje indican qué paso ha causado el problema.

Escribir `exit` en el shell del invitado (PID 1) apaga la VM y finaliza la sesión.

## Robustez

La aplicación nunca se cierra por sí sola. Si una sesión termina (escribes `exit`, una VM se apaga o falla un inicio), la aplicación permanece abierta mostrando los botones Reiniciar / Ajustes. Después de una sesión fallida o demasiado corta, no vuelve a iniciarse automáticamente (sin bucles de fallos).

Los sistemas se vuelven a empaquetar (comprimidos / cifrados) antes de detener el servicio, y el árbol de archivos sin procesar se invalida antes de eliminarlo. Así, una salida interrumpida nunca puede dejar un sistema parcialmente eliminado que siga considerándose válido. Si queda un árbol residual, se vuelve a empaquetar en el siguiente inicio.

## Limitaciones importantes

- proot no es una frontera de seguridad (utiliza el modo VM si necesitas aislamiento).
- La sobrescritura en almacenamiento flash es un intento de mejor esfuerzo; el borrado criptográfico es la garantía sólida.
- Android nunca permite instalaciones silenciosas: cualquier actualización requiere tu confirmación y debe estar firmada con la misma clave.

## Build

Haz push a GitHub. `.github/actions/prepare-assets`:

1. Descarga proot (y QEMU) desde el repositorio apt de Termux (verificando SHA-256).
2. Construye el kernel y el initramfs de VM (`bash/build_vm_assets.py`) a partir de `linux-virt` de Alpine y `busybox-static` (`VM_KERNEL=debian` cambia al kernel de Debian; `ALPINE_BRANCH` fija una rama de Alpine).
3. Obtiene el rootfs de Kyanite (`bash/fetch-rootfs.sh`): descarga la release, comprueba su SHA-256, verifica la firma Ed25519 con la clave fijada en `bash/kyanite-release.pub` y vuelve a comprimirlo con `xz -6` para que la aplicación pueda descomprimirlo utilizando un heap pequeño. Utiliza la entrada `kyanite-tag` de la acción (o `KYANITE_TAG`) para fijar una release, por ejemplo `v0.1.1`; por defecto se utiliza la última. Una release sin firma válida hace fallar la compilación (`KYANITE_ALLOW_UNSIGNED=1` permite omitir esta comprobación).

Después, Gradle construye el APK. Los hashes y las URL se suben como artefacto `provenance`.

Android 12 y versiones posteriores pueden terminar procesos secundarios («phantom process killer»); desactívalo si las sesiones se interrumpen en segundo plano.
