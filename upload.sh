#!/bin/sh
set -eu

target_dir=bin/targets/mediatek/filogic
rom_dir=rom
sdk_dir=$rom_dir/sdk

copy_one() {
	pattern=$1
	destination=$2
	# shellcheck disable=SC2086 # Intentional expansion of the single pattern.
	set -- "$target_dir"/$pattern
	if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
		echo "upload: expected exactly one file matching $pattern" >&2
		exit 1
	fi
	cp "$1" "$destination/"
	basename "$1"
}

mkdir -p "$rom_dir" "$sdk_dir"

initramfs=$(copy_one \
	'x-wrt-*-mediatek-filogic-tenda_be12-pro-initramfs-kernel.bin' \
	"$rom_dir")
sysupgrade=$(copy_one \
	'x-wrt-*-mediatek-filogic-tenda_be12-pro-squashfs-sysupgrade.bin' \
	"$rom_dir")
sdk=$(copy_one 'x-wrt-sdk-*-mediatek-filogic_*.tar.zst' "$sdk_dir")

printf 'Tenda BE12 Pro:%s %s\n' "$initramfs" "$sysupgrade" \
	>"$rom_dir/map.list"
(
	cd "$rom_dir"
	sha256sum "$initramfs" "$sysupgrade" >sha256sums.txt
)
printf '%s\n' "$sdk" >"$sdk_dir/sdk_map.list"
(
	cd "$sdk_dir"
	sha256sum "$sdk" >sdk_sha256sums.txt
)
