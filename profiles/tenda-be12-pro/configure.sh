#!/bin/sh
set -eu

profile_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
source_root=${1:-$(pwd)}
release_tag=${2:?usage: configure.sh SOURCE_ROOT RELEASE_TAG}

printf '%s\n' "$release_tag" |
	grep -Eq '^[0-9]+[.][0-9]+_b[0-9]{12}$' || {
	echo "configure: invalid X-WRT release tag: $release_tag" >&2
	exit 1
}

[ -x "$source_root/scripts/diffconfig.sh" ] || {
	echo "configure: invalid X-WRT source tree: $source_root" >&2
	exit 1
}

cp "$profile_dir/config.seed" "$source_root/.config"
printf 'CONFIG_VERSION_NUMBER="%s"\n' "$release_tag" >>"$source_root/.config"
make -C "$source_root" defconfig

grep -Fqx 'CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_tenda_be12-pro=y' \
	"$source_root/.config"
device_count=$(grep -Ec '^CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_.*=y$' \
	"$source_root/.config")
[ "$device_count" -eq 1 ] || {
	echo "configure: expected one selected mediatek-filogic device, found $device_count" >&2
	exit 1
}

while IFS= read -r package; do
	case "$package" in ''|'#'*) continue ;; esac
	grep -Fqx "CONFIG_PACKAGE_${package}=y" "$source_root/.config" || {
		echo "configure: required package is not built in: $package" >&2
		exit 1
	}
done <"$profile_dir/packages.required"

while IFS= read -r package; do
	case "$package" in ''|'#'*) continue ;; esac
	if grep -Eq "^CONFIG_PACKAGE_${package}=(y|m)$" "$source_root/.config"; then
		echo "configure: excluded package is selected: $package" >&2
		exit 1
	fi
done <"$profile_dir/packages.excluded"

actual_seed="$source_root/.config.seed.actual"
(cd "$source_root" && ./scripts/diffconfig.sh) |
	sed '/^CONFIG_VERSION_NUMBER=/d' >"$actual_seed"

if ! cmp -s "$profile_dir/config.seed" "$actual_seed"; then
	echo "configure: config.seed drifted after make defconfig" >&2
	diff -u "$profile_dir/config.seed" "$actual_seed" || true
	exit 1
fi
rm -f "$actual_seed"
