#!/usr/bin/env python3
"""Derive a single-device configuration from the selected tag's official feed."""
import re
import sys
from pathlib import Path

DEVICES = {
    "cmcc_rax3000m",
    "cmcc_rax3000m-emmc-ubootlayout",
    "cmcc_rax3000m-nand-ubootlayout",
}
APPLICATIONS = ["luci-app-mosdns", "luci-app-wol", "luci-app-vlmcsd"]


def configure(source: Path, tag: str, device: str) -> None:
    if device not in DEVICES:
        raise ValueError(f"unsupported device: {device}")
    if not re.fullmatch(r"\d+\.\d+_b\d{12}", tag):
        raise ValueError(f"invalid release tag: {tag}")
    selected = f"CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_{device}"
    package_key = f"CONFIG_TARGET_DEVICE_PACKAGES_mediatek_filogic_DEVICE_{device}"
    candidates = []
    for path in sorted((source / "feeds/x/rom/lede").glob("config.mediatek-filogic*")):
        lines = path.read_text().splitlines()
        if f"{selected}=y" in lines:
            candidates.append((path, lines))
    if len(candidates) != 1:
        raise ValueError(f"expected one official configuration for {device}, found {len(candidates)}")
    upstream, lines = candidates[0]
    if "CONFIG_TARGET_PER_DEVICE_ROOTFS=y" not in lines:
        raise ValueError("official configuration does not enable per-device root filesystems")
    package_lines = [line for line in lines if line.startswith(package_key + "=")]
    if len(package_lines) != 1:
        raise ValueError("missing or ambiguous official device package list")
    packages = package_lines[0].split('"')[1].split()
    packages = list(dict.fromkeys(packages + APPLICATIONS))
    required = (Path(__file__).parent / "packages.required").read_text().splitlines()
    overrides = {f"CONFIG_PACKAGE_{package}": "y" for package in required}
    overrides.update({
        "CONFIG_ALL_KMODS": "n",
        "CONFIG_ALL_NONSHARED": "n",
        "CONFIG_SDK": "n",
        "CONFIG_IB": "n",
        "CONFIG_VERSION_NUMBER": f'"{tag}"',
    })
    result = []
    for line in lines:
        if line.startswith("CONFIG_TARGET_DEVICE_"):
            if line == f"{selected}=y":
                result.append(line)
            elif line.startswith(package_key + "="):
                result.append(f'{package_key}="{" ".join(packages)}"')
            continue
        key = line.split("=", 1)[0]
        unset = re.fullmatch(r"# (CONFIG_\S+) is not set", line)
        if key in overrides or (unset and unset[1] in overrides):
            continue
        # Let defconfig select modules required by the chosen device, instead of
        # carrying optional modules for other devices from the multi-device feed.
        if re.fullmatch(r"CONFIG_PACKAGE_.*=m", line):
            continue
        result.append(line)
    for key, value in overrides.items():
        result.append(f"# {key} is not set" if value == "n" else f"{key}={value}")
    (source / ".config").write_text("\n".join(result) + "\n", newline="\n")
    state = source / ".build-profile/rax3000m"
    state.mkdir(parents=True, exist_ok=True)
    (state / "upstream-config").write_text(upstream.name + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("usage: configure.py SOURCE_ROOT RELEASE_TAG DEVICE")
    try:
        configure(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
    except ValueError as error:
        sys.exit(f"configure: {error}")
