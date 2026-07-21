#!/usr/bin/env python3
"""Export public original posts from an X archive into TC's JSONL index.

Only data/tweets.js and data/note-tweet.js are read. Direct messages, contacts,
account security files, ad data, and application tokens are never inspected.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


def load_archive_js(path: Path):
    raw = path.read_text(encoding="utf-8")
    try:
        payload = raw.split("=", 1)[1].strip()
    except IndexError as error:
        raise ValueError(f"无法识别 X 归档文件：{path}") from error
    return json.loads(payload)


def utc_key(created_at: str) -> str:
    parsed = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def normalize(text: str) -> str:
    text = re.sub(r"https://t\.co/\S+", "", text or "")
    return re.sub(r"\s+", " ", text.replace("…", "")).strip()


def public_originals(archive: Path, handle: str) -> list[dict]:
    data = archive / "data"
    tweets_path = data / "tweets.js"
    notes_path = data / "note-tweet.js"
    if not tweets_path.is_file() or not notes_path.is_file():
        raise FileNotFoundError(
            "归档目录必须包含 data/tweets.js 和 data/note-tweet.js"
        )

    tweets = [row["tweet"] for row in load_archive_js(tweets_path)]
    notes = [row["noteTweet"] for row in load_archive_js(notes_path)]
    notes_by_timestamp = {note["createdAt"]: note for note in notes}

    def full_text(tweet: dict) -> str:
        exact = notes_by_timestamp.get(utc_key(tweet["created_at"]))
        if exact:
            return exact.get("core", {}).get("text", "")
        preview = normalize(tweet.get("full_text", ""))
        if len(preview) >= 30:
            matches = [
                note
                for note in notes
                if normalize(note.get("core", {}).get("text", "")).startswith(preview)
            ]
            if len(matches) == 1:
                return matches[0].get("core", {}).get("text", "")
        return tweet.get("full_text", "")

    records: list[dict] = []
    for tweet in tweets:
        text = tweet.get("full_text", "")
        if text.startswith("RT @") or tweet.get("in_reply_to_status_id_str"):
            continue
        created = datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S %z %Y")
        likes = int(tweet.get("favorite_count") or 0)
        reposts = int(tweet.get("retweet_count") or 0)
        records.append(
            {
                "id": tweet["id_str"],
                "date": created.date().isoformat(),
                "text": full_text(tweet),
                "likes": likes,
                "reposts": reposts,
                "engagement": likes + reposts,
                "url": f"https://x.com/{handle}/status/{tweet['id_str']}",
                "status": "historical-public",
            }
        )
    records.sort(key=lambda row: (row["date"], row["id"]), reverse=True)
    return records


def write_jsonl(records: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="X 归档根目录")
    parser.add_argument("--output", type=Path, required=True, help="输出 JSONL 路径")
    parser.add_argument("--handle", default="Leobai825", help="公开 X 用户名")
    args = parser.parse_args()
    rows = public_originals(args.archive.resolve(), args.handle.lstrip("@"))
    write_jsonl(rows, args.output.resolve())
    dates = [row["date"] for row in rows]
    date_range = f"{min(dates)} 至 {max(dates)}" if dates else "空"
    print(f"已导出 {len(rows)} 条公开原创内容，日期范围：{date_range}")


if __name__ == "__main__":
    main()

