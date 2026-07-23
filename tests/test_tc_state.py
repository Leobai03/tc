from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "tc-state" / "scripts" / "tc_state.py"


class TcStateTest(unittest.TestCase):
    def run_state(self, state_root: Path, *arguments: str, check: bool = True):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(state_root), *arguments],
            check=check,
            capture_output=True,
            text=True,
        )

    def payload(self, decision: str = "只测试一个服务") -> dict:
        return {
            "project": "九十天主线",
            "title": "确定唯一主线",
            "source_skill": "tc",
            "status": "active",
            "problem_definition": "选出未来九十天唯一主线。",
            "confirmed_facts": ["已有公开内容渠道"],
            "decision": decision,
            "tradeoff": "暂时不新开赛道。",
            "rejected_directions": ["同时做三个项目"],
            "assumptions": ["现有咨询存在重复需求"],
            "next_action": "整理最近十次咨询。",
            "success_metric": "七天内正式报价五次。",
            "evidence": [],
            "next_skill": "tc-action",
        }

    def write_payload(self, directory: Path, payload: dict, name: str) -> Path:
        target = directory / name
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return target

    def test_save_list_restore_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            state_root = base / "state"
            first = self.write_payload(base, self.payload(), "first.json")
            saved = json.loads(
                self.run_state(state_root, "save", "--payload", str(first)).stdout
            )
            self.assertTrue(Path(saved["saved"]).is_file())
            self.assertTrue(Path(saved["current"]).is_file())
            self.assertTrue(Path(saved["structured"]).is_file())

            listed = json.loads(self.run_state(state_root, "list").stdout)
            self.assertEqual(listed[0]["project"], "九十天主线")
            self.assertEqual(listed[0]["snapshots"], 1)

            restored = json.loads(
                self.run_state(state_root, "restore", "--project", "九十天主线").stdout
            )
            self.assertIn("只测试一个服务", restored["content"])

            second_payload = self.payload("根据第一轮反馈收紧服务范围")
            second = self.write_payload(base, second_payload, "second.json")
            self.run_state(state_root, "save", "--payload", str(second))

            restored_again = json.loads(
                self.run_state(state_root, "restore", "--project", "九十天主线").stdout
            )
            self.assertIn("根据第一轮反馈收紧服务范围", restored_again["content"])

            report = json.loads(
                self.run_state(state_root, "report", "--project", "九十天主线").stdout
            )
            report_path = Path(report["report"])
            self.assertTrue(report_path.is_file())
            self.assertEqual(report["snapshots"], 2)
            self.assertIn("时间线", report_path.read_text(encoding="utf-8"))

    def test_missing_required_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            state_root = base / "state"
            payload = self.payload()
            payload["decision"] = ""
            source = self.write_payload(base, payload, "invalid.json")
            result = self.run_state(
                state_root, "save", "--payload", str(source), check=False
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("decision", result.stderr)

    def test_evidence_export_requires_separate_consent_and_redacts_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            state_root = base / "state"
            payload = self.payload()
            payload["problem_definition"] = (
                "联系客户 13800138000，并发到 test@example.com。"
            )
            payload["evidence"] = [
                "客户原话在 https://example.com/private",
                "已收到一笔真实定金",
            ]
            source = self.write_payload(base, payload, "evidence.json")
            self.run_state(state_root, "save", "--payload", str(source))
            target = base / "candidate.json"

            denied = self.run_state(
                state_root,
                "export-evidence",
                "--project",
                "九十天主线",
                "--output",
                str(target),
                check=False,
            )
            self.assertNotEqual(denied.returncode, 0)
            self.assertFalse(target.exists())

            exported = json.loads(
                self.run_state(
                    state_root,
                    "export-evidence",
                    "--project",
                    "九十天主线",
                    "--output",
                    str(target),
                    "--consent",
                ).stdout
            )
            candidate = json.loads(target.read_text(encoding="utf-8"))

        self.assertFalse(exported["uploaded"])
        self.assertEqual(candidate["source_type"], "tc-state-opt-in")
        self.assertFalse(candidate["commercial_eligible"])
        self.assertNotIn(
            "九十天主线", json.dumps(candidate, ensure_ascii=False)
        )
        self.assertNotIn("13800138000", candidate["problem"])
        self.assertNotIn("test@example.com", candidate["problem"])
        self.assertNotIn("https://example.com/private", " ".join(candidate["evidence"]))
        self.assertEqual(candidate["consent_scope"], "local-candidate-only")


if __name__ == "__main__":
    unittest.main()
