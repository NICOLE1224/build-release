#!/usr/bin/env python3
"""Give the pinned VLMCSd package an APK-compatible numeric version.

Keep the source archive, source tag, build directory and hash unchanged.
Only the package metadata version changes from svn1113 to 1113.
"""
import sys
from pathlib import Path

makefile = Path(sys.argv[1]) / "Makefile"
text = makefile.read_text()
replacements = {
    "PKG_VERSION:=svn1113": "PKG_VERSION:=1113\nPKG_SOURCE_VERSION:=svn1113",
    "PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz":
        "PKG_SOURCE:=$(PKG_NAME)-$(PKG_SOURCE_VERSION).tar.gz\n"
        "PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)-$(PKG_SOURCE_VERSION)",
    "PKG_SOURCE_URL:=https://codeload.github.com/Wind4/vlmcsd/tar.gz/$(PKG_VERSION)?":
        "PKG_SOURCE_URL:=https://codeload.github.com/Wind4/vlmcsd/tar.gz/$(PKG_SOURCE_VERSION)?",
}
for original, replacement in replacements.items():
    if text.count(original) != 1:
        sys.exit(f"adapt-vlmcsd-service: unexpected pinned Makefile: {original}")
    text = text.replace(original, replacement, 1)
makefile.write_text(text, newline="\n")
