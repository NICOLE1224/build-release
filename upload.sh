#!/bin/sh
set -eu
: "${CONFIG_VERSION_NUMBER:?CONFIG_VERSION_NUMBER is required}"
: "${RAX3000M_DEVICE:?RAX3000M_DEVICE is required}"
printf '%s\n' "$CONFIG_VERSION_NUMBER" | grep -Eq '^[0-9]+[.][0-9]+_b[0-9]{12}$'
case "$RAX3000M_DEVICE" in
	cmcc_rax3000m|cmcc_rax3000m-emmc-ubootlayout|cmcc_rax3000m-nand-ubootlayout) ;;
	*) echo "upload: unsupported device" >&2; exit 1 ;;
esac
builder_root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
python3 "$builder_root/profiles/rax3000m/export-images.py" \
	. "$CONFIG_VERSION_NUMBER" "$RAX3000M_DEVICE"
