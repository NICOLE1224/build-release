#!/bin/bash
set -euo pipefail
jobs=${1:?usage: build.sh JOBS}
: "${CONFIG_VERSION_NUMBER:?CONFIG_VERSION_NUMBER is required}"
: "${BUILD_DEVICE:?BUILD_DEVICE is required}"
echo "Building ${BUILD_DEVICE} (${CONFIG_VERSION_NUMBER}) with ${jobs} jobs."
if ! make -j"$jobs"; then
	make -j1 V=s 2>&1 | tee ../make.log
fi
