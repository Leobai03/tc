#!/usr/bin/env python3
"""Build individual TC Skill archives and one release bundle."""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def zip_skill(skill_dir: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_file():
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
        f"TC v{version}\n\n"
        "优先使用：npx -y skills add Leobai03/tc -g --all\n"
        "需要手动上传时，按需使用 skills/ 中的单个 ZIP。\n"
        "不知道用哪个，只安装 tc.zip 并输入 /tc。\n"
    )
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", instructions)
        archive.writestr("VERSION", f"{version}\n")
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
