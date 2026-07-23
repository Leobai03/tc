# 安装包内知识副本

这里的 `atoms.jsonl`、`public-posts.jsonl`、概念词典、`core-sources/`、`knowledge-packs/` 和 `external-sources/` 来源卡都由仓库根目录 `知识库/` 自动同步，用于保证单独安装 `/tc-knowledge` 后仍能理解知识结构。

`external-sources/dbs-books.md` 只是一张来源卡。受 CC BY-NC 4.0 约束的 DBS 推文全文不会放进安装包，需要用户确认许可后从原作者仓库同步到本机。

维护者可以用 `dbs-candidate` 把3至5条相关 DBS 记录加工成不含正文的本机 L1 研究候选；用户也可以逐次授权，把 `tc-state export-evidence` 生成的脱敏文件交给 `candidate-add`。两类候选默认都写入 `~/.tc/knowledge-candidates/`，不自动上传、公开、商用或升级。

不要直接修改这些副本。维护者应修改根目录真源，然后运行：

```bash
python3 tools/sync_knowledge.py
```
