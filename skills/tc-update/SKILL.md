---
name: tc-update
description: TC Skill 官方更新入口。用户输入“/tc-update”，或明确要求更新、升级、重新安装、检查并同步 TC Skill 最新版时使用。只从 Leobai03/tc 更新 TC 系列 Skill，不修改其他 Skill，不读取或上传用户聊天和业务资料。
---

# TC Update｜更新 TC

用户已经明确要求更新时，直接执行，不重复确认；宿主需要终端权限时，由用户在权限窗口决定。

## 更新步骤

1. 运行：

   ```bash
   npx -y skills add Leobai03/tc -g --all
   ```

2. 成功后读取仓库根目录 `VERSION`，告诉用户当前版本。当前对话未重新载入 Skill 时，提醒用户新建对话再使用。
3. 失败时只说明最短原因和用户需要处理的网络、权限或 Node.js 问题，不粘贴无关日志。

## 边界

- 只更新 `Leobai03/tc`。
- 不更新用户安装的其他 Skill。
- 不修改用户聊天、业务文件或本地存档。
- 用户只问版本或更新内容时，先回答，不自动执行更新。
