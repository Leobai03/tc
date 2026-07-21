# 安装包内知识副本

这里的 `atoms.jsonl`、`public-posts.jsonl`、概念词典、`core-sources/` 和 `knowledge-packs/` 都由仓库根目录 `知识库/` 自动同步，用于保证单独安装 `/tc-knowledge` 后仍能离线检索。

不要直接修改这些副本。维护者应修改根目录真源，然后运行：

```bash
python3 tools/sync_knowledge.py
```
