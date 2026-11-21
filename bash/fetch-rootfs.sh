#!/usr/bin/env bash
# Builds assets/rootfs/kyanite-aarch64.tar.xz from a RELEASE of Kyanite (https://github.com/StringManolo/Kyanite).
#
#   KYANITE_REPO   owner/repo of the release            (default StringManolo/Kyanite)
#   KYANITE_TAG    "latest" or a tag such as v0.1.1     (default latest; pin a tag for reproducible builds)
#   KYANITE_ALLOW_UNSIGNED=1   accept a release without a valid signature (default: refuse)
#
# Steps: download tar.xz + .sha256 + .sha256.sig, check the SHA-256, verify the Ed25519 signature of the .sha256
# against the key(s) in bash/kyanite-release.pub, sanity-check the tree, then re-compress with xz -6.
# Re-compressing matters: Kyanite releases use xz -9 (64 MiB dictionary); the app unpacks the asset in the JVM
# and a 8 MiB dictionary (-6) keeps that comfortably inside the heap. The tar content is not touched.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

REPO="${KYANITE_REPO:-StringManolo/Kyanite}"
TAG="${KYANITE_TAG:-latest}"
ARCH="aarch64"
NAME="kyanite-rootfs-${ARCH}.tar.xz"
DEST="$ROOT/app/src/main/assets/rootfs"
FILE="$DEST/kyanite-${ARCH}.tar.xz"
mkdir -p "$DEST" "$ROOT/build-info"

PUBKEYS="${KYANITE_PUBKEY_FILE:-$ROOT/bash/kyanite-release.pub}"   # override: tests only
if [ -n "${KYANITE_BASE_URL:-}" ]; then
  BASE="$KYANITE_BASE_URL"                                            # override: tests only (file:// works)
elif [ "$TAG" = "latest" ]; then
  BASE="https://github.com/${REPO}/releases/latest/download"
else
  BASE="https://github.com/${REPO}/releases/download/${TAG}"
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cd "$work"

dl() { curl -fsSL --retry 3 --retry-delay 2 -o "$1" "$BASE/$1"; }
dl "$NAME"
dl "$NAME.sha256"

echo "== SHA-256"
sha256sum -c "$NAME.sha256"

echo "== signature"
SIG_STATE="not verified"
if dl "$NAME.sha256.sig" 2>/dev/null; then
  ok=0
  while read -r hex _; do
    case "$hex" in ''|'#'*) continue ;; esac
    [[ "$hex" =~ ^[0-9a-fA-F]{64}$ ]] || { echo "ignoring malformed key line in bash/kyanite-release.pub"; continue; }
    python3 -c 'import sys,binascii; sys.stdout.buffer.write(binascii.unhexlify("302a300506032b6570032100"+sys.argv[1]))' "$hex" > pub.der
    if openssl pkeyutl -verify -pubin -inkey pub.der -keyform DER -rawin \
         -in "$NAME.sha256" -sigfile "$NAME.sha256.sig" >/dev/null 2>&1; then
      ok=1; break
    fi
  done < "$PUBKEYS"
  if [ "$ok" = 1 ]; then
    SIG_STATE="OK (Ed25519, key ${hex:0:16}…)"
  elif [ "${KYANITE_ALLOW_UNSIGNED:-0}" = 1 ]; then
    SIG_STATE="INVALID, accepted because KYANITE_ALLOW_UNSIGNED=1"
  else
    echo "signature of $NAME.sha256 does not verify against bash/kyanite-release.pub" >&2
    exit 1
  fi
elif [ "${KYANITE_ALLOW_UNSIGNED:-0}" = 1 ]; then
  SIG_STATE="missing, accepted because KYANITE_ALLOW_UNSIGNED=1"
else
  echo "release has no $NAME.sha256.sig (set KYANITE_ALLOW_UNSIGNED=1 to accept it anyway)" >&2
  exit 1
fi
echo "signature: $SIG_STATE"

echo "== sanity check"
# list to a file first: `tar | grep -q` dies with SIGPIPE under pipefail even when the match exists
tar -tJf "$NAME" > rootfs.list
for need in 'sbin/init' 'bin/sh' 'usr/bin/env' 'bin/brush' 'usr/bin/kpkg'; do
  grep -qE "(^|/)${need}\$" rootfs.list || { echo "rootfs looks wrong (no $need)"; head -20 rootfs.list; exit 1; }
done
echo "rootfs entries: $(wc -l < rootfs.list)"

echo "== re-compress (xz -6, 8 MiB dictionary)"
xz -dc "$NAME" | xz -T0 -6 > "$FILE"

{
  echo "release: ${REPO} @ ${TAG}"
  echo "signature: $SIG_STATE"
  echo "upstream: $(cat "$NAME.sha256")"
  sha256sum "$FILE"
} > "$ROOT/build-info/rootfs-provenance.txt"
cat "$ROOT/build-info/rootfs-provenance.txt"
ls -lh "$FILE"
