#!/bin/sh
set -eu

repository_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
source_root=${1:-$(pwd)}

exec sh "$repository_dir/profiles/tenda-be12-pro/prepare.sh" "$source_root"
