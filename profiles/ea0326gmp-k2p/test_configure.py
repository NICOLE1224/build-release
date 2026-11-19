#!/usr/bin/env python3
"""Regression checks for single-device package selection and early validation."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

import configure

spec = importlib.util.spec_from_file_location("verify_config", Path(__file__).with_name("verify-config.py"))
verify_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_config)

DEVICE_PACKAGES = {
    "nokia_ea0326gmp": "apk-openssl libopenssl luci-app-openclash wpad-openssl",
    "phicomm_k2p": "apk-mbedtls kmod-mt7615e -uboot-envtools wpad-mbedtls",
}


class DevicePackagesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name)
        feed = self.source / "feeds/x/rom/lede"
        feed.mkdir(parents=True)
        for name, device in configure.DEVICES.items():
            lines = [f"CONFIG_TARGET_{device.target}=y", f"CONFIG_TARGET_{device.board}=y",
                     "CONFIG_TARGET_PER_DEVICE_ROOTFS=y", "CONFIG_TARGET_MULTI_PROFILE=y",
                     "# CONFIG_JSON_OVERVIEW_IMAGE_INFO is not set",
                     "CONFIG_PACKAGE_luci-app-openclash=m", "CONFIG_PACKAGE_libopenssl=y",
                     "CONFIG_PACKAGE_luci-app-mosdns=y", "# CONFIG_PACKAGE_v2ray-geoip is not set",
                     "CONFIG_PACKAGE_luci-compat=y", "CONFIG_PACKAGE_kmod-mt7615e=m",
                     "CONFIG_PACKAGE_unrelated-device-package=m",
                     "CONFIG_PACKAGE_apk-mbedtls=m", "CONFIG_PACKAGE_apk-openssl=m",
                     "CONFIG_PACKAGE_wpad-openssl=m", "CONFIG_PACKAGE_wpad-mbedtls=m",
                     "CONFIG_PACKAGE_wpad-basic-mbedtls=m",
                     f"CONFIG_TARGET_DEVICE_{device.board}_DEVICE_{name}=y",
                     f'CONFIG_TARGET_DEVICE_PACKAGES_{device.board}_DEVICE_{name}="{DEVICE_PACKAGES[name]}"',
                     f"CONFIG_TARGET_DEVICE_{device.board}_DEVICE_other=y"]
            (feed / f"config.{device.target}-{device.subtarget}").write_text("\n".join(lines) + "\n")
        # An unrelated configuration of the same target that does not build the device.
        (feed / "config.mediatek-filogic-1").write_text(
            "# CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_nokia_ea0326gmp is not set\n")
        metadata = self.source / "tmp/.config-package.in"
        metadata.parent.mkdir()
        metadata.write_text(
            "config PACKAGE_apk-mbedtls\n"
            "\tdepends on m || (PACKAGE_apk-openssl != y)\n"
            "config PACKAGE_wpad-openssl\n"
            "\tdepends on m || (PACKAGE_wpad-basic-mbedtls != y)\n"
            "config PACKAGE_wpad-mbedtls\n"
            "\tdepends on m || (PACKAGE_wpad-basic-mbedtls != y)\n"
        )

    def generate(self, device="nokia_ea0326gmp"):
        configure.configure(self.source, "26.10_b202611171234", device)
        return (self.source / ".config").read_text()

    def test_device_selection_and_applications(self):
        for name, device in configure.DEVICES.items():
            with self.subTest(device=name):
                text = self.generate(name)
                self.assertIn(f"CONFIG_TARGET_DEVICE_{device.board}_DEVICE_{name}=y\n", text)
                self.assertNotIn("DEVICE_other", text)
                self.assertIn("CONFIG_JSON_OVERVIEW_IMAGE_INFO=y\n", text)
                self.assertNotIn("CONFIG_PACKAGE_unrelated-device-package=", text)
                for package in configure.COMMON_APPLICATIONS:
                    self.assertIn(f"CONFIG_PACKAGE_{package}=y\n", text)
                for preferred, fallbacks in device.providers.items():
                    self.assertIn(f"CONFIG_PACKAGE_{preferred}=y\n", text)
                    for fallback in fallbacks:
                        self.assertIn(f"# CONFIG_PACKAGE_{fallback} is not set\n", text)
                verify_config.verify(self.source, name)

    def test_tailscale_only_on_ea0326gmp(self):
        self.assertIn("CONFIG_PACKAGE_tailscale=y\n", self.generate("nokia_ea0326gmp"))
        self.assertIn("CONFIG_PACKAGE_luci-app-tailscale-community=y\n", self.generate("nokia_ea0326gmp"))
        self.assertNotIn("tailscale", self.generate("phicomm_k2p"))

    def test_clash_and_mosdns_are_removed(self):
        for name in configure.DEVICES:
            with self.subTest(device=name):
                text = self.generate(name)
                self.assertIn("# CONFIG_PACKAGE_luci-app-openclash is not set\n", text)
                self.assertIn("# CONFIG_PACKAGE_luci-app-mosdns is not set\n", text)
                self.assertIn("# CONFIG_PACKAGE_v2ray-geoip is not set\n", text)
                package_list = [line for line in text.splitlines() if "DEVICE_PACKAGES" in line][0]
                self.assertNotIn("clash", package_list)

    def test_k2p_keeps_device_removals(self):
        text = self.generate("phicomm_k2p")
        self.assertIn("-uboot-envtools", text)
        self.assertIn("CONFIG_PACKAGE_kmod-mt7615e=m\n", text)

    def test_guard_rejects_clash_after_defconfig(self):
        text = self.generate() + "CONFIG_PACKAGE_mihomo=m\n"
        (self.source / ".config").write_text(text)
        with self.assertRaisesRegex(ValueError, "Clash/MosDNS packages must not be built: mihomo"):
            verify_config.verify(self.source, "nokia_ea0326gmp")

    def test_guard_rejects_missing_device_package_after_defconfig(self):
        text = self.generate().replace("CONFIG_PACKAGE_libopenssl=y\n", "")
        (self.source / ".config").write_text(text)
        with self.assertRaisesRegex(ValueError, "not selected for compilation: libopenssl"):
            verify_config.verify(self.source, "nokia_ea0326gmp")

    def test_custom_apps_must_be_built_in(self):
        text = self.generate("phicomm_k2p").replace("CONFIG_PACKAGE_luci-app-vlmcsd=y",
                                                    "CONFIG_PACKAGE_luci-app-vlmcsd=m")
        (self.source / ".config").write_text(text)
        with self.assertRaisesRegex(ValueError, "required package is not built in: luci-app-vlmcsd"):
            verify_config.verify(self.source, "phicomm_k2p")

    def test_guard_rejects_base_and_device_provider_conflicts(self):
        text = self.generate()
        text = text.replace("CONFIG_PACKAGE_apk-openssl=y", "CONFIG_PACKAGE_apk-openssl=m")
        text = text.replace("# CONFIG_PACKAGE_apk-mbedtls is not set", "CONFIG_PACKAGE_apk-mbedtls=y")
        (self.source / ".config").write_text(text)
        with self.assertRaisesRegex(ValueError, "apk-mbedtls \\+ apk-openssl"):
            verify_config.verify(self.source, "nokia_ea0326gmp")

    def test_guard_requires_image_metadata(self):
        text = self.generate("phicomm_k2p").replace("CONFIG_JSON_OVERVIEW_IMAGE_INFO=y\n", "")
        (self.source / ".config").write_text(text)
        with self.assertRaisesRegex(ValueError, "profiles.json"):
            verify_config.verify(self.source, "phicomm_k2p")

    def test_unused_modular_fallback_is_not_an_install_conflict(self):
        text = self.generate().replace("# CONFIG_PACKAGE_wpad-basic-mbedtls is not set",
                                       "CONFIG_PACKAGE_wpad-basic-mbedtls=m")
        (self.source / ".config").write_text(text)
        verify_config.verify(self.source, "nokia_ea0326gmp")

    def test_guard_requires_generated_conflict_metadata(self):
        self.generate()
        (self.source / "tmp/.config-package.in").unlink()
        with self.assertRaisesRegex(ValueError, "conflict metadata is missing"):
            verify_config.verify(self.source, "nokia_ea0326gmp")

    def test_unknown_device_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported device"):
            self.generate("cmcc_rax3000m")


if __name__ == "__main__":
    unittest.main()
