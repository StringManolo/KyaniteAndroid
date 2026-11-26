# KyaniteAndroid

A Termux alternative for advanced users: [**Kyanite**](https://github.com/StringManolo/Kyanite) (a small, memory-safe
Rust rootfs with `kpkg` and Brush) on Android, built from the
[KotlinApkTemplate](https://github.com/StringManolo/KotlinApkTemplate) and compiled entirely by GitHub Actions.
Fork of [DebianLiveCD4Android](https://github.com/StringManolo/DebianLiveCD4Android).

🌐 **[Official website](https://stringmanolo.github.io/KyaniteAndroid/)** · User-friendly introduction, screenshots, features and download guide.

📱 **[Download Kyanite for Android](https://github.com/StringManolo/KyaniteAndroid/releases/latest/download/Kyanite.apk)**

- Kyanite runs under **proot** (the `termux/proot` fork), not inside a Termux-style prefix.
- The Kyanite rootfs is the signed `kyanite-rootfs-aarch64.tar.xz` from the Kyanite releases, shipped inside the APK
  (about 8 MB). The CI verifies its SHA-256 and its Ed25519 signature before packaging it (see Build).
- Software installed afterwards comes from `kpkg` / `apt` inside Kyanite; the app itself does not care what is in the rootfs.
- Terminal emulation reuses Termux's `terminal-emulator` / `terminal-view`, with an extra-keys bar (ESC, TAB, CTRL, ALT, HOME, END, PGUP, PGDN, arrows; tap a modifier = one-shot, long-press = lock).
- `targetSdk 28` on purpose: newer targets cannot exec binaries from the app's data directory (W^X).
## First run, environments and modes (⚙ button, always available)

Nothing is installed or started until you choose. The first launch opens the settings screen.

|            | **Normal**                            | **Ephemeral**                                  | **VM**                                           |
|------------|---------------------------------------|------------------------------------------------|--------------------------------------------------|
| **System** | proot on your installed Kyanite       | proot on a temp copy of it, wiped on exit      | QEMU, installed tree streamed into guest RAM     |
| **LiveCD** | proot on a persistent extraction      | fresh extraction every start, wiped on exit    | QEMU, shipped image streamed into guest RAM      |

**Modes never interfere with each other's storage**

- Each **system** lives in `files/systems/<id>/` and is written only by System + Normal while it is the selected one.
  Systems are created, imported or downloaded explicitly in Settings > Systems; nothing is installed automatically.
- `LiveCD persistence` (`files/systems/livecd/`) is written only by LiveCD + Normal.
- Ephemeral uses `files/eph/*` and wipes it on exit (and on the next launch if the app was killed).
- VM writes nothing to disk. System + Ephemeral/VM only *read* the installed System and refuse to run if it is
  not installed (they never install it).
- The one explicit cross-access: a LiveCD session in a proot mode may bind the installed System at `/mnt/system`
  (read-write, opt-in in the settings), like a live CD mounting the hard disk to repair or back it up.
  Not available in VM mode.

**Ephemeral is disk, not RAM**: flash storage (F2FS, wear levelling) may keep remnants. **VM** is the only mode
with no disk traces: `qemu-system-aarch64` in TCG mode (no KVM for apps) boots a tiny initramfs that receives the
rootfs over a virtio-console port into a tmpfs. Much slower than proot; pick RAM and cores in the settings.
VM mode is optional at build time (`with-vm` in the workflow); the settings screen says what is missing if it is
unavailable and shows a diagnostics block.

## Window and appearance

- **Fullscreen** or **Floating window** (needs "Display over other apps"). The floating window can be dragged
  anywhere (even partly off-screen), resized freely (◢ corner), rotated (↻: 90°, long-press 15°), pinned (PIN locks
  position/size/rotation and is remembered), made transparent (◐ slider) and minimized (—): while minimized the
  window is gone and the notification offers *Restore*, *Settings* and *Exit*. Tap the terminal to give the window
  the keyboard; tap outside to release it. Non-right-angle rotations leave transparent corners that still capture
  touches (Android limitation).
- **Appearance** (applies instantly, no restart): colour scheme (Dark, Solarized, Dracula, Nord, Gruvbox, Matrix,
  Light), font size and bold. Pinch-to-zoom also changes the font size.

## Settings (tabs)

- **Environment**: system / LiveCD, mode (VM is **experimental**), VM RAM and cores, window mode, wake lock (off by default), opt-in access to
  shared storage (`/sdcard`, `~/storage/shared`; needs the Android permission, like `termux-setup-storage`, but on demand).
- **Systems**: several systems at once; create from the shipped Kyanite, import (tar, tar.gz, tar.xz, `.kya`),
  download (Kyanite latest release, Alpine, Ubuntu Base and Arch Linux ARM catalog with checksum verification where upstream publishes one, or any
  URL + optional SHA-256), rename, duplicate, delete (optionally with random overwrite), export (tar.gz / tar.xz / `.kya`),
  snapshots and restore.
- **Appearance**: 28 colour schemes (including Vim-inspired ones) plus a fully custom palette, font size and bold.
- **Security**
  - PIN lock (+ re-lock timeout, + duress PIN, + wrong-PIN lockout).
  - Compression and AES-256-GCM encryption *at rest*: a system that is not in use is stored as an archive and unpacked
    only while a session runs. The key is generated by the app (Android Keystore) or derived from your passphrase; it can
    be re-wrapped, rotated (re-encrypts everything) or removed at any time.
  - Privacy: block screenshots / hide from Recents, hide notification content, block clipboard, clear it on exit, end the
    session when the screen turns off.
  - Scheduled wipe: after N hours without opening the app, on a date, after N wrong PINs, on the duress PIN, or when USB
    debugging is enabled. It destroys the key first (crypto-shredding), overwrites files with CSPRNG data, deletes them and
    can fill the free space with random files (anti-forensics). Conditions are polled about every 30 min.
- **Network**: master switch. Off = a local VPN with no exit drops all traffic of the app (and of every process inside
  it), the VM gets no NIC, and the app does not download or open the browser.
- **Updates**: none / manual (opens the releases page) / automatic (default every 8 h: check, download, offer install).

VM notes: the guest boots an Alpine `linux-virt` arm64 kernel (Kyanite has no kernel of its own yet) under QEMU TCG
(software emulation, no KVM), so expect roughly 10-40 s to the prompt on a phone even for a tiny rootfs like Kyanite; the rootfs transfer itself takes seconds. If the console stops
at a `[kya]` message for minutes, something is wrong and the rescue shell / last message tells which step. Typing `exit`
in the guest shell (PID 1) powers the VM off, which ends the session.

Robustness: the app never closes by itself. If a session ends (you type `exit`, a VM powers off, a start fails) it stays
open with Restart / Settings buttons, and after a failed or very short session it does not relaunch automatically (no
crash loops). Systems are re-packed (compressed / encrypted) before the service stops, and the plain tree is invalidated
before it is deleted, so an interrupted exit can never leave a half-deleted "valid" system; a leftover tree is re-packed
on the next start.

Limits worth knowing: proot is not a security boundary (use VM mode for isolation); overwriting on flash storage is best
effort (crypto-shredding is the strong guarantee); Android never allows silent installs, so an update always needs your
confirmation and must be signed with the same key.

## Build

Push to GitHub. `.github/actions/prepare-assets`:

1. downloads proot (and QEMU) from the Termux apt repo (sha256-verified);
2. builds the VM kernel/initramfs (`bash/build_vm_assets.py`) from Alpine's `linux-virt` and `busybox-static`
   (`VM_KERNEL=debian` switches to Debian's kernel, `ALPINE_BRANCH` pins an Alpine branch);
3. fetches the Kyanite rootfs (`bash/fetch-rootfs.sh`): downloads the release, checks its SHA-256, verifies the
   Ed25519 signature against the key pinned in `bash/kyanite-release.pub`, and re-compresses it with `xz -6` so the
   app can unpack it with a small heap. Use the `kyanite-tag` input of the action (or `KYANITE_TAG`) to pin a release
   such as `v0.1.1`; the default is the latest one. A release without a valid signature fails the build
   (`KYANITE_ALLOW_UNSIGNED=1` overrides that).

Then Gradle builds the APK. Hashes and URLs are uploaded as the `provenance` artifact.

Android 12+ may kill child processes ("phantom process killer"); disable it if sessions die in the background.
