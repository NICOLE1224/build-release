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

sing_box_makefile="feeds/packages/net/sing-box/Makefile"
be12_make_script="feeds/x/rom/lede/make.sh"
be12_config="feeds/x/rom/lede/config.mediatek-filogic-be12pro-only"

sed -i \
	-e 's/^PKG_VERSION:=.*/PKG_VERSION:=1.14.0-rc.4/' \
	-e 's/^PKG_HASH:=.*/PKG_HASH:=7d30e1c5fd812cc2b43d88802632126cd969490381f7754d6739fd5810f67c68/' \
	"$sing_box_makefile"

grep -Fqx 'PKG_VERSION:=1.14.0-rc.4' "$sing_box_makefile"
grep -Fqx 'PKG_HASH:=7d30e1c5fd812cc2b43d88802632126cd969490381f7754d6739fd5810f67c68' \
	"$sing_box_makefile"

sed -i \
	-e 's#s/luci-app-openclash/luci-app-homeproxy luci-app-mosdns/#s/luci-app-openclash/sing-box luci-app-mosdns/#' \
	-e 's/be12_excluded_packages="kmod-mt7915e kmod-usb-core kmod-usb-common"/be12_excluded_packages="kmod-mt7915e kmod-usb-core kmod-usb-common luci-app-homeproxy"/' \
	"$be12_make_script"

grep -Fq 's/luci-app-openclash/sing-box luci-app-mosdns/' "$be12_make_script"
grep -Fq 'be12_excluded_packages="kmod-mt7915e kmod-usb-core kmod-usb-common luci-app-homeproxy"' \
	"$be12_make_script"

sed -i \
	's/^CONFIG_PACKAGE_luci-app-homeproxy=y$/# CONFIG_PACKAGE_luci-app-homeproxy is not set/' \
	"$be12_config"

grep -Fqx '# CONFIG_PACKAGE_luci-app-homeproxy is not set' "$be12_config"

clone_pinned \
	https://github.com/sbwml/luci-app-mosdns.git \
	65060f710fb80c2d8881fa861e780a0bb32524b7 \
	package/custom/mosdns

clone_pinned \
	https://github.com/sbwml/v2ray-geodata.git \
	2e3845caae172326f02b3406048c7a3613f3dee5 \
	package/custom/v2ray-geodata

sed -i \
	-e 's|^GEOIP_URL:=.*|GEOIP_URL:=https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip-lite.dat|' \
	-e 's|^GEOSITE_URL:=.*|GEOSITE_URL:=https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat|' \
	package/custom/v2ray-geodata/Makefile

sed -i \
	-e 's|let geoip_url = mirror + "https://github.com/Loyalsoldier/geoip/releases/latest/download/" + geoip_type + ".dat";|let geoip_url = mirror + "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip-lite.dat";|' \
	-e 's|let geosite_url = mirror + "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat";|let geosite_url = mirror + "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat";|' \
	package/custom/mosdns/luci-app-mosdns/root/usr/share/mosdns/mosdns.uc

grep -Fq 'GEOIP_URL:=https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip-lite.dat' \
	package/custom/v2ray-geodata/Makefile
grep -Fq 'GEOSITE_URL:=https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat' \
	package/custom/v2ray-geodata/Makefile
grep -Fq 'let geoip_url = mirror + "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip-lite.dat";' \
	package/custom/mosdns/luci-app-mosdns/root/usr/share/mosdns/mosdns.uc
grep -Fq 'let geosite_url = mirror + "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat";' \
	package/custom/mosdns/luci-app-mosdns/root/usr/share/mosdns/mosdns.uc
