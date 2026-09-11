#!/bin/sh
set -eu

release_tag=${1:-}
if [ -z "$release_tag" ]; then
	release_tag=$(
		git ls-remote --tags --refs https://github.com/x-wrt/x-wrt.git |
			awk -F/ '{print $3}' |
			grep -E '^[0-9]+[.][0-9]+_b[0-9]{12}$' |
			sort -V |
			tail -n 1
	)
fi

printf '%s\n' "$release_tag" | grep -Eq '^[0-9]+[.][0-9]+_b[0-9]{12}$' || {
	echo "Invalid X-WRT release tag: $release_tag" >&2
	exit 1
}

gh workflow run main.yml --ref tenda-be12-pro -f "release_tag=$release_tag"
echo "Requested GitHub Actions build for $release_tag."
