#!/bin/sh
set -eu
profile_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
source_root=${1:?usage: prepare.sh SOURCE_ROOT}
. "$profile_dir/sources.env"
[ -d "$source_root/feeds/packages/.git" ] || {
	echo "prepare: install the official feeds first" >&2; exit 1
}
mkdir -p "$source_root/package/custom" "$source_root/.build-profile/rax3000m"

clone_pinned() {
	repository=$1 revision=$2 destination=$3 subtree=${4:-}
	[ ! -e "$destination" ] || { echo "prepare: $destination already exists" >&2; exit 1; }
	git init "$destination"
	git -C "$destination" remote add origin "$repository"
	if [ -n "$subtree" ]; then
		git -C "$destination" sparse-checkout init --cone
		git -C "$destination" sparse-checkout set "$subtree"
	fi
	git -C "$destination" fetch --depth 1 --filter=blob:none origin "$revision"
	git -C "$destination" checkout --detach FETCH_HEAD
	[ "$(git -C "$destination" rev-parse HEAD)" = "$revision" ]
}
resolve_mosdns_revision() {
	# CI passes the commit it resolved earlier, so the build and the manifest
	# use the same input even if the branch moves in the meantime.
	revision=${MOSDNS_RESOLVED_REVISION:-}
	if [ -z "$revision" ]; then
		revision=$(git ls-remote "$MOSDNS_REPOSITORY" "refs/heads/$MOSDNS_BRANCH" | awk '{print $1}')
	fi
	printf '%s\n' "$revision" | grep -Eqx '[0-9a-f]{40}' || {
		echo "prepare: invalid MosDNS revision for branch $MOSDNS_BRANCH: $revision" >&2; exit 1
	}
	printf 'MOSDNS_BRANCH=%s\nMOSDNS_REVISION=%s\n' "$MOSDNS_BRANCH" "$revision" \
		>"$source_root/.build-profile/rax3000m/mosdns.env"
	MOSDNS_REVISION=$revision
}
resolve_mosdns_revision
clone_pinned "$MOSDNS_REPOSITORY" "$MOSDNS_REVISION" "$source_root/package/custom/mosdns"
clone_pinned "$VLMCSD_LUCI_REPOSITORY" "$VLMCSD_LUCI_REVISION" \
	"$source_root/.build-profile/rax3000m/vlmcsd-luci" applications/luci-app-vlmcsd
clone_pinned "$VLMCSD_SERVICE_REPOSITORY" "$VLMCSD_SERVICE_REVISION" \
	"$source_root/.build-profile/rax3000m/vlmcsd-service" net/vlmcsd
cp -R "$source_root/.build-profile/rax3000m/vlmcsd-luci/applications/luci-app-vlmcsd" \
	"$source_root/package/custom/luci-app-vlmcsd"
cp -R "$source_root/.build-profile/rax3000m/vlmcsd-service/net/vlmcsd" \
	"$source_root/package/custom/vlmcsd"

python3 "$profile_dir/adapt-vlmcsd.py" "$source_root/package/custom/luci-app-vlmcsd"
python3 "$profile_dir/adapt-vlmcsd-service.py" "$source_root/package/custom/vlmcsd"
python3 "$profile_dir/verify-vlmcsd.py" "$source_root/package/custom/luci-app-vlmcsd" \
	"$source_root/package/custom/vlmcsd"
patch_file="$profile_dir/patches/squeezelite-kconfig.patch"
git -C "$source_root/feeds/packages" apply --check "$patch_file"
git -C "$source_root/feeds/packages" apply "$patch_file"
