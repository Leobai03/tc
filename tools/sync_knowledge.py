#!/usr/bin/env python3
"""Synchronize canonical TC knowledge into installable Skill bundles."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ATOMS = ROOT / "知识库" / "原子库" / "atoms.jsonl"
CANONICAL_POSTS = ROOT / "知识库" / "公开内容索引" / "posts.jsonl"
CANONICAL_DICTIONARY = ROOT / "知识库" / "高频概念词典.md"
CANONICAL_PACKS = ROOT / "知识库" / "Skill知识包"
CANONICAL_CORE_SOURCES = ROOT / "知识库" / "核心参考源"
CANONICAL_EXTERNAL_SOURCES = ROOT / "知识库" / "外部理论库"

COPY_MAP = {
    CANONICAL_ATOMS: ROOT / "skills" / "tc-knowledge" / "references" / "atoms.jsonl",
    CANONICAL_POSTS: ROOT
    / "skills"
    / "tc-knowledge"
    / "references"
    / "public-posts.jsonl",
    CANONICAL_DICTIONARY: ROOT
    / "skills"
    / "tc-knowledge"
    / "references"
    / "concept-dictionary.md",
}


def expected_pairs() -> list[tuple[Path, Path]]:
    pairs = list(COPY_MAP.items())
    for source in sorted(CANONICAL_CORE_SOURCES.glob("*.md")):
        if source.name == "README.md":
            continue
        pairs.append(
            (source, ROOT / "skills" / "tc" / "references" / "core-sources" / source.name)
        )
        pairs.append(
            (
                source,
                ROOT
                / "skills"
                / "tc-knowledge"
                / "references"
                / "core-sources"
                / source.name,
            )
        )
    for source in sorted(CANONICAL_PACKS.glob("*.md")):
        pairs.append(
            (source, ROOT / "skills" / "tc" / "references" / "knowledge-packs" / source.name)
        )
        pairs.append(
            (
                source,
                ROOT
                / "skills"
                / "tc-knowledge"
                / "references"
                / "knowledge-packs"
                / source.name,
            )
        )
    for source in sorted(CANONICAL_EXTERNAL_SOURCES.glob("*.md")):
        pairs.append(
            (
                source,
                ROOT / "skills" / "tc" / "references" / "external-sources" / source.name,
            )
        )
        pairs.append(
            (
                source,
                ROOT
                / "skills"
                / "tc-knowledge"
                / "references"
                / "external-sources"
                / source.name,
            )
        )
    return pairs


def differences() -> list[str]:
    problems: list[str] = []
    for source, target in expected_pairs():
        if not source.is_file():
            problems.append(f"缺少知识真源：{source.relative_to(ROOT)}")
        elif not target.is_file():
            problems.append(f"缺少安装副本：{target.relative_to(ROOT)}")
        elif source.read_bytes() != target.read_bytes():
            problems.append(f"知识副本未同步：{target.relative_to(ROOT)}")
    return problems


def sync() -> None:
    for source, target in expected_pairs():
        if not source.is_file():
            raise FileNotFoundError(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(f"已同步 {len(expected_pairs())} 份知识安装副本")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只检查，不写入")
    args = parser.parse_args()
    if args.check:
        problems = differences()
        if problems:
            raise SystemExit("\n".join(problems))
        print("知识安装副本与真源一致")
    else:
        sync()


if __name__ == "__main__":
    main()
