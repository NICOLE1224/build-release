#!/bin/sh
# Dispatch the firmware builds of every device branch that are out of date.
#
# Each branch keeps its own .github/workflows/main.yml. GitHub only runs
# scheduled workflows from the default branch, so this script runs from there
# and starts the other branches' builds with workflow_dispatch.
#
# A firmware is out of date when its release is missing or its manifest does
# not record the current dynamic inputs: the newest X-WRT tag (part of every
# release tag), the newest stable Sing-box (BE12 Pro) and the MosDNS branch head
# (BE12 Pro, RAX3000M). Pinned inputs change only through branch commits.
#
# Environment:
#   GITHUB_REPOSITORY  owner/name of this repository (required)
#   FORCE=true         dispatch all firmwares regardless of their state
#   DRY_RUN=true       print the dispatches instead of running them
#   RETRY_HOURS=6      wait this long before retrying a failed branch head
set -eu

repo=${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}
force=${FORCE:-false}
dry_run=${DRY_RUN:-false}
retry_hours=${RETRY_HOURS:-6}
workflow=main.yml
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

die() {
	echo "schedule: $*" >&2
	exit 1
}

latest_xwrt_tag() {
	git ls-remote --tags --refs https://github.com/x-wrt/x-wrt.git |
		awk -F/ '{print $3}' |
		grep -E '^[0-9]+[.][0-9]+_b[0-9]{12}$' |
		sort -V |
		tail -n 1
}

latest_sing_box_version() {
	tag=$(gh api -H 'X-GitHub-Api-Version: 2022-11-28' \
		repos/SagerNet/sing-box/releases/latest \
		--jq 'select(.draft == false and .prerelease == false) | .tag_name')
	printf '%s\n' "$tag" | grep -Eqx 'v[0-9]+[.][0-9]+[.][0-9]+' ||
		die "invalid Sing-box tag: $tag"
	printf '%s\n' "${tag#v}"
}

# Prints "<branch> <revision>" for the MosDNS branch a device branch follows.
mosdns_head() {
	branch=$1
	profile=$2
	env_file="$work_dir/$branch.sources.env"
	gh api -H 'Accept: application/vnd.github.raw' \
		"repos/$repo/contents/profiles/$profile/sources.env?ref=$branch" >"$env_file"
	mosdns_repository=$(sed -n 's/^MOSDNS_REPOSITORY=//p' "$env_file")
	mosdns_branch=$(sed -n 's/^MOSDNS_BRANCH=//p' "$env_file")
	[ -n "$mosdns_repository" ] && [ -n "$mosdns_branch" ] ||
		die "$branch does not define MOSDNS_REPOSITORY and MOSDNS_BRANCH"
	revision=$(git ls-remote "$mosdns_repository" "refs/heads/$mosdns_branch" |
		awk '{print $1}')
	printf '%s\n' "$revision" | grep -Eqx '[0-9a-f]{40}' ||
		die "cannot resolve MosDNS $mosdns_branch for $branch"
	printf '%s %s\n' "$mosdns_branch" "$revision"
}

# Succeeds when release $1 has a manifest containing every fixed string $2...
release_is_current() {
	asset_tag=$1
	shift
	manifest_dir="$work_dir/$asset_tag"
	mkdir -p "$manifest_dir"
	gh release download "$asset_tag" --repo "$repo" \
		--pattern build-manifest.txt --dir "$manifest_dir" >/dev/null 2>&1 ||
		return 1
	for expected in "$@"; do
		grep -Fq "$expected" "$manifest_dir/build-manifest.txt" || return 1
	done
}

