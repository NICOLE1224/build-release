#!/usr/bin/env python3
"""Adapt the pinned legacy LuCI app to X-WRT's package path and ACL checks."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
makefile = root / "Makefile"
text = makefile.read_text()
assert text.count("include ../../luci.mk") == 1, "unexpected LuCI include"
assert text.count("LUCI_DEPENDS:=+vlmcsd") == 1, "unexpected LuCI dependencies"
text = text.replace("include ../../luci.mk", "include $(TOPDIR)/feeds/luci/luci.mk")
text = text.replace("LUCI_DEPENDS:=+vlmcsd", "LUCI_DEPENDS:=+vlmcsd +luci-compat")
makefile.write_text(text, newline="\n")
controller = root / "luasrc/controller/vlmcsd.lua"
text = controller.read_text()
marker = '\tentry({"admin", "services", "vlmcsd"},'
assert text.count(marker) == 1, "unexpected VLMCSd controller"
text = text.replace(marker, '\tlocal page = entry({"admin", "services", "vlmcsd"},', 1)
text = text.replace('100).dependent = true', '100)\n\tpage.dependent = true\n\tpage.acl_depends = { "luci-app-vlmcsd" }', 1)
controller.write_text(text, newline="\n")
acl = root / "root/usr/share/rpcd/acl.d/luci-app-vlmcsd.json"
acl.parent.mkdir(parents=True, exist_ok=True)
acl.write_text(json.dumps({"luci-app-vlmcsd": {
    "description": "Grant access to the VLMCSd configuration",
    "read": {"uci": ["vlmcsd"], "file": {"/etc/vlmcsd.ini": ["read"]}},
    "write": {"uci": ["vlmcsd"], "file": {"/etc/vlmcsd.ini": ["write"]}},
}}, indent=2) + "\n", newline="\n")
