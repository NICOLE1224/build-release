#!/usr/bin/env python3
"""Derive a single-device configuration from the selected tag's official feed."""
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Device:
    target: str
    subtarget: str
    # Built-in applications in addition to the official device image.
    applications: tuple
    # Image provider -> fallbacks that must not share the root filesystem.
    # Select the provider in the base rootfs too, otherwise omitted modular
    # defaults become built-in on defconfig and conflict at image assembly.
    providers: dict = field(default_factory=dict)
    # Bootloader artifacts are exported when the build produces them.
    artifacts: tuple = ()

    @property
    def board(self) -> str:
        return f"{self.target}_{self.subtarget}"


COMMON_APPLICATIONS = (
    "luci-app-wol", "etherwake",
    "luci-app-vlmcsd", "vlmcsd", "luci-compat", "luci-lua-runtime",
)
DEVICES = {
    # MT7981B, 128 MiB SPI-NAND: room for the Tailscale client.
    "nokia_ea0326gmp": Device(
        "mediatek", "filogic",
        COMMON_APPLICATIONS + ("tailscale", "luci-app-tailscale-community"),
        {"apk-openssl": ("apk-mbedtls",), "wpad-openssl": ("wpad-basic-mbedtls",)},
        ("preloader.bin", "bl31-uboot.fip"),
    ),
    # MT7621, 16 MiB SPI-NOR (15744k firmware partition): Tailscale does not fit.
    "phicomm_k2p": Device(
        "ramips", "mt7621",
        COMMON_APPLICATIONS,
        {"apk-mbedtls": ("apk-openssl",), "wpad-mbedtls": ("wpad-basic-mbedtls", "wpad-openssl")},
    ),
}
# Clash/MosDNS families and their rule data are never built for these devices.
EXCLUDED = re.compile(r"clash|mihomo|mosdns|v2dat|v2ray-geo", re.I)


def is_excluded(package: str) -> bool:
    return bool(EXCLUDED.search(package.lstrip("-")))


def configure(source: Path, tag: str, device_name: str) -> None:
    if device_name not in DEVICES:
        raise ValueError(f"unsupported device: {device_name}")
    if not re.fullmatch(r"\d+\.\d+_b\d{12}", tag):
        raise ValueError(f"invalid release tag: {tag}")
    device = DEVICES[device_name]
    selected = f"CONFIG_TARGET_DEVICE_{device.board}_DEVICE_{device_name}"
    package_key = f"CONFIG_TARGET_DEVICE_PACKAGES_{device.board}_DEVICE_{device_name}"
    candidates = []
    pattern = f"config.{device.target}-{device.subtarget}*"
    for path in sorted((source / "feeds/x/rom/lede").glob(pattern)):
        lines = path.read_text().splitlines()
        if f"{selected}=y" in lines:
            candidates.append((path, lines))
    if len(candidates) != 1:
        raise ValueError(f"expected one official configuration for {device_name}, found {len(candidates)}")
    upstream, lines = candidates[0]
    if "CONFIG_TARGET_PER_DEVICE_ROOTFS=y" not in lines:
        raise ValueError("official configuration does not enable per-device root filesystems")
    if f"CONFIG_TARGET_{device.target}=y" not in lines or \
            f"CONFIG_TARGET_{device.board}=y" not in lines:
        raise ValueError("official configuration selects a different target")
    package_lines = [line for line in lines if line.startswith(package_key + "=")]
    if len(package_lines) != 1:
        raise ValueError("missing or ambiguous official device package list")
    packages = [package for package in package_lines[0].split('"')[1].split()
                if not is_excluded(package)]
    packages = list(dict.fromkeys(packages + list(device.applications)))
    upstream_values = dict(line.split("=", 1) for line in lines
                           if line.startswith("CONFIG_PACKAGE_") and "=" in line)
    # TARGET_DEVICE_PACKAGES is an image install list, not a Kconfig selection.
    # Its packages must also be enabled for compilation. Keep them modular so
    # per-device variants are installed only when assembling this device's image.
    overrides = {
        f"CONFIG_PACKAGE_{package}": "y" if upstream_values.get(f"CONFIG_PACKAGE_{package}") == "y" else "m"
        for package in packages if not package.startswith("-")
    }
    overrides.update({f"CONFIG_PACKAGE_{package}": "y" for package in device.applications})
    for preferred, fallbacks in device.providers.items():
        if preferred not in packages:
            raise ValueError(f"official device package list no longer requests {preferred}")
        overrides[f"CONFIG_PACKAGE_{preferred}"] = "y"
        overrides.update({f"CONFIG_PACKAGE_{fallback}": "n" for fallback in fallbacks})
    for line in lines:
        name = re.fullmatch(r"(?:# )?CONFIG_PACKAGE_(\S+?)(?:=.*| is not set)", line)
        if name and is_excluded(name[1]):
            overrides[f"CONFIG_PACKAGE_{name[1]}"] = "n"
    overrides.update({
        "CONFIG_ALL_KMODS": "n",
        "CONFIG_ALL_NONSHARED": "n",
        "CONFIG_SDK": "n",
        "CONFIG_IB": "n",
        # The exporter relies on profiles.json; ramips disables it upstream.
        "CONFIG_JSON_OVERVIEW_IMAGE_INFO": "y",
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
        # Selected-device modules are restored through overrides above. Drop
        # unrelated modules; defconfig resolves dependencies of the retained ones.
        if re.fullmatch(r"CONFIG_PACKAGE_.*=m", line):
            continue
        result.append(line)
    for key, value in overrides.items():
        result.append(f"# {key} is not set" if value == "n" else f"{key}={value}")
    (source / ".config").write_text("\n".join(result) + "\n", newline="\n")
    state = source / ".build-profile/ea0326gmp-k2p"
    state.mkdir(parents=True, exist_ok=True)
    (state / "upstream-config").write_text(upstream.name + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("usage: configure.py SOURCE_ROOT RELEASE_TAG DEVICE")
    try:
        configure(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
    except ValueError as error:
        sys.exit(f"configure: {error}")
