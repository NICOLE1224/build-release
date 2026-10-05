#!/bin/sh
set -eu
release_tag=${1:-}
device=${2:-cmcc_rax3000m}
gh workflow run main.yml --repo NICOLE1224/build-release --ref rax3000m \
	-f "release_tag=$release_tag" -f "device=$device"
echo "Requested RAX3000M build: ${release_tag:-newest official tag}, $device"