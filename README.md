# TC

[![Version](https://img.shields.io/badge/version-1.3.0-45C2FF.svg?style=flat-square)](VERSION)
[![License](https://img.shields.io/badge/license-Apache--2.0-16A34A.svg?style=flat-square)](LICENSE)

> 先重构问题，再定义问题，最后给一个明确方案。

TC 是作者“天策”的名字缩写。它把天策长期形成的价值观与逻辑做成一套渐进式创业解题流程：先把混乱叙述重构成真问题，用户确认后，再给一个明确方案；需要时继续生成文案和真实市场行动。它不承诺赚钱，只提高做出清楚判断和拿到真实证据的概率。

[官网入口](https://leobai825.icu/tc.html) · [X：@Leobai825](https://x.com/Leobai825) · [版本记录](https://github.com/Leobai03/tc/releases)

## 最短使用方式

安装后输入：

```text
/tc
```

也可以把问题一起发出来：

```text
/tc 我做了一个创业社群，有流量也有收入，但不知道下一步该放大什么。
```

TC 会按顺序完成：

```text
/tc
  ↓
把事情直接说出来
  ↓
TC 重构问题并给出问题定义草案
  ↓
你确认或纠正
  ↓
TC 给一个明确方案和第一步
  ↓
带真实结果回来，继续下一步
```

TC 不会一上来扔给你一篇大报告。它默认一次只推进当前一步：先把问题说清楚，再给方案。

## 安装

### Codex、Claude Code 与其他支持 Agent Skills 的工具

```bash
npx -y skills add Leobai03/tc -g --all
```

安装后新开一个对话，输入 `/tc`。

### Claude Code 插件市场

```bash
claude plugin marketplace add Leobai03/tc
claude plugin install tc@tc-skills
```

### 豆包、DeepSeek、Kimi 与普通聊天 AI

这些工具不一定支持原生 Skill 安装。打开 [TC 统一入口](https://leobai825.icu/tc.html)，复制轻量版提示词，作为新对话的第一条消息发送即可。

## Skill 套件

| 调用入口 | 作用 | 什么时候用 |
| --- | --- | --- |
| `/tc` | 主入口与渐进式解题 | 不知道该用哪个时，只记这个 |
| `/tc-diagnosis` | 问题重构与定义 | 方向很多、叙述很乱、不知道真问题 |
| `/tc-copy` | 商业文案 | 需要推文、报价、招募、私聊或跟进表达 |
| `/tc-action` | 行动推进 | 已经想明白，但迟迟没有接触真实市场 |
| `/tc-update` | 官方更新 | 检查或同步 TC 最新版 |

当前只发布五个有清楚边界的 Skill。后续只有在真实使用中反复出现独立任务时，才新增模块，不为了数量制造空插件。

## 知识库

TC 内置 16 份按需读取的参考资料，核心是“问对问题，再解决问题”，并覆盖创业链条、内容到收入、X 增长、收入记分、案例复盘、外部知识源路由、实操资料提炼、跨平台分发、反馈与公开边界等主题。

- [知识库导航](知识库/README.md)
- [来源与验证规则](知识库/来源与验证.md)
- [案例录入模板](知识库/案例录入模板.md)
- [知识原子录入模板](知识库/知识原子录入模板.md)
- [外部知识源接入](知识库/外部知识源接入.md)

知识库不把观点伪装成事实。动态平台规则、法律、投资、医疗、价格与业务数据必须在使用时重新核对。

### 知识源怎么分工

```text
用户的飞书 / Notion / 当前状态页：今天仍然有效吗
用户的内容与数据归档：过去真实发生过什么
TC 内置知识包：现在应该怎样判断和行动
```

TC 只按当前问题读取最小必要资料，不会自动收集用户全部对话，也不会把私有知识库打包进公开仓库。

## 项目结构

```text
tc/
├── skills/                    # 5 个正式 Skill
│   ├── tc/                    # 渐进式主入口
│   ├── tc-diagnosis/          # 问题重构与定义
│   ├── tc-copy/               # 商业文案
│   ├── tc-action/             # 行动推进
│   └── tc-update/             # 官方更新
├── 知识库/                    # 导航、来源规则与案例录入规范
├── .codex-plugin/             # Codex 插件元数据
├── .claude-plugin/            # Claude Code 市场清单
├── tools/                     # 构建、版本同步与完整性校验
├── tests/                     # 行为验收场景
└── VERSION                    # 唯一公开版本号
```

## 版本规则

TC 使用 `主版本.次版本.修订号`：

- `1.0.1`：修正文案、路由或小问题，兼容原用法。
- `1.1.0`：增加新能力或新 Skill，原调用方式仍可用。
- `2.0.0`：出现不兼容的结构或行为变化。

准备新版本：

```bash
python3 tools/release.py prepare 1.3.0
python3 tools/check.py
python3 tools/build.py
```

推送 `v1.3.0` 标签后，GitHub Actions 会校验版本、构建安装包并创建 GitHub Release。

## 与 DBS 的关系

TC 可以与 [dontbesilent 的 dbskill](https://github.com/dontbesilent2025/dbskill)协同，但不是其官方组成部分。TC 不复制或重新分发 DBS 的 Skill 正文；DBS 适合深度诊断，TC 负责继续推进文案、市场动作和收入证据。

## 贡献与反馈

提交案例或改进前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。Skill 不会自动把用户对话发送给作者；只有用户明确同意时，才可以把脱敏反馈发送至 `1179884054@qq.com`。

## License

本项目采用 [Apache License 2.0](LICENSE)。引用第三方方法时，仍需遵守对应来源的许可证与署名要求。
