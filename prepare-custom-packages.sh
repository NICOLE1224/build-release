#!/bin/sh
set -eu

clone_pinned() {
	repository="$1"
	revision="$2"
	destination="$3"

	git clone --filter=blob:none --no-checkout "$repository" "$destination"
	git -C "$destination" fetch --depth 1 origin "$revision"
	git -C "$destination" checkout --detach "$revision"
}

mkdir -p package/custom

if [ -L package/feeds/packages/v2ray-geodata ]; then
	rm package/feeds/packages/v2ray-geodata
fi

clone_pinned \
	https://github.com/immortalwrt/homeproxy.git \
	e8b8ebcfbdd1759c5f7f323b5a9d32b5b5434954 \
	package/custom/luci-app-homeproxy

clone_pinned \
	https://github.com/sbwml/luci-app-mosdns.git \
	65060f710fb80c2d8881fa861e780a0bb32524b7 \
	package/custom/mosdns

clone_pinned \
	https://github.com/sbwml/v2ray-geodata.git \
	2e3845caae172326f02b3406048c7a3613f3dee5 \
	package/custom/v2ray-geodata
