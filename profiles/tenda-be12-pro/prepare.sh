#!/bin/sh
set -eu

profile_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
source_root=${1:-$(pwd)}

# shellcheck disable=SC1091
. "$profile_dir/sources.env"

die() {
	echo "prepare: $*" >&2
	exit 1
}

clone_pinned() {
	repository=$1
	revision=$2
	destination=$3

	[ ! -e "$destination" ] || die "$destination already exists"
	git clone --filter=blob:none --no-checkout "$repository" "$destination"
	git -C "$destination" fetch --depth 1 origin "$revision"
	git -C "$destination" checkout --detach "$revision"
	[ "$(git -C "$destination" rev-parse HEAD)" = "$revision" ] ||
		die "unexpected revision in $destination"
}

apply_patch() {
	repository=$1
	patch_file=$2

	git -C "$repository" apply --check "$patch_file"
	git -C "$repository" apply "$patch_file"
}

prepare_latest_stable_sing_box() {
	makefile=$1
	state_dir=$2

	command -v jq >/dev/null 2>&1 || die "jq is required to resolve Sing-box releases"
	if [ -n "${GH_TOKEN:-}" ] && command -v gh >/dev/null 2>&1; then
		release_json=$(gh api \
			-H 'X-GitHub-Api-Version: 2022-11-28' \
			"repos/$SING_BOX_GITHUB_REPOSITORY/releases/latest")
	else
		release_json=$(curl --fail --silent --show-error --location --retry 3 \
			-H 'Accept: application/vnd.github+json' \
			-H 'X-GitHub-Api-Version: 2022-11-28' \
			"$SING_BOX_RELEASE_API")
	fi
	stable_tag=$(printf '%s\n' "$release_json" |
		jq -er 'select(.draft == false and .prerelease == false) |
			.tag_name | select(test("^v[0-9]+\\.[0-9]+\\.[0-9]+$"))')
	release_id=$(printf '%s\n' "$release_json" | jq -er '.id | numbers')
	published_at=$(printf '%s\n' "$release_json" | jq -er '.published_at | strings')

	printf '%s\n' "$stable_tag" |
		grep -Eq '^v[0-9]+[.][0-9]+[.][0-9]+$' ||
		die "invalid stable sing-box tag: $stable_tag"
	printf '%s\n' "$release_id" | grep -Eq '^[0-9]+$' ||
		die "invalid Sing-box release ID"
	printf '%s\n' "$published_at" |
		grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' ||
		die "invalid Sing-box release timestamp"
	version=${stable_tag#v}
	source_url="$SING_BOX_SOURCE_BASE_URL/$stable_tag"
	archive="sing-box-$version.tar.gz"
	archive_tmp="$source_root/dl/.$archive.tmp.$$"

	mkdir -p "$source_root/dl" "$state_dir"
	trap 'rm -f "$archive_tmp"' EXIT HUP INT TERM
	curl --fail --location --retry 3 "$source_url" --output "$archive_tmp"
	source_sha256=$(sha256sum "$archive_tmp" | awk '{print $1}')
	mv "$archive_tmp" "$source_root/dl/$archive"
	trap - EXIT HUP INT TERM

	[ "$(grep -c '^PKG_VERSION:=' "$makefile")" -eq 1 ] ||
		die "unexpected sing-box PKG_VERSION definition"
	[ "$(grep -c '^PKG_HASH:=' "$makefile")" -eq 1 ] ||
		die "unexpected sing-box PKG_HASH definition"
	grep -Fqx "PKG_SOURCE:=\$(PKG_NAME)-\$(PKG_VERSION).tar.gz" "$makefile" ||
		die "unexpected sing-box source archive definition"
	grep -Fqx "PKG_SOURCE_URL:=https://codeload.github.com/SagerNet/sing-box/tar.gz/v\$(PKG_VERSION)?" \
		"$makefile" || die "unexpected sing-box source URL definition"
	grep -Fqx "GO_PKG_LDFLAGS_X:=\$(GO_PKG)/constant.Version=\$(PKG_VERSION)" \
		"$makefile" || die "unexpected sing-box version ldflag"

	sed -i \
		-e "s/^PKG_VERSION:=.*/PKG_VERSION:=$version/" \
		-e "s/^PKG_HASH:=.*/PKG_HASH:=$source_sha256/" \
		"$makefile"
	grep -Fqx "PKG_VERSION:=$version" "$makefile"
	grep -Fqx "PKG_HASH:=$source_sha256" "$makefile"

	{
		printf 'SING_BOX_VERSION=%s\n' "$version"
		printf 'SING_BOX_SOURCE_SHA256=%s\n' "$source_sha256"
		printf 'SING_BOX_SOURCE_URL=%s\n' "$source_url"
		printf 'SING_BOX_RELEASE_ID=%s\n' "$release_id"
		printf 'SING_BOX_PUBLISHED_AT=%s\n' "$published_at"
	} >"$state_dir/sing-box.env"
}

[ -d "$source_root/feeds/packages/.git" ] || die "run feeds update before this script"
mkdir -p "$source_root/package/custom"

v2ray_feed="$source_root/package/feeds/packages/v2ray-geodata"
if [ -L "$v2ray_feed" ]; then
	unlink "$v2ray_feed"
elif [ -e "$v2ray_feed" ]; then
	die "$v2ray_feed exists but is not a feed symlink"
fi

clone_pinned "$MOSDNS_REPOSITORY" "$MOSDNS_REVISION" \
	"$source_root/package/custom/mosdns"
clone_pinned "$V2RAY_GEODATA_REPOSITORY" "$V2RAY_GEODATA_REVISION" \
	"$source_root/package/custom/v2ray-geodata"

prepare_latest_stable_sing_box \
	"$source_root/feeds/packages/net/sing-box/Makefile" \
	"$source_root/.build-profile/tenda-be12-pro"
apply_patch "$source_root/package/custom/mosdns" "$profile_dir/patches/mosdns-geodata.patch"
apply_patch "$source_root/package/custom/v2ray-geodata" "$profile_dir/patches/v2ray-geodata.patch"

grep -Fqx "PKG_VERSION:=$GEODATA_VERSION" \
	"$source_root/package/custom/v2ray-geodata/Makefile"
grep -Fqx "META_RULES_REVISION:=$META_RULES_REVISION" \
	"$source_root/package/custom/v2ray-geodata/Makefile"
grep -Fqx "GEOIP_HASH:=$GEOIP_SHA256" \
	"$source_root/package/custom/v2ray-geodata/Makefile"
grep -Fqx "GEOSITE_HASH:=$GEOSITE_SHA256" \
	"$source_root/package/custom/v2ray-geodata/Makefile"
