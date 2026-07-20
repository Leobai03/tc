#!/usr/bin/env python3
"""Synchronize the TC semantic version across public manifests."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def prepare(raw_version: str) -> None:
    version = raw_version.removeprefix("v")
    if not SEMVER.fullmatch(version):
        raise SystemExit(f"版本号必须符合 MAJOR.MINOR.PATCH：{raw_version}")

    codex_path = ROOT / ".codex-plugin" / "plugin.json"
    codex = json.loads(codex_path.read_text(encoding="utf-8"))
    codex["version"] = version
    codex_path.write_text(
        json.dumps(codex, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    claude_path = ROOT / ".claude-plugin" / "marketplace.json"
    claude = json.loads(claude_path.read_text(encoding="utf-8"))
    claude.setdefault("metadata", {})["version"] = version
    for plugin in claude.get("plugins", []):
        plugin["version"] = version
    claude_path.write_text(
        json.dumps(claude, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme, count = re.subn(
        r"(badge/version-)[0-9.]+(-45C2FF\.svg)",
        rf"\g<1>{version}\g<2>",
        readme,
        count=1,
    )
    if count != 1:
        raise SystemExit("README 中没有找到唯一版本徽章")
    readme_path.write_text(readme, encoding="utf-8")
    (ROOT / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    print(f"TC 公开版本已同步为 v{version}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("version")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.version)


if __name__ == "__main__":
    main()
