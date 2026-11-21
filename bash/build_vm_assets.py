#!/usr/bin/env python3
"""Build the VM boot assets: a Linux arm64 kernel and a tiny initramfs.

Outputs (packaged as APK assets):
  app/src/main/assets/vm/Image         kernel
  app/src/main/assets/vm/initramfs.bin busybox + virtio modules + bash/vm/init

The kernel comes from Alpine Linux's `linux-virt` package by default (a kernel built for virtual machines, much
smaller than a general purpose one). Kyanite itself has no kernel yet, and the Kyanite userland is static musl +
glibc, so it does not care which kernel runs it. Set VM_KERNEL=debian to build from Debian's linux-image-arm64
instead (fallback if the Alpine kernel misbehaves under QEMU).

  VM_KERNEL        alpine (default) | debian
  ALPINE_BRANCH    latest-stable (default) | v3.xx | edge
  ALPINE_MIRROR    https://dl-cdn.alpinelinux.org/alpine
  DEBIAN_SUITE     trixie (only for VM_KERNEL=debian)

The initramfs does NOT contain the rootfs: the app streams it into the guest at boot (see VmFeeder.kt), so the same
VM image serves both the shipped LiveCD and the installed System.

Authenticity of the downloads rests on HTTPS to the distribution mirror; the sha256 of everything fetched is
written to build-info/vm-provenance.txt.
"""
import glob, gzip, hashlib, io, lzma, os, re, shutil, subprocess, sys, tarfile, tempfile, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "app/src/main/assets/vm"
INFO = ROOT / "build-info"
PROVIDER = os.environ.get("VM_KERNEL", "alpine").lower()

ALPINE_MIRROR = os.environ.get("ALPINE_MIRROR", "https://dl-cdn.alpinelinux.org/alpine").rstrip("/")
ALPINE_BRANCH = os.environ.get("ALPINE_BRANCH", "latest-stable")
DEBIAN_MIRROR = "https://deb.debian.org/debian"
DEBIAN_SUITE = os.environ.get("DEBIAN_SUITE", "trixie")

# Modules the init script needs, in no particular order: their dependencies are added and sorted below.
# Anything the kernel has built in simply is not found and is skipped.
MODULES = ["failover", "net_failover", "virtio_mmio", "virtio_console", "virtio_net"]
# Applets bash/vm/init relies on; checked in the busybox binary so a missing one fails the build, not the boot.
APPLETS = ["sh", "mount", "insmod", "find", "tar", "ip", "cat", "cp", "mkdir", "ls", "dmesg",
           "sleep", "switch_root", "cttyhack", "setsid", "head", "tail"]


def fetch(url):
    with urllib.request.urlopen(url, timeout=600) as r:
        return r.read()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------------------------- Alpine

def alpine_index():
    base = f"{ALPINE_MIRROR}/{ALPINE_BRANCH}/main/aarch64"
    blob = fetch(f"{base}/APKINDEX.tar.gz")
    # tarfile reads the concatenated gzip streams (signature segment + index segment) as one stream
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        member = next((m for m in tf if m.name == "APKINDEX"), None)
        if member is None:
            sys.exit("APKINDEX.tar.gz has no APKINDEX member (did Alpine change the index format?)")
        raw = tf.extractfile(member).read().decode()
    pk = {}
    for block in raw.split("\n\n"):
        f = {}
        for line in block.splitlines():
            if len(line) > 2 and line[1] == ":":
                f[line[0]] = line[2:]
        if "P" in f and "V" in f:
            pk[f["P"]] = f
    return base, pk


def get_apk(base, pk, name, dest):
    f = pk.get(name)
    if f is None:
        sys.exit(f"Alpine package {name} not found in {ALPINE_BRANCH}/main/aarch64")
    fname = f"{name}-{f['V']}.apk"
    data = fetch(f"{base}/{fname}")
    apk = dest.parent / fname
    apk.write_bytes(data)
    dest.mkdir(parents=True, exist_ok=True)
    # v2 .apk = gzip streams of tar segments; GNU tar reads them as one archive. It warns about the APK-TOOLS.*
    # pax keywords, which is harmless, so the exit status is not trusted: callers check for the files they need.
    subprocess.run(["tar", "-xzf", str(apk), "-C", str(dest)], stderr=subprocess.DEVNULL)
    return f"{name} {f['V']} sha256={sha256(data)} {base}/{fname}"


