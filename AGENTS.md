# TC 项目维护规则

## 产品真源

- TC 的核心目标：先用天策的价值观与逻辑，引导用户找到真正想问、真正需要解决的问题，再给出解决办法。
- `/tc` 是唯一需要普通用户记住的公开入口。
- `skills/tc/SKILL.md` 保存主流程；详细知识按需放在 `skills/tc/references/`。
- `VERSION` 是公开版本号的唯一真源。

## 修改规则

1. 不为了增加数量创建没有独立任务边界的 Skill。
2. 不把用户的表面请求直接当成真实需要，也不把简单问题强行复杂化。
3. 不编造案例、收入、评价、知识原子数量或官方合作关系。
4. 动态平台规则、商业数据和人物状态在使用时重新核对，不永久写死。
5. 知识只保留一份权威正文；SKILL.md 负责路由，不重复大段参考资料。
6. 新案例公开前必须脱敏，并记录来源、日期、动作、结果与适用边界。

## 发布前检查

```bash
python3 tools/check.py
python3 tools/build.py
npx -y skills add . --list
```

同时使用 Skill Creator 与 Plugin Creator 的校验器检查全部 Skill 和 `.codex-plugin/plugin.json`。版本发布前运行 `python3 tools/release.py prepare X.Y.Z`，提交后再推送同名 `vX.Y.Z` 标签。
