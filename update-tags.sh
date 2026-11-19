#!/bin/sh
set -eu
release_tag=${1:-}
device=${2:-all}
gh workflow run main.yml --repo NICOLE1224/build-release --ref ea0326gmp-k2p \
	-f "release_tag=$release_tag" -f "device=$device"
echo "Requested EA0326GMP/K2P build: ${release_tag:-newest official tag}, $device"