def provider_alpine(work):
    base, pk = alpine_index()
    kx, bx = work / "kernel", work / "busybox"
    prov = [get_apk(base, pk, "linux-virt", kx), get_apk(base, pk, "busybox-static", bx)]
    vmlinuz = next(iter(sorted((kx / "boot").glob("vmlinuz-*"))), None)
    if vmlinuz is None:
        sys.exit("linux-virt did not unpack a boot/vmlinuz-* (did Alpine change the package layout?)")
    busybox = bx / "bin/busybox.static"
    if not busybox.is_file():
        sys.exit("busybox-static did not unpack bin/busybox.static")
    cfg = next(iter(sorted((kx / "boot").glob("config-*"))), None)
    return kx, vmlinuz, cfg, busybox, prov


# --------------------------------------------------------------------------------------------- Debian (fallback)

def debian_index():
    raw = lzma.decompress(fetch(f"{DEBIAN_MIRROR}/dists/{DEBIAN_SUITE}/main/binary-arm64/Packages.xz")).decode()
    pk = {}
    for block in raw.split("\n\n"):
        f = {}
        for line in block.splitlines():
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                f[k.strip()] = v.strip()
        if "Package" in f:
            pk[f["Package"]] = f
    return pk


def get_deb(pk, name, work, x):
    f = pk[name]
    data = fetch(f"{DEBIAN_MIRROR}/{f['Filename']}")
    got = sha256(data)
    if got != f["SHA256"]:
        sys.exit(f"sha256 mismatch for {name}")
    deb = work / f"{name}.deb"
    deb.write_bytes(data)
    subprocess.check_call(["dpkg-deb", "-x", str(deb), str(x)])
    return f"{name} {f['Version']} sha256={got} {DEBIAN_MIRROR}/{f['Filename']}"


def pick_kernel_pkg(depends):
    """First dependency like linux-image-6.12.48+deb13-arm64 (not -unsigned/-dbg/-rt/-cloud variants)."""
    for dep in re.split(r"[,|]", depends):
        name = re.split(r"[ (|]", dep.strip())[0]
        if name.startswith("linux-image-") and name.endswith("-arm64") and re.match(r"linux-image-\d", name):
            return name
    sys.exit(f"no linux-image-<version>-arm64 in Depends: {depends}")


def provider_debian(work):
    pk = debian_index()
    kx, bx = work / "kernel", work / "busybox"
    kx.mkdir(); bx.mkdir()
    kname = pick_kernel_pkg(pk["linux-image-arm64"]["Depends"])
    print("kernel package:", kname)
    prov = [get_deb(pk, kname, work, kx), get_deb(pk, "busybox-static", work, bx)]
    vmlinuz = next(iter(sorted((kx / "boot").glob("vmlinuz-*"))))
    busybox = next(p for p in bx.rglob("busybox") if p.is_file() and p.parent.name == "bin")
    cfg = next(iter(sorted((kx / "boot").glob("config-*"))), None)
    return kx, vmlinuz, cfg, busybox, prov


# --------------------------------------------------------------------------------------------- shared

def raw_arm64_image(blob):
    """Return a plain arm64 Image. Handles gzip and EFI zboot (compressed payload) wrappers."""
    if blob[:2] == b"\x1f\x8b":
        blob = gzip.decompress(blob)
    if blob[:2] == b"MZ" and blob[4:8] == b"zimg":  # EFI zboot
        off = int.from_bytes(blob[8:12], "little")
        size = int.from_bytes(blob[12:16], "little")
        kind = blob[24:56].split(b"\0")[0].decode()
        payload = blob[off:off + size]
        print("EFI zboot kernel, payload compression:", kind)
        if kind.startswith("gzip"):
            blob = gzip.decompress(payload)
        elif kind.startswith(("xz", "lzma")):
            blob = lzma.decompress(payload)
        elif kind.startswith("zstd"):
            blob = subprocess.run(["zstd", "-d", "-q", "-c"], input=payload, check=True,
                                  stdout=subprocess.PIPE).stdout
        else:
            sys.exit(f"unsupported zboot compression: {kind}")
    return blob


