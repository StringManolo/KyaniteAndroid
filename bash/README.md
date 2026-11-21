# Bash

Scripts to help you manage your app.

### utils-compile-apk
Push the repo to github to trigger the Github Actions workflow to compile the apk

### utils-generate-keystore
Generate the keys and files needed for github secrets.

### termux_fetch.py (CI)
Downloads binaries from the Termux apt repo (proot, QEMU) and repackages them as `jniLibs`.

### build_vm_assets.py + vm/init (CI)
Builds the VM kernel (`assets/vm/Image`, from Alpine's `linux-virt`; `VM_KERNEL=debian` for Debian's) and the tiny
initramfs (`assets/vm/initramfs.bin`: busybox, the virtio modules in dependency order, `vm/init`).

### fetch-rootfs.sh + kyanite-release.pub (CI)
Downloads the Kyanite aarch64 rootfs release into `assets/rootfs/`, verifying its SHA-256 and its Ed25519 signature
(public key pinned in `kyanite-release.pub`). `KYANITE_TAG` selects the release (default `latest`).
