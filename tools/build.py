#!/usr/bin/env python3
"""Build individual TC Skill archives and one release bundle."""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {"__pycache__", ".DS_Store"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def should_include(path: Path) -> bool:
    return not (
        any(part in IGNORED_PARTS for part in path.parts)
        or path.suffix in IGNORED_SUFFIXES
    )


def zip_skill(skill_dir: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_file() and should_include(path):
                archive.write(path, Path(skill_dir.name) / path.relative_to(skill_dir))


def build(output: Path) -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if output.exists():
        shutil.rmtree(output)
    skills_output = output / "skills"
    skills_output.mkdir(parents=True)

    built: list[Path] = []
    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        skill_dir = skill_md.parent
        target = skills_output / f"{skill_dir.name}.zip"
        zip_skill(skill_dir, target)
        built.append(target)
        print(f"built {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}")

    bundle = output / f"tc-suite-{version}.zip"
    instructions = (
        f"TC｜天策创业解题系统 v{version}\n\n"
        "它是干什么的：\n"
        "把一件讲不清、想不明白或推不动的创业问题直接交给 /tc。\n"
        "TC 会先帮你找到真正的问题，再给一个明确方案和可验证的第一步。\n\n"
        "推荐安装：\n"
        "npx -y skills add Leobai03/tc -g --all\n\n"
        "第一次使用：\n"
        "新开一个对话，输入 /tc，然后把真实情况直接说出来。\n\n"
        "手动安装：\n"
        "skills/tc.zip 是主入口；其他 ZIP 是专项能力。\n"
        "不知道选哪个时，只使用 tc.zip。\n\n"
        "完整说明：README.md 和 docs/ 文件夹。\n"
    )
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", instructions)
        archive.writestr("VERSION", f"{version}\n")
        for relative in (
            Path("README.md"),
            Path("LICENSE"),
            Path("docs/新手入门.md"),
            Path("docs/工作原理.md"),
            Path("docs/真实示例.md"),
        ):
            archive.write(ROOT / relative, relative)
        for path in built:
            archive.write(path, Path("skills") / path.name)
    print(f"built {bundle.relative_to(ROOT) if bundle.is_relative_to(ROOT) else bundle}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    build(args.output.resolve())


if __name__ == "__main__":
    main()
