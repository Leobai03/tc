#!/usr/bin/env python3
"""Search and validate TC's bundled public knowledge."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES = SKILL_ROOT / "references"
ATOMS = REFERENCES / "atoms.jsonl"
POSTS = REFERENCES / "public-posts.jsonl"
PACKS = REFERENCES / "knowledge-packs"
CORE_SOURCES = REFERENCES / "core-sources"
EXTERNAL_SOURCES = REFERENCES / "external-sources"
DBS_SOURCE_CARD = EXTERNAL_SOURCES / "dbs-books.md"
DBS_REPOSITORY = "https://github.com/dontbesilent2025/dbskill"
DBS_MARKDOWN_URL = (
    "https://raw.githubusercontent.com/dontbesilent2025/dbskill/"
    "main/books/dontbesilent-%E5%BC%80%E6%BA%90%E6%8E%A8%E6%96%87%E9%9B%86.md"
)
DBS_LICENSE_URL = (
    "https://raw.githubusercontent.com/dontbesilent2025/dbskill/main/LICENSE"
)
DBS_FILENAME = "dontbesilent-开源推文集.md"
DBS_ENV_PATH = "TC_DBS_BOOKS_PATH"
DBS_RECORD_HEADING = re.compile(
    r"^## (?P<date>\d{4}-\d{2}-\d{2}) · (?P<post_type>.+)$", re.MULTILINE
)
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
CANDIDATE_REQUIRED_TEXT = {
    "problem",
    "hypothesis",
    "scenario",
    "action",
    "success_metric",
    "counterexample",
    "boundary",
    "source_type",
}
CANDIDATE_SOURCE_REQUIRED = {"source_id", "license", "commercial_use"}


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


def load_json_object(path: str | Path) -> dict:
    source = Path(path).expanduser()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"无法读取候选知识 JSON：{source}（{error}）") from error
    if not isinstance(payload, dict):
        raise ValueError("候选知识 payload 顶层必须是 JSON 对象")
    return payload


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


def default_dbs_cache_dir() -> Path:
    root = Path(os.environ.get("TC_HOME", str(Path.home() / ".tc"))).expanduser()
    return root / "external" / "dbs-books"


def default_candidate_dir() -> Path:
    root = Path(os.environ.get("TC_HOME", str(Path.home() / ".tc"))).expanduser()
    return root / "knowledge-candidates"


def resolve_dbs_markdown(
    explicit_path: str | Path | None = None, cache_dir: str | Path | None = None
) -> Path:
    candidate = explicit_path or os.environ.get(DBS_ENV_PATH)
    if candidate:
        path = Path(candidate).expanduser()
        return path / DBS_FILENAME if path.is_dir() else path
    root = Path(cache_dir).expanduser() if cache_dir else default_dbs_cache_dir()
    return root / DBS_FILENAME


def parse_dbs_books(text: str) -> list[dict]:
    """Parse the public DBS Markdown corpus without copying it into TC."""
    headings = list(DBS_RECORD_HEADING.finditer(text))
    rows: list[dict] = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        block = text[heading.start() : end]
        url_match = re.search(r"^原帖：\[(https://x\.com/[^\]]+)\]", block, re.MULTILINE)
        metadata_match = re.search(r"^主题：(.+?)｜表达：(.+)$", block, re.MULTILINE)
        tags_match = re.search(r"^标签：(.+)$", block, re.MULTILINE)
        if not (url_match and metadata_match and tags_match):
            raise ValueError(f"DBS Markdown 记录格式不完整：{heading.group(0)}")

        quoted_lines: list[str] = []
        for raw_line in block.splitlines()[1:]:
            if raw_line.startswith("原帖："):
                break
            if raw_line == ">":
                quoted_lines.append("")
            elif raw_line.startswith("> "):
                quoted_lines.append(raw_line[2:])
        body = "\n".join(quoted_lines).strip()
        tags = [
            item.strip()
            for item in re.split(r"[、,，]", tags_match.group(1))
            if item.strip()
        ]
        url = url_match.group(1)
        rows.append(
            {
                "kind": "external-post",
                "source_id": "dbs-books",
                "id": url.rstrip("/").rsplit("/", 1)[-1],
                "date": heading.group("date"),
                "post_type": heading.group("post_type").strip(),
                "text": body,
                "url": url,
                "theme": metadata_match.group(1).strip(),
                "expression": metadata_match.group(2).strip(),
                "tags": tags,
                "evidence_grade": "C",
                "license": "CC BY-NC 4.0",
                "status": "external-view",
            }
        )
    return rows


def load_dbs_books(
    explicit_path: str | Path | None = None, cache_dir: str | Path | None = None
) -> tuple[Path, list[dict]]:
    path = resolve_dbs_markdown(explicit_path, cache_dir)
    if not path.is_file():
        raise FileNotFoundError(
            f"没有找到 DBS Markdown：{path}。先运行 external-sync --source dbs-books "
            "--accept-license，或通过 --source-path 指定已下载文件。"
        )
    return path, parse_dbs_books(path.read_text(encoding="utf-8"))


def search_dbs_books(
    query: str,
    limit: int,
    explicit_path: str | Path | None = None,
    cache_dir: str | Path | None = None,
) -> list[dict]:
    _, rows = load_dbs_books(explicit_path, cache_dir)
    results: list[dict] = []
    for row in rows:
        score = (
            score_text(query, " ".join(row["tags"])) * 5
            + score_text(query, f"{row['theme']} {row['expression']}") * 3
            + score_text(query, row["text"])
        )
        if score:
            results.append({**row, "score": score})
    results.sort(key=lambda row: row["date"], reverse=True)
    results.sort(key=lambda row: row["score"], reverse=True)
    return results[:limit]


def normalize_candidate(payload: dict) -> dict:
    missing = CANDIDATE_REQUIRED_TEXT - set(payload)
    if missing:
        raise ValueError(f"候选知识缺少字段：{sorted(missing)}")
    for field in CANDIDATE_REQUIRED_TEXT:
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise ValueError(f"候选知识字段 {field} 必须是非空字符串")

    evidence = payload.get("evidence", [])
    if not isinstance(evidence, list) or any(
        not isinstance(item, str) for item in evidence
    ):
        raise ValueError("候选知识 evidence 必须是字符串数组")

    sources = payload.get("sources", [])
    if not isinstance(sources, list) or not sources:
        raise ValueError("候选知识至少需要一个可追溯来源")
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("候选知识 sources 中的每一项必须是对象")
        source_missing = CANDIDATE_SOURCE_REQUIRED - set(source)
        if source_missing:
            raise ValueError(f"候选来源缺少字段：{sorted(source_missing)}")
        if not isinstance(source["source_id"], str) or not source["source_id"].strip():
            raise ValueError("候选来源 source_id 必须是非空字符串")
        if not isinstance(source["license"], str) or not source["license"].strip():
            raise ValueError("候选来源 license 必须是非空字符串")
        if not isinstance(source["commercial_use"], bool):
            raise ValueError("候选来源 commercial_use 必须是布尔值")

    has_noncommercial_source = any(not source["commercial_use"] for source in sources)
    commercial_eligible = bool(payload.get("commercial_eligible", False))
    if has_noncommercial_source and commercial_eligible:
        raise ValueError("含非商业来源的候选知识不能标记为可商用")

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    fingerprint = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:10]
    candidate_id = payload.get("id") or (
        f"TC-CAND-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{fingerprint}"
    )
    if not isinstance(candidate_id, str) or not re.fullmatch(
        r"[0-9A-Za-z._-]+", candidate_id
    ):
        raise ValueError("候选知识 id 只能包含字母、数字、点、下划线和连字符")

    return {
        "id": candidate_id,
        "created_at": payload.get("created_at", now),
        "level": "L1",
        "status": "candidate-research",
        "visibility": "local-private",
        "human_review_required": True,
        "promotion_eligible": False,
        "commercial_eligible": commercial_eligible,
        "source_type": payload["source_type"].strip(),
        "problem": payload["problem"].strip(),
        "hypothesis": payload["hypothesis"].strip(),
        "scenario": payload["scenario"].strip(),
        "action": payload["action"].strip(),
        "success_metric": payload["success_metric"].strip(),
        "counterexample": payload["counterexample"].strip(),
        "boundary": payload["boundary"].strip(),
        "evidence": [item.strip() for item in evidence if item.strip()],
        "sources": sources,
        "review_note": payload.get(
            "review_note",
            "候选内容只能用于设计实验；取得独立市场证据并完成人工许可审查前，"
            "不得进入公开或商业 TC 方法。",
        ),
    }


def save_candidate(
    payload: dict, candidate_dir: str | Path | None = None
) -> dict:
    record = normalize_candidate(payload)
    root = (
        Path(candidate_dir).expanduser()
        if candidate_dir
        else default_candidate_dir()
    )
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{record['id']}.json"
    if target.exists():
        raise ValueError(f"候选知识已经存在：{target}")
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(target)
    return {
        "saved": str(target),
        "id": record["id"],
        "status": record["status"],
        "promotion_eligible": record["promotion_eligible"],
        "commercial_eligible": record["commercial_eligible"],
    }


def create_dbs_candidate(
    query: str,
    payload_path: str | Path,
    limit: int,
    source_path: str | Path | None = None,
    cache_dir: str | Path | None = None,
    candidate_dir: str | Path | None = None,
) -> dict:
    if limit < 3 or limit > 5:
        raise ValueError("DBS 候选知识每次必须选择 3 至 5 条相关记录")
    rows = search_dbs_books(query, limit, source_path, cache_dir)
    if not rows:
        raise ValueError(f"DBS 中没有找到与“{query}”相关的记录")
    payload = load_json_object(payload_path)
    for field in (
        "problem",
        "hypothesis",
        "scenario",
        "action",
        "success_metric",
        "counterexample",
        "boundary",
    ):
        value = payload.get(field, "")
        if not isinstance(value, str):
            continue
        compact_value = re.sub(r"\s+", "", value)
        for row in rows:
            compact_source = re.sub(r"\s+", "", row["text"])
            if len(compact_value) >= 25 and compact_value in compact_source:
                raise ValueError(
                    f"字段 {field} 疑似直接复制 DBS 原文；请只写独立问题假设和验证动作"
                )
    payload.update(
        {
            "source_type": "dbs-external-research",
            "commercial_eligible": False,
            "sources": [
                {
                    "source_id": row["source_id"],
                    "record_id": row["id"],
                    "date": row["date"],
                    "url": row["url"],
                    "theme": row["theme"],
                    "tags": row["tags"],
                    "license": row["license"],
                    "commercial_use": False,
                }
                for row in rows
            ],
            "review_note": (
                "这是带 DBS 溯源的非商业研究候选，不含原文正文。"
                "只有取得独立用户、付款或交付证据，并通过人工许可审查后，"
                "才能另行提炼为 TC 方法。"
            ),
        }
    )
    return save_candidate(payload, candidate_dir)


def list_candidates(candidate_dir: str | Path | None = None) -> list[dict]:
    root = (
        Path(candidate_dir).expanduser()
        if candidate_dir
        else default_candidate_dir()
    )
    if not root.is_dir():
        return []
    rows: list[dict] = []
    for path in sorted(root.glob("*.json")):
        try:
            payload = load_json_object(path)
        except ValueError:
            continue
        rows.append(
            {
                "id": payload.get("id", path.stem),
                "source_type": payload.get("source_type"),
                "status": payload.get("status"),
                "created_at": payload.get("created_at"),
                "commercial_eligible": payload.get("commercial_eligible", False),
                "path": str(path),
            }
        )
    return rows


def fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "TC-Knowledge/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"下载失败：{url}（{error}）") from error


def sync_dbs_books(cache_dir: str | Path | None = None) -> dict:
    root = Path(cache_dir).expanduser() if cache_dir else default_dbs_cache_dir()
    markdown_bytes = fetch_bytes(DBS_MARKDOWN_URL)
    license_bytes = fetch_bytes(DBS_LICENSE_URL)
    markdown = markdown_bytes.decode("utf-8")
    license_text = license_bytes.decode("utf-8")
    rows = parse_dbs_books(markdown)
    if not rows:
        raise ValueError("DBS Markdown 没有解析出任何记录，拒绝覆盖本地缓存")
    if "CC BY-NC 4.0" not in license_text:
        raise ValueError("上游许可证与预期不符，拒绝同步")

    root.mkdir(parents=True, exist_ok=True)
    markdown_path = root / DBS_FILENAME
    license_path = root / "LICENSE"
    metadata_path = root / "source.json"
    markdown_tmp = markdown_path.with_suffix(".md.tmp")
    license_tmp = license_path.with_suffix(".tmp")
    metadata_tmp = metadata_path.with_suffix(".json.tmp")
    metadata = {
        "source_id": "dbs-books",
        "repository": DBS_REPOSITORY,
        "markdown_url": DBS_MARKDOWN_URL,
        "license": "CC BY-NC 4.0",
        "commercial_use": False,
        "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "records": len(rows),
        "sha256": hashlib.sha256(markdown_bytes).hexdigest(),
    }
    markdown_tmp.write_bytes(markdown_bytes)
    license_tmp.write_bytes(license_bytes)
    metadata_tmp.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_tmp.replace(markdown_path)
    license_tmp.replace(license_path)
    metadata_tmp.replace(metadata_path)
    return {**metadata, "path": str(markdown_path)}


def dbs_status(
    explicit_path: str | Path | None = None, cache_dir: str | Path | None = None
) -> dict:
    path = resolve_dbs_markdown(explicit_path, cache_dir)
    if not path.is_file():
        return {
            "source_id": "dbs-books",
            "installed": False,
            "path": str(path),
            "license": "CC BY-NC 4.0",
            "commercial_use": False,
        }
    rows = parse_dbs_books(path.read_text(encoding="utf-8"))
    return {
        "source_id": "dbs-books",
        "installed": True,
        "path": str(path),
        "records": len(rows),
        "date_range": [min(row["date"] for row in rows), max(row["date"] for row in rows)],
        "license": "CC BY-NC 4.0",
        "commercial_use": False,
    }


def search(
    query: str,
    scope: str,
    limit: int,
    source_path: str | Path | None = None,
    cache_dir: str | Path | None = None,
) -> list[dict]:
    if scope == "dbs-books":
        return search_dbs_books(query, limit, source_path, cache_dir)
    results: list[dict] = []
    if scope in {"all", "sources"}:
        for path in sorted(CORE_SOURCES.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            score = score_text(query, f"{path.stem} {content}")
            if score:
                results.append(
                    {
                        "kind": "source",
                        "score": score,
                        "name": path.stem,
                        "path": f"core-sources/{path.name}",
                        "preview": re.sub(r"\s+", " ", content)[:320],
                    }
                )
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
        for kind in ("source", "pack", "atom", "post")
    }
    chosen: list[dict] = []
    if groups["source"] and len(chosen) < limit:
        chosen.append(groups["source"].pop(0))
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
        groups["source"] + groups["pack"] + groups["atom"] + groups["post"], key=relevance
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
        elif row["kind"] == "pack":
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
        elif row["kind"] == "external-post":
            preview = re.sub(r"\s+", " ", row["text"]).strip()[:300]
            lines.extend(
                [
                    f"### [DBS 外部观点] {row['date']} · {row['theme']}",
                    "",
                    preview + ("……" if len(row["text"]) > 300 else ""),
                    "",
                    f"- 标签：{'、'.join(row['tags'])}",
                    f"- 表达：{row['expression']} · 原帖：{row['url']}",
                    "- 证据：第三方公开观点（C 级），不是事实或 TC 定律",
                    "- 许可：CC BY-NC 4.0，仅限署名的非商业使用；商业输出不得复制或改写原文",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"### [核心参考源] {row['name']}",
                    "",
                    row["preview"] + "……",
                    "",
                    f"- 文件：{row['path']}",
                    "- 边界：这是判断问题的核心视角，不是当前事实或普遍真理",
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
    sources = list(CORE_SOURCES.glob("*.md"))
    if len(sources) < 2:
        errors.append("TC 核心参考源不足两份")
    if not DBS_SOURCE_CARD.is_file():
        errors.append("缺少 DBS 外部理论库来源卡")
    else:
        source_card = DBS_SOURCE_CARD.read_text(encoding="utf-8")
        for phrase in (
            DBS_REPOSITORY,
            "CC BY-NC 4.0",
            "不随 TC 安装包分发",
            "dbs-candidate",
            "commercial_eligible=false",
            "promotion_eligible=false",
        ):
            if phrase not in source_card:
                errors.append(f"DBS 外部理论库来源卡缺少：{phrase}")
    return errors


def stats() -> dict:
    atoms = load_jsonl(ATOMS)
    posts = load_jsonl(POSTS)
    topics = Counter(topic for atom in atoms for topic in atom["topics"])
    result = {
        "atoms": len(atoms),
        "posts": len(posts),
        "packs": len(list(PACKS.glob("*.md"))),
        "sources": len(list(CORE_SOURCES.glob("*.md"))),
        "post_date_range": [min(row["date"] for row in posts), max(row["date"] for row in posts)]
        if posts
        else [],
        "levels": dict(Counter(atom["level"] for atom in atoms)),
        "top_topics": topics.most_common(12),
    }
    result["external_dbs_books"] = dbs_status()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument(
        "--scope",
        choices=["all", "sources", "atoms", "posts", "packs", "dbs-books"],
        default="all",
    )
    search_parser.add_argument("--limit", type=int, default=5)
    search_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    search_parser.add_argument(
        "--source-path",
        help="DBS Markdown 文件或其所在目录；也可设置 TC_DBS_BOOKS_PATH",
    )
    search_parser.add_argument("--cache-dir", help="DBS 外部理论库缓存目录")
    subparsers.add_parser("stats")
    subparsers.add_parser("validate")
    sync_parser = subparsers.add_parser(
        "external-sync", help="从原作者仓库同步可选的外部 Markdown 理论库"
    )
    sync_parser.add_argument("--source", choices=["dbs-books"], required=True)
    sync_parser.add_argument("--cache-dir", help="缓存目录，默认 ~/.tc/external/dbs-books")
    sync_parser.add_argument(
        "--accept-license",
        action="store_true",
        help="确认接受 CC BY-NC 4.0 的署名与非商业限制",
    )
    status_parser = subparsers.add_parser("external-status")
    status_parser.add_argument("--source", choices=["dbs-books"], required=True)
    status_parser.add_argument("--source-path")
    status_parser.add_argument("--cache-dir")
    candidate_parser = subparsers.add_parser(
        "candidate-add",
        help="把人工整理或 tc-state 导出的证据保存为本机候选知识",
    )
    candidate_parser.add_argument("--payload", required=True)
    candidate_parser.add_argument("--candidate-dir")
    dbs_candidate_parser = subparsers.add_parser(
        "dbs-candidate",
        help="把 3 至 5 条 DBS 外部观点加工成带许可边界的本机研究候选",
    )
    dbs_candidate_parser.add_argument("--query", required=True)
    dbs_candidate_parser.add_argument("--payload", required=True)
    dbs_candidate_parser.add_argument("--limit", type=int, default=3)
    dbs_candidate_parser.add_argument("--source-path")
    dbs_candidate_parser.add_argument("--cache-dir")
    dbs_candidate_parser.add_argument("--candidate-dir")
    candidate_list_parser = subparsers.add_parser("candidate-list")
    candidate_list_parser.add_argument("--candidate-dir")
    args = parser.parse_args()

    if args.command == "search":
        if args.limit < 1 or args.limit > 50:
            raise SystemExit("--limit 必须在 1 到 50 之间")
        try:
            rows = search(
                args.query,
                args.scope,
                args.limit,
                source_path=args.source_path,
                cache_dir=args.cache_dir,
            )
        except (FileNotFoundError, ValueError) as error:
            raise SystemExit(str(error)) from error
        if args.format == "json":
            json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
            print()
        else:
            print(markdown_results(args.query, rows))
    elif args.command == "stats":
        json.dump(stats(), sys.stdout, ensure_ascii=False, indent=2)
        print()
    elif args.command == "external-sync":
        if not args.accept_license:
            raise SystemExit(
                "DBS 推文集采用 CC BY-NC 4.0。确认仅作署名的非商业研究后，"
                "重新运行并加上 --accept-license。"
            )
        try:
            result = sync_dbs_books(args.cache_dir)
        except (RuntimeError, UnicodeDecodeError, ValueError) as error:
            raise SystemExit(str(error)) from error
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    elif args.command == "external-status":
        try:
            result = dbs_status(args.source_path, args.cache_dir)
        except ValueError as error:
            raise SystemExit(str(error)) from error
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    elif args.command == "candidate-add":
        try:
            result = save_candidate(
                load_json_object(args.payload), args.candidate_dir
            )
        except ValueError as error:
            raise SystemExit(str(error)) from error
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    elif args.command == "dbs-candidate":
        try:
            result = create_dbs_candidate(
                args.query,
                args.payload,
                args.limit,
                source_path=args.source_path,
                cache_dir=args.cache_dir,
                candidate_dir=args.candidate_dir,
            )
        except (FileNotFoundError, ValueError) as error:
            raise SystemExit(str(error)) from error
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    elif args.command == "candidate-list":
        json.dump(
            list_candidates(args.candidate_dir),
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
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
            f"{summary['atoms']} 条知识原子，{summary['sources']} 个核心参考源，"
            f"{summary['packs']} 个知识包"
        )


if __name__ == "__main__":
    main()
