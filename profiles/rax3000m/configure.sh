#!/bin/sh
set -eu
profile_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
source_root=${1:?usage: configure.sh SOURCE_ROOT RELEASE_TAG DEVICE}
release_tag=${2:?usage: configure.sh SOURCE_ROOT RELEASE_TAG DEVICE}
device=${3:-cmcc_rax3000m}
python3 "$profile_dir/configure.py" "$source_root" "$release_tag" "$device"
make -C "$source_root" defconfig

grep -Fqx "CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_${device}=y" "$source_root/.config"
count=$(grep -Ec '^CONFIG_TARGET_DEVICE_.*=y$' "$source_root/.config")
[ "$count" -eq 1 ] || {
	echo "configure: expected exactly one RAX3000M device, found $count" >&2; exit 1
}
while IFS= read -r package; do
	case "$package" in ''|'#'*) continue ;; esac
	grep -Fqx "CONFIG_PACKAGE_${package}=y" "$source_root/.config" || {
		echo "configure: required package is not built in: $package" >&2; exit 1
	}
done <"$profile_dir/packages.required"
