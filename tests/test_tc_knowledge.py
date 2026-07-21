from __future__ import annotations

import importlib.util
from pathlib import Path
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
        rows = tc_knowledge.search("产品化 真实需求", "all", 8)
        self.assertTrue(rows)
        self.assertTrue(any(row["kind"] == "atom" for row in rows))
        self.assertTrue(any(row["kind"] == "pack" for row in rows))
        self.assertTrue(any(row["kind"] == "source" for row in rows))
        self.assertEqual(rows[0]["kind"], "source")

    def test_partner_worldview_is_a_searchable_core_source(self) -> None:
        rows = tc_knowledge.search("AI Agent To B 商业化 企业交付", "sources", 5)
        self.assertTrue(rows)
        partner_rows = [row for row in rows if "技术合伙人" in row["name"]]
        self.assertTrue(partner_rows)
        self.assertEqual(partner_rows[0]["kind"], "source")

    def test_historical_posts_stay_historical(self) -> None:
        rows = tc_knowledge.search("天策局", "posts", 3)
        self.assertTrue(rows)
        self.assertTrue(all(row["status"] == "historical-public" for row in rows))


if __name__ == "__main__":
    unittest.main()
