#!/usr/bin/env python3
"""Search and validate TC's bundled public knowledge."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES = SKILL_ROOT / "references"
ATOMS = REFERENCES / "atoms.jsonl"
POSTS = REFERENCES / "public-posts.jsonl"
PACKS = REFERENCES / "knowledge-packs"
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


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number} 不是合法 JSON：{error}") from error
    return rows


def query_tokens(query: str) -> list[str]:
    normalized = query.strip().lower()
    tokens = [part for part in re.split(r"[\s,，。；;、/]+", normalized) if part]
    if normalized and normalized not in tokens:
        tokens.insert(0, normalized)
    compact = re.sub(r"\s+", "", normalized)
    if len(compact) >= 4:
        tokens.extend(compact[index : index + 2] for index in range(len(compact) - 1))
    return list(dict.fromkeys(tokens))


def score_text(query: str, text: str) -> int:
    haystack = text.lower()
    normalized = query.strip().lower()
    score = 8 if normalized and normalized in haystack else 0
    for token in query_tokens(query):
        if token in haystack:
            score += 3 if len(token) > 1 else 1
    return score


def search(query: str, scope: str, limit: int) -> list[dict]:
    results: list[dict] = []
    if scope in {"all", "atoms"}:
        for atom in load_jsonl(ATOMS):
            text = " ".join(
                [
                    atom["id"],
                    atom["knowledge"],
                    atom["original"],
                    atom["boundary"],
                    " ".join(atom["topics"]),
                ]
            )
            score = score_text(query, text)
            if score:
                results.append({"kind": "atom", "score": score, **atom})
    if scope in {"all", "posts"}:
        for post in load_jsonl(POSTS):
            score = score_text(query, post["text"])
            if score:
                results.append({"kind": "post", "score": score, **post})
    if scope in {"all", "packs"}:
        for path in sorted(PACKS.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            score = score_text(query, f"{path.stem} {content}")
            if score:
                results.append(
                    {
                        "kind": "pack",
                        "score": score,
                        "name": path.stem,
                        "path": f"knowledge-packs/{path.name}",
                        "preview": re.sub(r"\s+", " ", content)[:260],
                    }
                )
    def relevance(row: dict) -> tuple:
        return (
            -row["score"],
            -int(row.get("engagement", 0)),
            row.get("date", ""),
            row.get("id", row.get("name", "")),
        )

    results.sort(key=relevance)
    if scope != "all":
        return results[:limit]

    # Default results are intentionally assembled, not just globally ranked:
    # one method pack gives context, up to three atoms give traceable rules,
    # and one raw post gives historical evidence. Users who only want history
    # can explicitly use --scope posts.
    groups = {
        kind: [row for row in results if row["kind"] == kind]
        for kind in ("pack", "atom", "post")
    }
    chosen: list[dict] = []
    if groups["pack"] and len(chosen) < limit:
        chosen.append(groups["pack"].pop(0))
    while groups["atom"] and len(chosen) < min(limit, 4):
        chosen.append(groups["atom"].pop(0))
    if groups["post"] and len(chosen) < limit:
        selected_source_ids = {
            row["url"].rstrip("/").rsplit("/", 1)[-1]
            for row in chosen
            if row["kind"] == "atom"
        }
        source_index = next(
            (
                index
                for index, row in enumerate(groups["post"])
                if row["id"] in selected_source_ids
            ),
            0,
        )
        chosen.append(groups["post"].pop(source_index))
    leftovers = sorted(
        groups["pack"] + groups["atom"] + groups["post"], key=relevance
    )
    chosen.extend(leftovers[: limit - len(chosen)])
    return chosen


def markdown_results(query: str, rows: list[dict]) -> str:
    if not rows:
        return f"没有找到与“{query}”直接相关的 TC 知识。"
    lines = [f"找到 {len(rows)} 条与“{query}”最相关的结果：", ""]
    for row in rows:
        if row["kind"] == "atom":
            lines.extend(
                [
                    f"### [知识原子] {row['id']}",
                    "",
                    row["knowledge"],
                    "",
                    f"- 来源：{row['date']} · {row['url']}",
                    f"- 等级：{row['level']} · 证据 {row['evidence_grade']}",
                    f"- 边界：{row['boundary']}",
                    "",
                ]
            )
        elif row["kind"] == "post":
            preview = re.sub(r"\s+", " ", row["text"]).strip()[:300]
            lines.extend(
                [
                    f"### [历史原推] {row['date']}",
                    "",
                    preview + ("……" if len(row["text"]) > 300 else ""),
                    "",
                    f"- 原链接：{row['url']}",
                    f"- 互动快照：{row['engagement']}（只代表归档时）",
                    "- 状态：历史公开表达，不自动代表当前状态或 TC 认可",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"### [知识包] {row['name']}",
                    "",
                    row["preview"] + "……",
                    "",
                    f"- 文件：{row['path']}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip()


def validate() -> list[str]:
    errors: list[str] = []
    atom_ids: set[str] = set()
    post_ids: set[str] = set()
    try:
        atoms = load_jsonl(ATOMS)
        posts = load_jsonl(POSTS)
    except (OSError, ValueError) as error:
        return [str(error)]
    for atom in atoms:
        missing = ATOM_REQUIRED - set(atom)
        if missing:
            errors.append(f"知识原子缺少字段：{sorted(missing)}")
            continue
        if atom["id"] in atom_ids:
            errors.append(f"知识原子 ID 重复：{atom['id']}")
        atom_ids.add(atom["id"])
        if atom["object_type"] not in {"QST", "CON", "OPI", "CAS", "SOL"}:
            errors.append(f"知识原子 {atom['id']} 的 object_type 无效")
        if atom["level"] not in {"L0", "L1", "L2", "L3"}:
            errors.append(f"知识原子 {atom['id']} 的 level 无效")
        if atom["evidence_grade"] not in {"A", "B", "C", "D"}:
            errors.append(f"知识原子 {atom['id']} 的 evidence_grade 无效")
    for post in posts:
        missing = {"id", "date", "text", "url", "engagement", "status"} - set(post)
        if missing:
            errors.append(f"公开推文缺少字段：{sorted(missing)}")
            continue
        if post["id"] in post_ids:
            errors.append(f"公开推文 ID 重复：{post['id']}")
        post_ids.add(post["id"])
        if post["status"] != "historical-public":
            errors.append(f"公开推文 {post['id']} 的状态不正确")
    packs = list(PACKS.glob("*.md"))
    if not packs:
        errors.append("没有安装任何 TC 专项知识包")
    return errors


def stats() -> dict:
    atoms = load_jsonl(ATOMS)
    posts = load_jsonl(POSTS)
    topics = Counter(topic for atom in atoms for topic in atom["topics"])
    return {
        "atoms": len(atoms),
        "posts": len(posts),
        "packs": len(list(PACKS.glob("*.md"))),
        "post_date_range": [min(row["date"] for row in posts), max(row["date"] for row in posts)]
        if posts
        else [],
        "levels": dict(Counter(atom["level"] for atom in atoms)),
        "top_topics": topics.most_common(12),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--scope", choices=["all", "atoms", "posts", "packs"], default="all")
    search_parser.add_argument("--limit", type=int, default=5)
    search_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    subparsers.add_parser("stats")
    subparsers.add_parser("validate")
    args = parser.parse_args()

    if args.command == "search":
        if args.limit < 1 or args.limit > 50:
            raise SystemExit("--limit 必须在 1 到 50 之间")
        rows = search(args.query, args.scope, args.limit)
        if args.format == "json":
            json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
            print()
        else:
            print(markdown_results(args.query, rows))
    elif args.command == "stats":
        json.dump(stats(), sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        errors = validate()
        if errors:
            print("TC 知识库校验失败：", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            raise SystemExit(1)
        summary = stats()
        print(
            f"TC 知识库校验通过：{summary['posts']} 条公开原推，"
            f"{summary['atoms']} 条知识原子，{summary['packs']} 个知识包"
        )


if __name__ == "__main__":
    main()
