# How to build x-wrt for your devices

## NICOLE1224 Tenda BE12 Pro build

This fork builds the long-lived `tenda-be12-pro` branch from
`NICOLE1224/x-wrt`. The branch pins the upstream feeds to the selected
upstream release tag and uses the matching long-lived
`NICOLE1224/com.x-wrt` `tenda-be12-pro` feed branch.

The custom build:

- replaces `luci-app-openclash` with `luci-app-homeproxy` and
  `luci-app-mosdns` in the Tenda BE12 Pro image;
- pins HomeProxy, MosDNS, and v2ray-geodata source revisions in
  `prepare-custom-packages.sh`;
- builds only the Tenda BE12 Pro profile instead of every
  `mediatek-filogic` device;
- disables preselected module packages and lets `make defconfig` restore
  only the dependencies required by the BE12 Pro image.

Trigger a build from a clone of this repository:

```sh
git switch tenda-be12-pro
sh update-tags.sh mediatek-filogic-tenda-be12-pro
```

Alternatively, open the repository's **Actions** page, select the workflow,
and use **Run workflow** on the
`tenda-be12-pro` branch.

The downloadable artifact is named
`x-wrt-tenda-be12-pro=mediatek-filogic`. Select the file containing
`tenda_be12-pro` from the extracted artifact.

Successful builds also publish a GitHub Release asset named
`x-wrt-tenda-be12-pro.mediatek-filogic-<release.tag>.zip`, plus a matching
`.sha256` checksum file. The release tag is read from `release.tag`.

## Automatic tagged builds

`NICOLE1224/x-wrt:tenda-be12-pro` owns upstream synchronization. It only syncs
the branch and pushes the matching release tag in `NICOLE1224/x-wrt`.

This repository checks `NICOLE1224/x-wrt` tags hourly. When it finds a newer
synced tag matching `N.N_bYYYYMMDDHHMM`, it builds that tag, publishes firmware
release assets with the same version, and records the built tag in
`release.tag` after a successful publish.

Both repositories must allow workflow write access:

1. Open **Settings** -> **Actions** -> **General**.
2. Set **Workflow permissions** to **Read and write permissions**.
3. Save the setting.

To build a tag manually, open **Actions** -> this workflow -> **Run workflow**
on the `tenda-be12-pro` branch, set `release_tag` and leave `source_ref` empty
to build the same tag from `NICOLE1224/x-wrt`.

## Upstream instructions


## First, fork this repository to your github account.

## Clone it from your fork.

```
git clone https://github.com/[your_account]/build-release.git
```

## Select a release tag to build.

You can find available tags at [https://github.com/x-wrt/x-wrt/tags](https://github.com/x-wrt/x-wrt/tags)

For example tag `23.06_b202307110013`
```
echo -n 23.06_b202307110013 >release.tag
```
Then you are going to build release tag `23.06_b202307110013`

If you want to build master branch, then use `master` as tag name
```
echo -n master >release.tag
```

## Run `sh update-tags.sh <target>` to start building your target.

Available targets see `cat target.list`
```
TARGET=ath79-generic
TARGET=ath79-generic-nosymbol
TARGET=ath79-nand
TARGET=ipq40xx-generic
TARGET=bcm27xx-bcm2709
TARGET=sunxi-cortexa7
TARGET=bcm27xx-bcm2710
TARGET=mediatek-mt7622
TARGET=mediatek-filogic
TARGET=qualcommax-ipq807x
TARGET=bcm27xx-bcm2711
TARGET=bcm53xx-generic
TARGET=ipq806x-generic
TARGET=kirkwood-generic
TARGET=mvebu-cortexa9
TARGET=ramips-mt7620
TARGET=ramips-mt7620-nosymbol
TARGET=ramips-mt7621
TARGET=ramips-mt7621-ext4fs
TARGET=ramips-mt76x8
TARGET=ramips-mt76x8-nosymbol
TARGET=rockchip-armv8
TARGET=armsr-armv8
TARGET=x86_64
TARGET=x86_64-docker
```

For example, to build all `ipq40xx-generic` target devices, please run:
```
sh update-tags.sh ipq40xx-generic
```

## What is your device target?

You can find your device firmware at [https://downloads.x-wrt.com/rom/](https://downloads.x-wrt.com/rom/)

and then you should known the target name

for example:

`Xiaomi Mi Router R3` target is `ramips-mt7620`

`P&W R619AC` target is `ipq40xx-generic`

`x86 64bits` target is `x86_64`

...
