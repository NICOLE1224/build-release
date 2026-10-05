#!/bin/bash
set -euo pipefail
jobs=${1:?usage: build.sh JOBS}
: "${CONFIG_VERSION_NUMBER:?CONFIG_VERSION_NUMBER is required}"
: "${RAX3000M_DEVICE:?RAX3000M_DEVICE is required}"
echo "Building ${RAX3000M_DEVICE} (${CONFIG_VERSION_NUMBER}) with ${jobs} jobs."
if ! make -j"$jobs"; then
	make -j1 V=s 2>&1 | tee ../make.log
fi
