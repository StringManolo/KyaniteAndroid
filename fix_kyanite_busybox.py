#!/usr/bin/env python3
"""Patch bash/build_vm_assets.py to fall back to Debian busybox-static if Alpine lacks applets.

Run from the repository root:
    python3 fix_kyanite_busybox.py
Or pass the repository path:
    python3 fix_kyanite_busybox.py /path/to/KyaniteAndroid

The script is idempotent and writes a .bak backup before changing the file.
"""
from pathlib import Path
import re
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    target = root / "bash" / "build_vm_assets.py"
    if not target.is_file():
        print(f"ERROR: no existe {target}", file=sys.stderr)
        return 1

    source = target.read_text(encoding="utf-8")
    if "Debian busybox-static fallback" in source:
        print("El fallback ya está aplicado; no se han realizado cambios.")
        return 0

    old_applets = '''APPLETS = ["sh", "mount", "insmod", "find", "tar", "ip", "cat", "cp", "mkdir", "ls", "dmesg",
           "sleep", "switch_root", "cttyhack"]'''
    new_applets = '''APPLETS = ["sh", "mount", "insmod", "find", "tar", "ip", "cat", "cp", "mkdir", "ls", "dmesg",
           "sleep", "switch_root", "cttyhack", "setsid", "head", "tail"]'''

    if old_applets in source:
        source = source.replace(old_applets, new_applets, 1)
    elif '"cttyhack", "setsid", "head", "tail"' not in source:
        print("ERROR: no encuentro la definición APPLETS esperada; no modifico nada.", file=sys.stderr)
        return 1

    old_check = '''    # busybox must have every applet the init script uses
    bb = busybox.read_bytes()
    missing = [a for a in APPLETS if b"\\0" + a.encode() + b"\\0" not in bb]
    if missing:
        sys.exit(f"busybox is missing applets needed by bash/vm/init: {missing}")
'''
    new_check = '''    # busybox must have every applet the init script uses. Alpine's busybox-static
    # may be built without cttyhack; in that case use Debian's static BusyBox while
    # keeping the Alpine kernel and its modules unchanged.
    def missing_applets(binary):
        data = binary.read_bytes()
        return [a for a in APPLETS if b"\\0" + a.encode() + b"\\0" not in data]

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
'''

    if old_check not in source:
        print("ERROR: no encuentro el bloque de comprobación BusyBox esperado; no modifico el archivo.", file=sys.stderr)
        return 1

    source = source.replace(old_check, new_check, 1)

    # Compile before writing so a malformed patch cannot damage the working copy.
    try:
        compile(source, str(target), "exec")
    except SyntaxError as exc:
        print(f"ERROR: el cambio produciría un error de sintaxis: {exc}", file=sys.stderr)
        return 1

    backup = target.with_suffix(target.suffix + ".bak")
    if backup.exists():
        print(f"ERROR: ya existe {backup}; no sobrescribo una copia anterior.", file=sys.stderr)
        return 1
    backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    target.write_text(source, encoding="utf-8")
    print(f"OK: cambios aplicados a {target}")
    print(f"Backup: {backup}")
    print("El kernel seguirá siendo Alpine; solo BusyBox del initramfs podrá venir de Debian.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
