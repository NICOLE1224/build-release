#!/bin/sh
set -eu
: "${CONFIG_VERSION_NUMBER:?CONFIG_VERSION_NUMBER is required}"
: "${BUILD_DEVICE:?BUILD_DEVICE is required}"
printf '%s\n' "$CONFIG_VERSION_NUMBER" | grep -Eq '^[0-9]+[.][0-9]+_b[0-9]{12}$'
case "$BUILD_DEVICE" in
	nokia_ea0326gmp|phicomm_k2p) ;;
	*) echo "upload: unsupported device" >&2; exit 1 ;;
esac
builder_root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
python3 "$builder_root/profiles/ea0326gmp-k2p/export-images.py" \
	. "$CONFIG_VERSION_NUMBER" "$BUILD_DEVICE"
