# DBS 开源推文集｜外部理论库来源卡

## 来源

- 作者：dontbesilent
- 仓库：https://github.com/dontbesilent2025/dbskill
- Markdown：https://github.com/dontbesilent2025/dbskill/blob/main/books/dontbesilent-开源推文集.md
- 当前公开说明：由公开推文筛选而成，记录保留日期、原帖链接、主题、表达形式和标签。
- TC 定位：外部观点与一手经验检索库，不是 TC 的事实真源，也不代表 TC 认可每条内容。

## 为什么只接 Markdown

AI 检索优先使用 Markdown，不读取 PDF。Markdown 可以稳定拆出：

- 日期与内容类型；
- 原文正文；
- 原帖链接；
- 主题与表达形式；
- 标签。

TC 的检索器会优先匹配标签和主题，再匹配正文；返回结果必须带日期、原链接和第三方观点边界。

## 许可与分发边界

上游许可证是 **CC BY-NC 4.0**：必须署名，只允许非商业使用。

- 全文不随 TC 安装包分发，也不改挂 Apache-2.0；
- 用户确认许可证后，由脚本直接从原作者仓库同步到本机 `~/.tc/external/dbs-books/`；
- 检索结果只用于署名的非商业研究、个人学习和来源回溯；
- 商业文案、付费交付、课程或产品不得复制、洗稿或改写原文，除非另行取得作者许可；
- TC 可以独立使用常识性商业原则，但不能把受许可保护的独特表达包装成自己的内容。

## 在 TC 中怎样使用

DBS 有两种完全不同的使用状态：

1. **对话态**：用户明确要求“结合 DBS”时，只检索 3 至 5 条相关观点，保留署名、日期、链接和非商业边界。
2. **维护态**：维护者可以把相关观点加工成保存在本机的 L1 研究候选，用来设计 TC 的问题、实验和反例；候选不会自动进入公开 Skill。

第一次同步：

```bash
python3 scripts/tc_knowledge.py external-sync \
  --source dbs-books --accept-license
```

按具体问题检索：

```bash
python3 scripts/tc_knowledge.py search \
  --scope dbs-books --query "流量 变现 产品" --limit 5
```

已经手动下载 Markdown 时，可以加：

```bash
--source-path /path/to/dontbesilent-开源推文集.md
```

也可以设置环境变量 `TC_DBS_BOOKS_PATH`。它可以指向 Markdown 文件，也可以指向包含该文件的目录。

### 维护态加工

先由维护者写一份不含原文的候选 payload：

```json
{
  "problem": "要解决的创业问题",
  "hypothesis": "准备验证的独立假设",
  "scenario": "适用场景",
  "action": "最小市场动作",
  "success_metric": "有效标准",
  "counterexample": "什么情况会推翻它",
  "boundary": "风险、许可和停止条件",
  "evidence": []
}
```

再把 3 至 5 条相关 DBS 记录作为来源元数据附到本机候选：

```bash
python3 skills/tc-knowledge/scripts/tc_knowledge.py dbs-candidate \
  --query "用户需求 产品验证" \
  --payload /tmp/tc-dbs-candidate.json \
  --limit 3
```

命令只保存记录 ID、日期、链接、主题、标签和许可证，不复制原文正文。默认写入 `~/.tc/knowledge-candidates/`，状态固定为 `L1 / candidate-research / local-private`，并且 `commercial_eligible=false`、`promotion_eligible=false`。

候选至少经过以下关口，才允许另行提炼：

1. 由真实用户原话、付款、交付、毛利或多个独立来源提供新证据；
2. 写出适用场景、反例、失败代价和停止条件；
3. 人工确认没有复制 DBS 的独特表达、结构或案例；
4. 人工确认许可范围。没有额外授权时，不把 DBS 候选直接放入 Apache-2.0 的公开或商业安装包。

升级后的公开 TC 原子必须引用独立证据，不能把 DBS 来源换个说法后伪装成 TC 自证。

## 路由规则

以下问题可以查这套外部理论库：

- 商业、产品、用户需求、定价与变现；
- 内容、自媒体、流量、短视频与个人品牌；
- AI、Agent、提示词、工作流与工具选择；
- 行动阻力、对标、学习、认知与个人成长。

使用顺序：

1. 先以用户当前事实和 TC 内部方法定义问题；
2. 再按关键词查 3 至 5 条最相关外部观点；
3. 区分观点、经验、方法、案例和问题；
4. 只保留会改变当前判断或验证动作的部分；
5. 最终方案仍由真实用户反馈、付款、交付和毛利验证。

不要因为作者表达有力量、内容数量多或传播效果好，就把观点升级成普遍规律。
