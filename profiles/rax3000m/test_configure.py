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


class DevicePackagesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name)
        feed = self.source / "feeds/x/rom/lede"
        feed.mkdir(parents=True)
        lines = ["CONFIG_TARGET_PER_DEVICE_ROOTFS=y", "CONFIG_TARGET_MULTI_PROFILE=y",
                 "CONFIG_PACKAGE_luci-app-openclash=m", "CONFIG_PACKAGE_libopenssl=y",
                 "CONFIG_PACKAGE_input-support=m", "CONFIG_PACKAGE_printer-support=m",
                 "CONFIG_PACKAGE_unrelated-device-package=m",
                 "CONFIG_PACKAGE_wpad-basic-mbedtls=m"]
        for device in sorted(configure.DEVICES):
            lines += [f"CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_{device}=y",
                      f'CONFIG_TARGET_DEVICE_PACKAGES_mediatek_filogic_DEVICE_{device}='
                      '"luci-app-openclash libopenssl -wpad-basic-mbedtls"']
        (feed / "config.mediatek-filogic-test").write_text("\n".join(lines) + "\n")

    def generate(self, device="cmcc_rax3000m"):
        configure.configure(self.source, "26.10_b202609302026", device)
        return (self.source / ".config").read_text()

    def test_device_modules_are_built_and_unrelated_modules_are_omitted(self):
        for device in sorted(configure.DEVICES):
            with self.subTest(device=device):
                text = self.generate(device)
                self.assertIn("CONFIG_PACKAGE_luci-app-openclash=m\n", text)
                self.assertIn("CONFIG_PACKAGE_libopenssl=y\n", text)
                self.assertIn("CONFIG_PACKAGE_input-support=m\n", text)
                self.assertIn("CONFIG_PACKAGE_printer-support=m\n", text)
                self.assertNotIn("CONFIG_PACKAGE_unrelated-device-package=", text)
                self.assertNotIn("CONFIG_PACKAGE_wpad-basic-mbedtls=", text)
                verify_config.verify(self.source, device)

    def test_guard_rejects_missing_device_package_after_defconfig(self):
        text = self.generate().replace("CONFIG_PACKAGE_luci-app-openclash=m\n", "")
        (self.source / ".config").write_text(text)
        with self.assertRaisesRegex(ValueError, "not selected for compilation: luci-app-openclash"):
            verify_config.verify(self.source, "cmcc_rax3000m")

    def test_custom_apps_must_be_built_in(self):
        text = self.generate().replace("CONFIG_PACKAGE_luci-app-mosdns=y", "CONFIG_PACKAGE_luci-app-mosdns=m")
        (self.source / ".config").write_text(text)
        with self.assertRaisesRegex(ValueError, "required package is not built in: luci-app-mosdns"):
            verify_config.verify(self.source, "cmcc_rax3000m")


if __name__ == "__main__":
    unittest.main()
