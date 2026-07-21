# TC 知识库导航

这不是一堆为了显得专业而堆起来的资料。它只保存 TC 在执行创业任务时需要按需读取、能够解释来源和边界的知识。

## 当前知识包

| 主题 | 权威文件 | 什么时候读取 |
| --- | --- | --- |
| 问对问题与解题 | [`skills/tc/references/question-to-solution.md`](../skills/tc/references/question-to-solution.md) | 每次复杂任务先读取，判断表面问题与真实需要 |
| 创业闭环 | [`skills/tc/references/market-loop.md`](../skills/tc/references/market-loop.md) | 验证需求、报价、成交、交付 |
| 长期原则 | [`skills/tc/references/principles.md`](../skills/tc/references/principles.md) | 方向取舍、现金流、合作原则 |
| 内容到收入 | [`skills/tc/references/content-to-revenue.md`](../skills/tc/references/content-to-revenue.md) | 内容、获客、报价、信任 |
| X 增长 | [`skills/tc/references/x-growth.md`](../skills/tc/references/x-growth.md) | X 定位、内容结构、复盘指标 |
| 收入记分 | [`skills/tc/references/revenue-scoreboard.md`](../skills/tc/references/revenue-scoreboard.md) | 区分流水、营收、回款和毛利 |
| 案例复盘 | [`skills/tc/references/case-library.md`](../skills/tc/references/case-library.md) | 失败信号、复盘与下一次验证 |
| 新手引导 | [`skills/tc/references/onboarding.md`](../skills/tc/references/onboarding.md) | 第一次使用 TC |
| 七天内测 | [`skills/tc/references/pilot-validation.md`](../skills/tc/references/pilot-validation.md) | 验证 Skill 是否真的推动行动 |
| 跨平台分发 | [`skills/tc/references/distribution.md`](../skills/tc/references/distribution.md) | 安装、分享和轻量版使用 |
| 用户反馈 | [`skills/tc/references/feedback.md`](../skills/tc/references/feedback.md) | 用户主动报告问题或建议 |
| 公开边界 | [`skills/tc/references/public-boundaries.md`](../skills/tc/references/public-boundaries.md) | 公开内容、商业宣传与隐私风险 |
| DBS 协同 | [`skills/tc/references/dbs-integration.md`](../skills/tc/references/dbs-integration.md) | 环境中已安装 DBS 时 |
| 草根创业方法 | [`skills/tc/references/grassroots-integration.md`](../skills/tc/references/grassroots-integration.md) | 调研、对标、试错、团队边界 |
| 外部知识源路由 | [`skills/tc/references/knowledge-routing.md`](../skills/tc/references/knowledge-routing.md) | 用户提供飞书、本地目录、历史内容或真源导航时 |
| 外部实操资料提炼 | [`skills/tc/references/source-distillation.md`](../skills/tc/references/source-distillation.md) | 把某个人的大量帖子或记录变成可验证知识原子时 |
| 天策公开知识包 | [`skills/tc/references/public-knowledge-atoms.md`](../skills/tc/references/public-knowledge-atoms.md) | 当前任务需要作者历史公开方法或案例时 |

## 外部知识源

TC 内置知识回答“怎么判断”，外部知识库回答“这个用户真实发生了什么”。接入方式见 [`外部知识源接入.md`](外部知识源接入.md)。

公开仓库只保存方法和接口，不复制用户私有资料。天策当前使用飞书 V4 管理最新状态、本地 X 导出保存历史公开证据、TC GitHub 发布通用方法。

## 第一批真实知识原子

[`原子库/atoms.jsonl`](原子库/atoms.jsonl) 当前保存 12 条可追溯的公开知识卡片，来源均为 `@Leobai825` 的历史公开推文。它们带日期、原链接、可信度和使用边界；数字与业务状态不能脱离原日期引用。

这批原子不是为了证明 TC “资料很多”，而是让下面三件事第一次可以被检查：

1. 一条原则到底来自哪里；
2. 原文里哪些部分可以采用、哪些只能当待验证观点；
3. 用户带回新证据后，旧判断是否需要降级或删除。

字段和录入规则见 [`原子库/README.md`](原子库/README.md)。

## 维护规则

1. `skills/tc/SKILL.md` 只保存核心流程和读取路由。
2. 详细方法只保留在一份参考文件中，避免相同结论多处漂移。
3. 新资料只有反复影响真实任务，才升级为知识包。
4. 案例进入公开仓库前必须脱敏，并说明事实、假设、动作和结果。
5. 粉丝、营收、价格、平台政策、合作状态等动态信息不作为永久事实写入知识库。
6. 无法核验的观点要标记为假设、经验或待验证，不包装成定律。
7. 外部知识源按需读取；先读真源导航，再读能改变当前判断的最小片段。
8. 大量外部帖子先进入知识原子层；原文被收录不代表 TC 认可，必须经过证据、边界、合规和可执行性筛选。

## 下一阶段

继续从真实公开案例和脱敏试用反馈中增加原子，但不设虚假的数量目标。每次新增都必须有来源、日期、适用场景、证据等级和是否仍有效；未经核验的内容不得升级为核心原则。

录入新原子时使用 [知识原子录入模板](知识原子录入模板.md)。
