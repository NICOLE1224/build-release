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
                 "CONFIG_PACKAGE_apk-mbedtls=m", "CONFIG_PACKAGE_apk-openssl=m",
                 "CONFIG_PACKAGE_wpad-openssl=m",
                 "CONFIG_PACKAGE_wpad-basic-mbedtls=m"]
        for device in sorted(configure.DEVICES):
            lines += [f"CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_{device}=y",
                      f'CONFIG_TARGET_DEVICE_PACKAGES_mediatek_filogic_DEVICE_{device}='
                      '"luci-app-openclash libopenssl apk-openssl wpad-openssl"']
        (feed / "config.mediatek-filogic-test").write_text("\n".join(lines) + "\n")
        metadata = self.source / "tmp/.config-package.in"
        metadata.parent.mkdir()
        metadata.write_text(
            "config PACKAGE_apk-mbedtls\n"
            "\tdepends on m || (PACKAGE_apk-openssl != y)\n"
            "config PACKAGE_wpad-openssl\n"
            "\tdepends on m || (PACKAGE_wpad-basic-mbedtls != y)\n"
        )

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
                self.assertIn("CONFIG_PACKAGE_apk-openssl=y\n", text)
                self.assertIn("CONFIG_PACKAGE_wpad-openssl=y\n", text)
                self.assertIn("# CONFIG_PACKAGE_apk-mbedtls is not set\n", text)
                self.assertIn("# CONFIG_PACKAGE_wpad-basic-mbedtls is not set\n", text)
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

    def test_guard_rejects_base_and_device_provider_conflicts(self):
        text = self.generate()
        for preferred, fallback in configure.IMAGE_PROVIDERS.items():
            text = text.replace(f"CONFIG_PACKAGE_{preferred}=y", f"CONFIG_PACKAGE_{preferred}=m")
            text = text.replace(f"# CONFIG_PACKAGE_{fallback} is not set", f"CONFIG_PACKAGE_{fallback}=y")
        (self.source / ".config").write_text(text)
        with self.assertRaisesRegex(ValueError, "conflicting packages in root filesystem") as error:
            verify_config.verify(self.source, "cmcc_rax3000m")
        self.assertIn("apk-mbedtls + apk-openssl", str(error.exception))
        self.assertIn("wpad-basic-mbedtls + wpad-openssl", str(error.exception))

    def test_guard_checks_other_conflicts_and_device_removals(self):
        metadata = self.source / "tmp/.config-package.in"
        metadata.write_text("config PACKAGE_example-a\n\tdepends on m || (PACKAGE_example-b != y)\n")
        values = {"CONFIG_PACKAGE_example-a": "y"}
        with self.assertRaisesRegex(ValueError, "example-a \\+ example-b"):
            verify_config.verify_install_conflicts(values, {"example-b"}, set(), metadata)
        verify_config.verify_install_conflicts(values, {"example-b"}, {"example-a"}, metadata)

    def test_guard_requires_generated_conflict_metadata(self):
        self.generate()
        (self.source / "tmp/.config-package.in").unlink()
        with self.assertRaisesRegex(ValueError, "conflict metadata is missing"):
            verify_config.verify(self.source, "cmcc_rax3000m")


if __name__ == "__main__":
    unittest.main()