# Succeeds when the branch must not be dispatched now: a build is already
# queued or running, or its last build failed on the current branch head less
# than RETRY_HOURS ago.
branch_is_blocked() {
	branch=$1
	# On any lookup error, skip rather than risk queueing a duplicate build.
	# Prints: <active runs> <last conclusion> <last head SHA> <last start epoch>
	state=$(gh run list --repo "$repo" --workflow "$workflow" --branch "$branch" \
		--limit 20 --json status,conclusion,headSha,createdAt --jq '
		([.[] | select(.status != "completed")] | length) as $active |
		(first(.[] | select(.status == "completed")) //
			{conclusion: "none", headSha: "none", createdAt: "1970-01-01T00:00:00Z"}) as $last |
		"\($active) \($last.conclusion) \($last.headSha) \($last.createdAt | fromdateiso8601)"') || {
		echo "$branch: cannot list builds; skipping"
		return 0
	}
	# shellcheck disable=SC2086
	set -- $state
	[ $# -eq 4 ] || {
		echo "$branch: unexpected build state '$state'; skipping"
		return 0
	}
	if [ "$1" -gt 0 ]; then
		echo "$branch: a build is already queued or running"
		return 0
	fi
	[ "$2" = failure ] || return 1
	head_sha=$(gh api "repos/$repo/branches/$branch" --jq .commit.sha) || {
		echo "$branch: cannot resolve branch head; skipping"
		return 0
	}
	age=$(($(date +%s) - $4))
	if [ "$3" = "$head_sha" ] && [ "$age" -lt $((retry_hours * 3600)) ]; then
		echo "$branch: last build of $head_sha failed $((age / 60)) min ago; retrying after ${retry_hours}h"
		return 0
	fi
	return 1
}

dispatch() {
	branch=$1
	shift
	echo "$branch: dispatching $*"
	if [ "$dry_run" = true ]; then
		return 0
	fi
	args=
	for field in "$@"; do
		args="$args -f $field"
	done
	# shellcheck disable=SC2086
	gh workflow run "$workflow" --repo "$repo" --ref "$branch" $args
}

xwrt_tag=$(latest_xwrt_tag)
printf '%s\n' "$xwrt_tag" | grep -Eqx '[0-9]+[.][0-9]+_b[0-9]{12}' ||
	die "cannot resolve the newest X-WRT tag"
echo "X-WRT tag: $xwrt_tag"

# Tenda BE12 Pro: release tag is the X-WRT tag.
branch=tenda-be12-pro
sing_box_version=$(latest_sing_box_version)
mosdns=$(mosdns_head "$branch" tenda-be12-pro)
# shellcheck disable=SC2086
set -- $mosdns
if [ "$force" != true ] &&
	release_is_current "$xwrt_tag" \
		"sing-box latest-stable $sing_box_version " \
		"mosdns branch:$1 $2 "; then
	echo "$branch: release is current"
elif [ "$force" = true ] || ! branch_is_blocked "$branch"; then
	dispatch "$branch" "release_tag=$xwrt_tag"
fi

# CMCC RAX3000M: one firmware for the default layout.
branch=rax3000m
device=cmcc_rax3000m
mosdns=$(mosdns_head "$branch" rax3000m)
# shellcheck disable=SC2086
set -- $mosdns
if [ "$force" != true ] &&
	release_is_current "rax3000m-$xwrt_tag-$device" "mosdns branch:$1 $2 "; then
	echo "$branch: release is current"
elif [ "$force" = true ] || ! branch_is_blocked "$branch"; then
	dispatch "$branch" "release_tag=$xwrt_tag" "device=$device"
fi

# Nokia EA0326GMP and Phicomm K2P: one release per device.
branch=ea0326gmp-k2p
outdated=
for device in nokia_ea0326gmp phicomm_k2p; do
	if [ "$force" != true ] && release_is_current "$device-$xwrt_tag"; then
		echo "$branch: $device release is current"
	else
		outdated="$outdated $device"
	fi
done
outdated=${outdated# }
case "$outdated" in
'') ;;
*' '*) devices=all ;;
*) devices=$outdated ;;
esac
if [ -n "$outdated" ] && { [ "$force" = true ] || ! branch_is_blocked "$branch"; }; then
	dispatch "$branch" "release_tag=$xwrt_tag" "device=$devices"
fi
