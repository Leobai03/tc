#!/usr/bin/env python3
"""Save, restore, list, and summarize local TC startup state."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path.home() / ".tc" / "projects"
REQUIRED_FIELDS = ("project", "problem_definition", "decision", "next_action")
LIST_FIELDS = (
    "confirmed_facts",
    "rejected_directions",
    "assumptions",
    "evidence",
)
SAFE_SLUG = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff._-]+")


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def slug(value: str, fallback: str = "untitled") -> str:
    cleaned = SAFE_SLUG.sub("-", value.strip()).strip("-._")
    return cleaned[:80] or fallback


def root_path(raw: str | None) -> Path:
    return Path(raw).expanduser().resolve() if raw else DEFAULT_ROOT


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def unique_path(directory: Path, stem: str, suffix: str = ".md") -> Path:
    candidate = directory / f"{stem}{suffix}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def load_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"无法读取有效 JSON：{path}（{error}）") from error
    if not isinstance(payload, dict):
        raise SystemExit("payload 顶层必须是 JSON 对象")
    for field in REQUIRED_FIELDS:
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise SystemExit(f"缺少必填文字字段：{field}")
    for field in LIST_FIELDS:
        value = payload.get(field, [])
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise SystemExit(f"字段 {field} 必须是字符串数组")
        payload[field] = [item.strip() for item in value if item.strip()]
    return payload


def bullets(items: list[str], empty: str = "- 暂无") -> str:
    return "\n".join(f"- {item}" for item in items) if items else empty


def render_snapshot(payload: dict[str, Any], stamp: str) -> str:
    title = payload.get("title") or payload["project"]
    return f"""# {title}

- 保存时间（UTC）：{stamp}
- 项目：{payload['project']}
- 来源 Skill：{payload.get('source_skill', 'tc')}
- 状态：{payload.get('status', 'active')}

## 问题定义

{payload['problem_definition'].strip()}

## 已确认事实

{bullets(payload['confirmed_facts'])}

## 当前决定

{payload['decision'].strip()}

## 必须接受的代价

{payload.get('tradeoff', '').strip() or '暂未记录'}

## 本轮明确不做

{bullets(payload['rejected_directions'])}

## 待验证假设

{bullets(payload['assumptions'])}

## 下一步

{payload['next_action'].strip()}

## 有效标准

{payload.get('success_metric', '').strip() or '暂未记录'}

## 已有证据

{bullets(payload['evidence'])}

## 下次建议入口

{payload.get('next_skill', 'tc')}
"""


def snapshot_files(project_dir: Path) -> list[Path]:
    sessions = project_dir / "sessions"
    return sorted(sessions.glob("*.md")) if sessions.is_dir() else []


def save_command(args: argparse.Namespace) -> None:
    payload = load_payload(Path(args.payload).expanduser())
    root = root_path(args.root)
    project_dir = root / slug(payload["project"], "project")
    stamp = now_stamp()
    title = slug(str(payload.get("title") or payload["project"]))
    content = render_snapshot(payload, stamp)
    snapshot = unique_path(project_dir / "sessions", f"{stamp}-{title}")
    current = project_dir / "current.md"
    atomic_write(snapshot, content)
    atomic_write(current, content)
    print(json.dumps({"saved": str(snapshot), "current": str(current)}, ensure_ascii=False))


def list_command(args: argparse.Namespace) -> None:
    root = root_path(args.root)
    results: list[dict[str, Any]] = []
    if root.is_dir():
        for project_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            files = snapshot_files(project_dir)
            results.append(
                {
                    "project": project_dir.name,
                    "snapshots": len(files),
                    "latest": str(files[-1]) if files else None,
                }
            )
    print(json.dumps(results, ensure_ascii=False, indent=2))


def restore_command(args: argparse.Namespace) -> None:
    project_dir = root_path(args.root) / slug(args.project, "project")
    files = snapshot_files(project_dir)
    if not files:
        raise SystemExit(f"没有找到项目存档：{args.project}")
    latest = files[-1]
    print(json.dumps({"path": str(latest), "content": latest.read_text(encoding="utf-8")}, ensure_ascii=False))


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\n\n(?P<body>.*?)(?=\n## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("body").strip() if match else "暂未记录"


def report_command(args: argparse.Namespace) -> None:
    project_dir = root_path(args.root) / slug(args.project, "project")
    files = snapshot_files(project_dir)
    if len(files) < 2 and not args.force:
        raise SystemExit("阶段报告至少需要两次存档；如确需单次汇总，请增加 --force")
    if not files:
        raise SystemExit(f"没有找到项目存档：{args.project}")

    entries: list[str] = []
    for path in files:
        content = path.read_text(encoding="utf-8")
        entries.append(
            f"### {path.stem}\n\n"
            f"**问题：** {section(content, '问题定义')}\n\n"
            f"**决定：** {section(content, '当前决定')}\n\n"
            f"**下一步：** {section(content, '下一步')}\n\n"
            f"**证据：**\n{section(content, '已有证据')}"
        )
    stamp = now_stamp()
    content = (
        f"# {args.project}｜TC 阶段报告\n\n"
        f"- 生成时间（UTC）：{stamp}\n"
        f"- 存档数量：{len(files)}\n\n"
        "## 时间线\n\n"
        + "\n\n".join(entries)
        + "\n\n## 下一轮使用方式\n\n"
        "把这份报告交给 `/tc`，重点判断哪些假设已被证实或推翻，以及下一阶段唯一问题。\n"
    )
    target = unique_path(project_dir / "reports", f"{stamp}-阶段报告")
    atomic_write(target, content)
    print(json.dumps({"report": str(target), "snapshots": len(files)}, ensure_ascii=False))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", help="覆盖默认保存根目录（用于测试或自定义）")
    commands = result.add_subparsers(dest="command", required=True)

    save_parser = commands.add_parser("save", help="保存一份结构化创业状态")
    save_parser.add_argument("--payload", required=True, help="UTF-8 JSON 文件路径")
    save_parser.set_defaults(func=save_command)

    list_parser = commands.add_parser("list", help="列出所有本地项目存档")
    list_parser.set_defaults(func=list_command)

    restore_parser = commands.add_parser("restore", help="恢复某项目最近一次存档")
    restore_parser.add_argument("--project", required=True)
    restore_parser.set_defaults(func=restore_command)

    report_parser = commands.add_parser("report", help="生成某项目阶段报告")
    report_parser.add_argument("--project", required=True)
    report_parser.add_argument("--force", action="store_true")
    report_parser.set_defaults(func=report_command)
    return result


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
