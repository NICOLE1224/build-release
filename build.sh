#!/bin/bash
set -uo pipefail

jobs=${1:?usage: build.sh JOBS}
: "${CONFIG_VERSION_NUMBER:?CONFIG_VERSION_NUMBER is required}"

export CFGS=config.nico-tenda-be12-pro
export WORKFLOW=1

echo "Starting Tenda BE12 Pro build with ${jobs} jobs."
df -h .
free -m

if ./feeds/x/rom/lede/make.sh make -j"$jobs"; then
	sh upload.sh
	exit $?
fi

make -j1 V=s 2>&1 | tee ../make.log
build_status=${PIPESTATUS[0]}
[ "$build_status" -eq 0 ] || exit "$build_status"

sh upload.sh
