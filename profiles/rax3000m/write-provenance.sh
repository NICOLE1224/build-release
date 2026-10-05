#!/bin/sh
set -eu
profile_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
builder_root=$(CDPATH='' cd -- "$profile_dir/../.." && pwd)
source_root=${1:?usage: write-provenance.sh SOURCE_ROOT RELEASE_TAG DEVICE OUTPUT}
release_tag=${2:?}
device=${3:?}
output=${4:?}
. "$profile_dir/sources.env"
{
	printf 'release_tag=%s\ndevice=%s\n' "$release_tag" "$device"
	printf 'builder_commit=%s\n' "$(git -C "$builder_root" rev-parse HEAD)"
	printf 'source_commit=%s\n' "$(git -C "$source_root" rev-parse HEAD)"
	printf 'upstream_config=%s\n' "$(cat "$source_root/.build-profile/rax3000m/upstream-config")"
	printf 'config_sha256=%s\n' "$(sha256sum "$source_root/.config" | awk '{print $1}')"
	printf '\n[feeds]\n'
	for feed in "$source_root"/feeds/*; do
		[ ! -L "$feed" ] && [ -d "$feed/.git" ] || continue
		printf '%s %s %s\n' "$(basename "$feed")" \
			"$(git -C "$feed" rev-parse HEAD)" "$(git -C "$feed" config --get remote.origin.url)"
	done
	printf '\n[custom_sources]\n'
	printf 'mosdns %s %s\n' "$MOSDNS_REVISION" "$MOSDNS_REPOSITORY"
	printf 'vlmcsd-luci %s %s\n' "$VLMCSD_LUCI_REVISION" "$VLMCSD_LUCI_REPOSITORY"
	printf 'vlmcsd-service %s %s\n' "$VLMCSD_SERVICE_REVISION" "$VLMCSD_SERVICE_REPOSITORY"
	grep -E '^PKG_(VERSION|RELEASE|SOURCE_VERSION|HASH):=' \
		"$source_root/package/custom/vlmcsd/Makefile"
} >"$output"
