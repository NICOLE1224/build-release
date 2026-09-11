#!/bin/sh
set -eu

profile_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
builder_root=$(CDPATH='' cd -- "$profile_dir/../.." && pwd)
source_root=${1:?usage: write-provenance.sh SOURCE_ROOT RELEASE_TAG OUTPUT}
release_tag=${2:?usage: write-provenance.sh SOURCE_ROOT RELEASE_TAG OUTPUT}
output=${3:?usage: write-provenance.sh SOURCE_ROOT RELEASE_TAG OUTPUT}

# shellcheck disable=SC1091
. "$profile_dir/sources.env"
sing_box_state="$source_root/.build-profile/tenda-be12-pro/sing-box.env"
[ -f "$sing_box_state" ] || {
	echo "provenance: missing resolved Sing-box state" >&2
	exit 1
}
# shellcheck disable=SC1090
. "$sing_box_state"

{
	printf 'release_tag=%s\n' "$release_tag"
	printf 'builder_url=%s\n' "$(git -C "$builder_root" config --get remote.origin.url)"
	printf 'builder_commit=%s\n' "$(git -C "$builder_root" rev-parse HEAD)"
	printf 'source_url=%s\n' 'https://github.com/x-wrt/x-wrt.git'
	printf 'source_commit=%s\n' "$(git -C "$source_root" rev-parse HEAD)"
	printf 'config_seed_sha256=%s\n' "$(sha256sum "$profile_dir/config.seed" | awk '{print $1}')"
	printf '\n[feeds]\n'
	for feed in "$source_root"/feeds/*; do
		[ ! -L "$feed" ] || continue
		[ -d "$feed/.git" ] || continue
		printf '%s %s %s\n' \
			"$(basename "$feed")" \
			"$(git -C "$feed" rev-parse HEAD)" \
			"$(git -C "$feed" config --get remote.origin.url)"
	done
	printf '\n[custom_sources]\n'
	printf 'mosdns %s %s\n' "$MOSDNS_REVISION" "$MOSDNS_REPOSITORY"
	printf 'v2ray-geodata %s %s\n' "$V2RAY_GEODATA_REVISION" "$V2RAY_GEODATA_REPOSITORY"
	printf 'sing-box latest-stable %s sha256:%s %s\n' \
		"$SING_BOX_VERSION" "$SING_BOX_SOURCE_SHA256" "$SING_BOX_SOURCE_URL"
	printf 'sing-box_release_api=%s\n' "$SING_BOX_RELEASE_API"
	printf 'sing-box_release_id=%s\n' "$SING_BOX_RELEASE_ID"
	printf 'sing-box_published_at=%s\n' "$SING_BOX_PUBLISHED_AT"
	printf 'meta-rules-dat %s\n' "$META_RULES_REVISION"
	printf 'geoip-lite.dat sha256:%s\n' "$GEOIP_SHA256"
	printf 'geosite.dat sha256:%s\n' "$GEOSITE_SHA256"
} >"$output"
