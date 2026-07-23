from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class SkillContractTests(unittest.TestCase):
    def test_product_positioning_cannot_drift_into_an_encyclopedia(self) -> None:
        main = read("skills/tc/SKILL.md")
        readme = read("README.md")
        for text in (main, readme):
            self.assertIn("AI 创业解题教练", text)
            self.assertIn(
                "讲清问题 → 找到最早断点 → 做一次低成本验证 → 根据结果继续调整",
                text,
            )
            self.assertIn("知识库只是", text)
            self.assertIn("创业百科", text)
            self.assertIn("暴利项目推荐器", text)
        self.assertIn("把创业想明白，更要把下一步做出来。", readme)

    def test_main_skill_is_a_lean_router(self) -> None:
        text = read("skills/tc/SKILL.md")
        self.assertLessEqual(len(text.splitlines()), 240)
        self.assertIn("从零项目", text)
        self.assertIn("诊断何时必须结束", text)
        self.assertIn("项目假设（不是市场结论）", text)
        self.assertIn("zero-to-one.md", text)

    def test_author_history_is_separated_from_user_judgment(self) -> None:
        main = read("skills/tc/SKILL.md")
        zero_to_one = read("skills/tc/references/zero-to-one.md")
        knowledge = read("skills/tc-knowledge/SKILL.md")
        for phrase in (
            "作者方法与作者经历必须隔离",
            "不得参与创业项目生成、方向推荐、用户能力判断或当前市场判断",
        ):
            self.assertIn(phrase, main)
        self.assertIn("不得拿 TC 作者", knowledge)
        self.assertIn("不得拿 TC 作者、知识库作者或历史案例人物", knowledge)
        self.assertIn("不得拿 TC 作者、知识库作者、历史案例人物", zero_to_one)
        self.assertIn("--scope posts", knowledge)

    def test_zero_to_one_never_pretends_market_access(self) -> None:
        text = read("skills/tc/references/zero-to-one.md")
        for phrase in (
            "项目假设",
            "最多追问两个",
            "有联网或检索工具",
            "没有联网或检索工具",
            "不得编造市场规模、价格、案例、客户",
        ):
            self.assertIn(phrase, text)

    def test_diagnosis_has_a_hard_handoff(self) -> None:
        text = read("skills/tc-diagnosis/SKILL.md")
        self.assertIn("诊断结束条件", text)
        self.assertIn("立即停止追问", text)
        self.assertIn("最多追问两个", text)
        self.assertIn("返回 `/tc` 生成一个项目假设", text)

    def test_dbs_distillation_is_local_and_license_gated(self) -> None:
        source_card = read("知识库/外部理论库/dbs-books.md")
        knowledge_skill = read("skills/tc-knowledge/SKILL.md")
        for text in (source_card, knowledge_skill):
            self.assertIn("dbs-candidate", text)
            self.assertIn("本机", text)
            self.assertIn("CC BY-NC 4.0", text)
            self.assertIn("独立", text)
        self.assertIn("commercial_eligible=false", source_card)
        self.assertIn("promotion_eligible=false", source_card)

    def test_state_feedback_requires_separate_consent(self) -> None:
        text = read("skills/tc-state/SKILL.md")
        self.assertIn("export-evidence", text)
        self.assertIn("单独取得当次授权", text)
        self.assertIn("不上传", text)
        self.assertIn("一次状态或一个成功案例不能升级", text)


if __name__ == "__main__":
    unittest.main()
