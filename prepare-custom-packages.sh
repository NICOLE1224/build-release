#!/bin/sh
set -eu
repository_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
exec sh "$repository_dir/profiles/rax3000m/prepare.sh" "${1:-$(pwd)}"