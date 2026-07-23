from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "tc-knowledge" / "scripts" / "tc_knowledge.py"
SPEC = importlib.util.spec_from_file_location("tc_knowledge", SCRIPT)
assert SPEC and SPEC.loader
tc_knowledge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tc_knowledge)


class TCKnowledgeTests(unittest.TestCase):
    def test_bundled_knowledge_validates(self) -> None:
        self.assertEqual(tc_knowledge.validate(), [])

    def test_stats_match_public_snapshot(self) -> None:
        stats = tc_knowledge.stats()
        self.assertEqual(stats["posts"], 489)
        self.assertEqual(stats["atoms"], 22)
        self.assertEqual(stats["sources"], 2)
        self.assertEqual(stats["packs"], 6)
        self.assertEqual(stats["post_date_range"], ["2025-11-27", "2026-07-14"])

    def test_product_search_prioritizes_curated_knowledge(self) -> None:
        rows = tc_knowledge.search("产品化 真实需求", "guidance", 8)
        self.assertTrue(rows)
        self.assertTrue(any(row["kind"] == "atom" for row in rows))
        self.assertTrue(any(row["kind"] == "pack" for row in rows))
        self.assertTrue(any(row["kind"] == "source" for row in rows))
        self.assertFalse(any(row["kind"] == "post" for row in rows))
        self.assertEqual(rows[0]["kind"], "source")

    def test_legacy_all_scope_also_excludes_author_history(self) -> None:
        rows = tc_knowledge.search("亚马逊 ACCA 副业", "all", 50)
        self.assertFalse(any(row["kind"] == "post" for row in rows))

    def test_cli_default_scope_does_not_return_author_posts(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "search",
                "--query",
                "ACCA 代写",
                "--format",
                "json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        rows = json.loads(completed.stdout)
        self.assertFalse(any(row["kind"] == "post" for row in rows))

    def test_partner_worldview_is_a_searchable_core_source(self) -> None:
        rows = tc_knowledge.search("AI Agent To B 商业化 企业交付", "sources", 5)
        self.assertTrue(rows)
        partner_rows = [row for row in rows if "技术合伙人" in row["name"]]
        self.assertTrue(partner_rows)
        self.assertEqual(partner_rows[0]["kind"], "source")

    def test_historical_posts_stay_historical(self) -> None:
        rows = tc_knowledge.search("天策局", "posts", 3)
        self.assertTrue(rows)
        self.assertTrue(all(row["kind"] == "post" for row in rows))
        self.assertTrue(all(row["status"] == "historical-public" for row in rows))

    def test_dbs_markdown_parser_preserves_source_fields(self) -> None:
        sample = """# 外部推文集

## 2026-07-01 · 主贴

> 先找用户，再做产品。

原帖：[https://x.com/dontbesilent/status/100](https://x.com/dontbesilent/status/100)

主题：商业与产品｜表达：方法
标签：用户需求、产品验证

---

## 2026-06-30 · 引用

> 流量不是收入。

原帖：[https://x.com/dontbesilent/status/99](https://x.com/dontbesilent/status/99)

主题：内容与传播｜表达：观点
标签：流量、变现
"""
        rows = tc_knowledge.parse_dbs_books(sample)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["date"], "2026-07-01")
        self.assertEqual(rows[0]["theme"], "商业与产品")
        self.assertEqual(rows[0]["tags"], ["用户需求", "产品验证"])
        self.assertEqual(rows[0]["license"], "CC BY-NC 4.0")

    def test_dbs_search_uses_user_supplied_markdown_without_bundling_it(self) -> None:
        sample = """# 外部推文集

## 2026-07-01 · 主贴

> 先找用户，再做产品。

原帖：[https://x.com/dontbesilent/status/100](https://x.com/dontbesilent/status/100)

主题：商业与产品｜表达：方法
标签：用户需求、产品验证
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / tc_knowledge.DBS_FILENAME
            path.write_text(sample, encoding="utf-8")
            rows = tc_knowledge.search(
                "产品验证", "dbs-books", 3, source_path=path
            )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_id"], "dbs-books")
        self.assertEqual(rows[0]["status"], "external-view")

    def test_dbs_source_card_is_bundled_but_corpus_is_not(self) -> None:
        self.assertTrue(tc_knowledge.DBS_SOURCE_CARD.is_file())
        bundled_corpus = tc_knowledge.REFERENCES / tc_knowledge.DBS_FILENAME
        self.assertFalse(bundled_corpus.exists())

    def candidate_payload(self) -> dict:
        return {
            "problem": "零资源用户不知道先验证哪个创业问题。",
            "hypothesis": "先从已经进入的工作场景生成一个服务假设。",
            "scenario": "用户有半年生活缓冲和一项实际工作经历。",
            "action": "接触五位真实从业者并记录原话。",
            "success_metric": "七天内完成五次有效对话。",
            "counterexample": "五次对话没有出现重复问题。",
            "boundary": "候选假设不是市场事实，不承诺收入。",
            "evidence": [],
        }

    def test_dbs_candidate_keeps_provenance_and_stays_noncommercial(self) -> None:
        sample = """# 外部推文集

## 2026-07-01 · 主贴

> 先找用户，再做产品。

原帖：[https://x.com/dontbesilent/status/100](https://x.com/dontbesilent/status/100)

主题：商业与产品｜表达：方法
标签：用户需求、产品验证

---

## 2026-06-30 · 主贴

> 用真实反馈修改方向。

原帖：[https://x.com/dontbesilent/status/99](https://x.com/dontbesilent/status/99)

主题：行动与反馈｜表达：方法
标签：用户需求、真实反馈

---

## 2026-06-29 · 主贴

> 小成本测试比完整开发更早。

原帖：[https://x.com/dontbesilent/status/98](https://x.com/dontbesilent/status/98)

主题：创业实验｜表达：方法
标签：产品验证、行动
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / tc_knowledge.DBS_FILENAME
            source.write_text(sample, encoding="utf-8")
            payload = root / "payload.json"
            payload.write_text(
                json.dumps(self.candidate_payload(), ensure_ascii=False),
                encoding="utf-8",
            )
            result = tc_knowledge.create_dbs_candidate(
                "用户需求 产品验证",
                payload,
                3,
                source_path=source,
                candidate_dir=root / "candidates",
            )
            saved = json.loads(Path(result["saved"]).read_text(encoding="utf-8"))

        self.assertEqual(saved["source_type"], "dbs-external-research")
        self.assertFalse(saved["commercial_eligible"])
        self.assertFalse(saved["promotion_eligible"])
        self.assertEqual(len(saved["sources"]), 3)
        self.assertTrue(
            all(source["license"] == "CC BY-NC 4.0" for source in saved["sources"])
        )
        self.assertTrue(all("text" not in source for source in saved["sources"]))

    def test_noncommercial_candidate_cannot_claim_commercial_eligibility(self) -> None:
        payload = {
            **self.candidate_payload(),
            "source_type": "external-research",
            "commercial_eligible": True,
            "sources": [
                {
                    "source_id": "dbs-books",
                    "license": "CC BY-NC 4.0",
                    "commercial_use": False,
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "不能标记为可商用"):
            tc_knowledge.normalize_candidate(payload)


if __name__ == "__main__":
    unittest.main()
