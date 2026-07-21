#!/usr/bin/env python3
"""Validate TC versions, manifests, Skill metadata, and local links."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
FRONTMATTER = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
NAME = re.compile(r"^name:\s*([^\n]+)$", re.MULTILINE)
DESCRIPTION = re.compile(r"^description:\s*(?:\|\s*\n(?:[ \t]+.*\n?)+|[^\n]+)$", re.MULTILINE)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    errors: list[str] = []
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not SEMVER.fullmatch(version):
        errors.append(f"VERSION 不是标准语义化版本：{version!r}")

    codex = load_json(ROOT / ".codex-plugin" / "plugin.json")
    if codex.get("name") != "tc":
        errors.append("Codex plugin name 必须是 tc")
    if codex.get("version") != version:
        errors.append("Codex plugin version 与 VERSION 不一致")
    if codex.get("skills") != "./skills/":
        errors.append("Codex plugin skills 必须指向 ./skills/")

    marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    if marketplace.get("metadata", {}).get("version") != version:
        errors.append("Claude marketplace metadata.version 与 VERSION 不一致")

    skill_dirs = sorted(path.parent for path in (ROOT / "skills").glob("*/SKILL.md"))
    skill_names: list[str] = []
    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        text = skill_md.read_text(encoding="utf-8")
        frontmatter = FRONTMATTER.search(text)
        if frontmatter is None:
            errors.append(f"{skill_md.relative_to(ROOT)} 缺少合法 YAML frontmatter")
            continue
        frontmatter_text = frontmatter.group("body")
        name_match = NAME.search(frontmatter_text)
        if name_match is None:
            errors.append(f"{skill_md.relative_to(ROOT)} 缺少 name")
            continue
        name = name_match.group(1).strip().strip("'\"")
        skill_names.append(name)
        if name != skill_dir.name:
            errors.append(f"{skill_md.relative_to(ROOT)} 的 name 与目录名不一致")
        if DESCRIPTION.search(frontmatter_text) is None:
            errors.append(f"{skill_md.relative_to(ROOT)} 缺少 description")
        if not (skill_dir / "agents" / "openai.yaml").is_file():
            errors.append(f"{skill_dir.relative_to(ROOT)} 缺少 agents/openai.yaml")
        if "[TODO:" in text:
            errors.append(f"{skill_md.relative_to(ROOT)} 含未完成 TODO")

    plugins = marketplace.get("plugins", [])
    plugin_names = [plugin.get("name") for plugin in plugins]
    if sorted(plugin_names) != sorted(skill_names):
        errors.append(
            f"Claude 插件清单与 skills/ 不一致：plugins={plugin_names}, skills={skill_names}"
        )
    for plugin in plugins:
        if plugin.get("version") != version:
            errors.append(f"Claude plugin {plugin.get('name')} 的版本不一致")
        expected = f"./skills/{plugin.get('name')}"
        if plugin.get("skills") != [expected]:
            errors.append(f"Claude plugin {plugin.get('name')} 应指向 {expected}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    badge = re.search(r"badge/version-([0-9.]+)-", readme)
    if badge is None or badge.group(1) != version:
        errors.append("README 版本徽章与 VERSION 不一致")

    required_docs = (
        ROOT / "docs" / "新手入门.md",
        ROOT / "docs" / "工作原理.md",
        ROOT / "docs" / "真实示例.md",
        ROOT / "docs" / "releases" / f"v{version}.md",
    )
    for document in required_docs:
        if not document.is_file():
            errors.append(f"缺少必要说明文档：{document.relative_to(ROOT)}")

    required_readme_phrases = (
        "TC 到底是什么",
        "一次完整对话长什么样",
        "仓库里的文件夹都是干什么的",
        "新手入门说明书",
        "真实使用示例",
    )
    for phrase in required_readme_phrases:
        if phrase not in readme:
            errors.append(f"README 缺少必要说明：{phrase}")

    tc_skill = (ROOT / "skills" / "tc" / "SKILL.md").read_text(encoding="utf-8")
    tc_lite = (ROOT / "skills" / "tc" / "assets" / "tc-lite.txt").read_text(
        encoding="utf-8"
    )
    short_entry = (
        "在。把事情直接发过来，乱一点也没关系。"
        "我先帮你把问题重新说清楚。"
    )
    for label, content in (("TC 主 Skill", tc_skill), ("TC 轻量版", tc_lite)):
        if short_entry not in content:
            errors.append(f"{label} 缺少统一的极短入口文案")
        if "问题定义（草案）" not in content or "我只确认一个点" not in content:
            errors.append(f"{label} 缺少渐进式问题定义输出")
    if "已进入 TC。" in tc_skill or "已进入 TC。" in tc_lite:
        errors.append("TC 仍包含旧版长入口文案")

    markdown_files = [
        *ROOT.glob("*.md"),
        *(ROOT / "docs").glob("**/*.md"),
        *(ROOT / "tests").glob("**/*.md"),
        *(ROOT / "知识库").glob("**/*.md"),
        *(ROOT / "skills").glob("**/*.md"),
    ]
    for markdown in markdown_files:
        text = markdown.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            target = target.split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (markdown.parent / target).resolve()
            if not resolved.exists():
                errors.append(
                    f"{markdown.relative_to(ROOT)} 存在失效链接：{target}"
                )

    return errors


def main() -> None:
    errors = validate()
    if errors:
        print("TC 完整性校验失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    skill_count = len(list((ROOT / "skills").glob("*/SKILL.md")))
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    print(f"TC 校验通过：v{version}，{skill_count} 个 Skill")


if __name__ == "__main__":
    main()
