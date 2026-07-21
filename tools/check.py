#!/usr/bin/env python3
"""Validate TC versions, manifests, Skill metadata, and local links."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from sync_knowledge import differences as knowledge_sync_differences


ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
FRONTMATTER = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
NAME = re.compile(r"^name:\s*([^\n]+)$", re.MULTILINE)
DESCRIPTION = re.compile(r"^description:\s*(?:\|\s*\n(?:[ \t]+.*\n?)+|[^\n]+)$", re.MULTILINE)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ATOM_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ATOM_REQUIRED = {
    "id",
    "knowledge",
    "original",
    "url",
    "date",
    "topics",
    "skills",
    "type",
    "object_type",
    "level",
    "evidence_grade",
    "confidence",
    "status",
    "visibility",
    "source_id",
    "boundary",
}


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
        ROOT / "docs" / "DBS架构深度调研.md",
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

    atoms_path = ROOT / "知识库" / "原子库" / "atoms.jsonl"
    atom_readme_path = ROOT / "知识库" / "原子库" / "README.md"
    atom_ids: set[str] = set()
    atom_count = 0
    if not atoms_path.is_file():
        errors.append("缺少公开知识原子库：知识库/原子库/atoms.jsonl")
    else:
        for line_number, raw_line in enumerate(
            atoms_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw_line.strip():
                continue
            atom_count += 1
            try:
                atom = json.loads(raw_line)
            except json.JSONDecodeError as error:
                errors.append(f"知识原子第 {line_number} 行不是合法 JSON：{error}")
                continue
            missing = ATOM_REQUIRED - set(atom)
            if missing:
                errors.append(f"知识原子第 {line_number} 行缺少字段：{sorted(missing)}")
                continue
            atom_id = atom["id"]
            atom_url = atom["url"]
            if not isinstance(atom_id, str) or not atom_id.strip():
                errors.append(f"知识原子第 {line_number} 行的 id 必须是非空字符串")
                continue
            if not isinstance(atom_url, str):
                errors.append(f"知识原子 {atom_id} 的 url 必须是字符串")
                continue
            if atom_id in atom_ids:
                errors.append(f"知识原子 ID 重复：{atom_id}")
            atom_ids.add(atom_id)
            if not atom_url.startswith("https://x.com/Leobai825/status/"):
                errors.append(f"知识原子 {atom_id} 的公开来源 URL 不符合当前范围")
            if not ATOM_DATE.fullmatch(str(atom["date"])):
                errors.append(f"知识原子 {atom_id} 的日期格式不正确")
            if atom["status"] != "historical-public":
                errors.append(f"知识原子 {atom_id} 必须标记为 historical-public")
            if atom["visibility"] != "public":
                errors.append(f"知识原子 {atom_id} 必须标记为 public")
            if atom["source_id"] != "tiance-x-archive":
                errors.append(f"知识原子 {atom_id} 的 source_id 不在当前公开范围")
            if atom["object_type"] not in {"QST", "CON", "OPI", "CAS", "SOL"}:
                errors.append(f"知识原子 {atom_id} 的 object_type 无效")
            if atom["level"] not in {"L0", "L1", "L2", "L3"}:
                errors.append(f"知识原子 {atom_id} 的 level 无效")
            if atom["evidence_grade"] not in {"A", "B", "C", "D"}:
                errors.append(f"知识原子 {atom_id} 的 evidence_grade 无效")
            for field in ("knowledge", "original", "boundary"):
                if not isinstance(atom[field], str) or not atom[field].strip():
                    errors.append(f"知识原子 {atom_id} 的 {field} 不能为空")
            for field in ("topics", "skills"):
                if (
                    not isinstance(atom[field], list)
                    or not atom[field]
                    or any(not isinstance(item, str) for item in atom[field])
                ):
                    errors.append(f"知识原子 {atom_id} 的 {field} 必须是非空字符串数组")
            if isinstance(atom["skills"], list) and all(
                isinstance(item, str) for item in atom["skills"]
            ):
                unknown_skills = set(atom["skills"]) - set(skill_names)
                if unknown_skills:
                    errors.append(f"知识原子 {atom_id} 引用了未知 Skill：{sorted(unknown_skills)}")
    if atom_count == 0:
        errors.append("公开知识原子库不能为空")
    if not atom_readme_path.is_file():
        errors.append("缺少知识原子库说明：知识库/原子库/README.md")
    else:
        atom_readme = atom_readme_path.read_text(encoding="utf-8")
        stated_count = re.search(r"当前共有 \*\*(\d+) 条\*\*原子", atom_readme)
        if stated_count is None or int(stated_count.group(1)) != atom_count:
            errors.append("知识原子库 README 的数量与 atoms.jsonl 不一致")
    pack_dir = ROOT / "知识库" / "Skill知识包"
    packs = sorted(pack_dir.glob("*.md"))
    if not packs:
        errors.append("缺少 TC 专项知识包")
    else:
        packed_text = "\n".join(path.read_text(encoding="utf-8") for path in packs)
        for atom_id in atom_ids:
            if atom_id not in packed_text:
                errors.append(f"专项知识包没有引用知识原子：{atom_id}")

    posts_path = ROOT / "知识库" / "公开内容索引" / "posts.jsonl"
    posts_readme_path = ROOT / "知识库" / "公开内容索引" / "README.md"
    post_ids: set[str] = set()
    post_count = 0
    if not posts_path.is_file():
        errors.append("缺少公开原创内容索引")
    else:
        for line_number, raw_line in enumerate(
            posts_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw_line.strip():
                continue
            post_count += 1
            try:
                post = json.loads(raw_line)
            except json.JSONDecodeError as error:
                errors.append(f"公开内容第 {line_number} 行不是合法 JSON：{error}")
                continue
            missing = {
                "id",
                "date",
                "text",
                "likes",
                "reposts",
                "engagement",
                "url",
                "status",
            } - set(post)
            if missing:
                errors.append(f"公开内容第 {line_number} 行缺少字段：{sorted(missing)}")
                continue
            post_id = str(post["id"])
            if post_id in post_ids:
                errors.append(f"公开内容 ID 重复：{post_id}")
            post_ids.add(post_id)
            if post["url"] != f"https://x.com/Leobai825/status/{post_id}":
                errors.append(f"公开内容 {post_id} 的 URL 不正确")
            if post["status"] != "historical-public":
                errors.append(f"公开内容 {post_id} 必须标记为 historical-public")
            if not ATOM_DATE.fullmatch(str(post["date"])):
                errors.append(f"公开内容 {post_id} 的日期格式不正确")
            if not isinstance(post["text"], str) or not post["text"].strip():
                errors.append(f"公开内容 {post_id} 正文为空")
    if post_count == 0:
        errors.append("公开原创内容索引不能为空")
    if not posts_readme_path.is_file():
        errors.append("缺少公开原创内容索引说明")
    else:
        posts_readme = posts_readme_path.read_text(encoding="utf-8")
        stated_posts = re.search(r"当前共有 \*\*(\d+) 条\*\*", posts_readme)
        if stated_posts is None or int(stated_posts.group(1)) != post_count:
            errors.append("公开内容索引 README 的数量与 posts.jsonl 不一致")

    source_registry_path = ROOT / "知识库" / "来源登记.example.json"
    if not source_registry_path.is_file():
        errors.append("缺少公开来源登记示例")
    else:
        source_registry = load_json(source_registry_path)
        source_ids = [source.get("id") for source in source_registry.get("sources", [])]
        if len(source_ids) != len(set(source_ids)):
            errors.append("来源登记存在重复 ID")
        if "tiance-x-archive" not in source_ids:
            errors.append("来源登记缺少 tiance-x-archive")
        source_text = source_registry_path.read_text(encoding="utf-8")
        if "/Users/" in source_text or "xcnkl208r114" in source_text:
            errors.append("公开来源登记包含本地绝对路径或私有飞书地址")

    errors.extend(knowledge_sync_differences())

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