def read_module(path):
    data = path.read_bytes()
    if path.name.endswith(".gz"):
        return gzip.decompress(data)
    if path.name.endswith(".xz"):
        return lzma.decompress(data)
    if path.name.endswith(".zst"):
        return subprocess.run(["zstd", "-d", "-q", "-c"], input=data, check=True, stdout=subprocess.PIPE).stdout
    return data


def mod_name(path):
    return re.sub(r"\.ko(\.(gz|xz|zst))?$", "", path.name).replace("-", "_")


def find_modules(kx):
    """{module name: path} for every .ko[.gz|.xz|.zst] under the unpacked kernel package."""
    mods = {}
    for p in kx.rglob("*.ko*"):
        if p.is_file() and re.search(r"\.ko(\.(gz|xz|zst))?$", p.name):
            mods[mod_name(p)] = p
    return mods


def module_deps(kx, mods):
    """{module name: set of (transitive) dependency names}, from modules.dep (running depmod if the package lacks it)."""
    dep = next(iter(kx.rglob("modules.dep")), None)
    if dep is None:
        any_ko = next(iter(mods.values()), None)
        kdir = any_ko and next((a for a in any_ko.parents if a.parent.name == "modules"), None)
        if kdir is not None:
            base = kdir.parent.parent.parent          # <base>/lib/modules/<ver>
            if base.name == "usr":                    # merged-/usr layout: depmod wants <base>/lib/modules
                if not (base.parent / "lib").exists():
                    os.symlink("usr/lib", base.parent / "lib")
                base = base.parent
            r = subprocess.run(["depmod", "-b", str(base), kdir.name], capture_output=True)
            print("depmod:", "ok" if r.returncode == 0 else f"failed ({r.stderr.decode().strip()[:200]})")
            dep = next(iter(kx.rglob("modules.dep")), None)
    deps = {}
    if dep is None:
        print("no modules.dep: dependencies unknown, modules are loaded in the listed order")
        return deps
    for line in dep.read_text().splitlines():
        if ":" not in line:
            continue
        left, right = line.split(":", 1)
        name = mod_name(Path(left))
        deps[name] = {mod_name(Path(r)) for r in right.split()}
    return deps


