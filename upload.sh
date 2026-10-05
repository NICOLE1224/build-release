#!/bin/sh
set -eu
: "${CONFIG_VERSION_NUMBER:?CONFIG_VERSION_NUMBER is required}"
: "${RAX3000M_DEVICE:?RAX3000M_DEVICE is required}"
printf '%s\n' "$CONFIG_VERSION_NUMBER" | grep -Eq '^[0-9]+[.][0-9]+_b[0-9]{12}$'
case "$RAX3000M_DEVICE" in
	cmcc_rax3000m|cmcc_rax3000m-emmc-ubootlayout|cmcc_rax3000m-nand-ubootlayout) ;;
	*) echo "upload: unsupported device" >&2; exit 1 ;;
esac
target_dir=bin/targets/mediatek/filogic
prefix="x-wrt-${CONFIG_VERSION_NUMBER}-mediatek-filogic-${RAX3000M_DEVICE}"
mkdir -p rom
case "$RAX3000M_DEVICE" in
	cmcc_rax3000m)
		recovery="$prefix-initramfs-recovery.itb"
		sysupgrade="$prefix-squashfs-sysupgrade.itb"
		;;
	*)
		recovery="$prefix-initramfs-kernel.bin"
		sysupgrade="$prefix-squashfs-sysupgrade.bin"
		;;
esac
for filename in "$recovery" "$sysupgrade"; do
	[ -s "$target_dir/$filename" ] || {
		echo "upload: missing required firmware $filename" >&2; exit 1
	}
	cp "$target_dir/$filename" rom/
done
# Hash only this run's exported images.
set -- "$recovery" "$sysupgrade"
factory="$prefix-squashfs-factory.bin"
if [ -s "$target_dir/$factory" ]; then
	cp "$target_dir/$factory" rom/
	set -- "$@" "$factory"
fi
(cd rom && sha256sum "$@" >"sha256-${CONFIG_VERSION_NUMBER}.sum")