def main():
    if PROVIDER not in ("alpine", "debian"):
        sys.exit(f"VM_KERNEL must be alpine or debian, not {PROVIDER!r}")
    work = Path(tempfile.mkdtemp())
    print("kernel provider:", PROVIDER)
    kx, vmlinuz, cfg, busybox, prov = (provider_alpine if PROVIDER == "alpine" else provider_debian)(work)

    # kernel
    blob = raw_arm64_image(vmlinuz.read_bytes())
    ok = blob[56:60] == b"ARM\x64"
    print("kernel:", vmlinuz.name, "size:", len(blob), "arm64 Image magic ok:", ok)
    if not ok:
        sys.exit("kernel is not a raw arm64 Image; QEMU direct boot would fail")
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "Image").write_bytes(blob)

    # kernel config sanity: the init script needs these (module or built-in)
    if cfg:
        text = cfg.read_text()
        for sym in ("VIRTIO", "VIRTIO_MMIO", "VIRTIO_CONSOLE", "VIRTIO_NET", "FAILOVER", "NET_FAILOVER",
                    "DEVTMPFS", "TMPFS", "SERIAL_AMBA_PL011_CONSOLE", "MAGIC_SYSRQ", "BLK_DEV_INITRD", "MODULES"):
            m = re.search(rf"^CONFIG_{sym}=(\w+)", text, re.M)
            print(f"  CONFIG_{sym} = {m.group(1) if m else 'not set'}")
        for sym in ("VIRTIO_CONSOLE", "SERIAL_AMBA_PL011_CONSOLE", "BLK_DEV_INITRD"):
            if not re.search(rf"^CONFIG_{sym}=(\w+)", text, re.M):
                sys.exit(f"kernel lacks CONFIG_{sym}: the VM cannot work with this kernel")
    else:
        print("WARNING: no kernel config in the package, skipping the config sanity check")

    # busybox must have every applet the init script uses. Alpine's busybox-static
    # may be built without cttyhack; in that case use Debian's static BusyBox while
    # keeping the Alpine kernel and its modules unchanged.
    def missing_applets(binary):
        data = binary.read_bytes()
        return [a for a in APPLETS if b"\0" + a.encode() + b"\0" not in data]

    missing = missing_applets(busybox)
    if missing and PROVIDER == "alpine":
        print("Alpine BusyBox lacks required applets:", missing)
        print("Trying Debian busybox-static as an initramfs-only fallback...")
        debian_pkgs = debian_index()
        debian_bx = work / "busybox-debian"
        debian_bx.mkdir(parents=True, exist_ok=True)
        debian_provenance = get_deb(debian_pkgs, "busybox-static", work, debian_bx)
        candidates = sorted(
            p for p in debian_bx.rglob("busybox")
            if p.is_file() and p.parent.name == "bin"
        )
        if not candidates:
            sys.exit("Debian busybox-static did not contain a bin/busybox executable")

        # Only accept the fallback if it passes exactly the same applet check.
        fallback = candidates[0]
        fallback_missing = missing_applets(fallback)
        if fallback_missing:
            sys.exit(
                "Debian busybox-static also lacks required applets: "
                f"{fallback_missing} (Alpine was missing: {missing})"
            )
        busybox = fallback
        prov.append(debian_provenance)
        missing = []
        print("Using Debian busybox-static:", busybox)

    if missing:
        sys.exit(f"busybox is missing applets needed by bash/vm/init: {missing}")

    # initramfs tree
    ir = work / "ir"
    for d in ("bin", "dev", "proc", "sys", "lib/modules", "newroot", "etc"):
        (ir / d).mkdir(parents=True, exist_ok=True)
    shutil.copy2(busybox, ir / "bin/busybox")
    shutil.copy2(ROOT / "bash/vm/init", ir / "init")
    os.chmod(ir / "init", 0o755)
    os.chmod(ir / "bin/busybox", 0o755)

    # modules: the wanted ones plus their dependencies, written as plain .ko and listed in load order
    mods = find_modules(kx)
    deps = module_deps(kx, mods)
    wanted, todo = set(), [m for m in MODULES if m in mods]
    while todo:
        m = todo.pop()
        if m in wanted:
            continue
        wanted.add(m)
        todo += [d for d in deps.get(m, ()) if d in mods]
    # a module's transitive dependency set is strictly smaller than that of anything depending on it,
    # so sorting by its size gives a valid load order
    order = sorted(wanted, key=lambda m: (len(deps.get(m, ())), MODULES.index(m) if m in MODULES else 99, m))
    for m in order:
        (ir / "lib/modules" / f"{m}.ko").write_bytes(read_module(mods[m]))
    (ir / "lib/modules/load.list").write_text("".join(f"{m}\n" for m in order))
    print("modules included (load order):", order, "| not found (assumed built into the kernel):",
          [m for m in MODULES if m not in mods])

    subprocess.check_call(["sudo", "mknod", "-m", "600", str(ir / "dev/console"), "c", "5", "1"])
    subprocess.check_call(["sudo", "mknod", "-m", "666", str(ir / "dev/null"), "c", "1", "3"])
    cpio = subprocess.run(
        ["sudo", "sh", "-c", f"cd '{ir}' && find . | cpio -o -H newc -R 0:0 --quiet | gzip -9"],
        check=True, stdout=subprocess.PIPE).stdout
    (ASSETS / "initramfs.bin").write_bytes(cpio)

    INFO.mkdir(exist_ok=True)
    with open(INFO / "vm-provenance.txt", "w") as fh:
        fh.write(f"# VM boot assets ({PROVIDER} packages, GPL)\n" + "\n".join(prov) + f"\nmodules: {order}\n")
    subprocess.check_call(["ls", "-lh", str(ASSETS)])


if __name__ == "__main__":
    main()
