# 安装与作用域

推荐让所有项目共用一个跟踪远端 `main` 的 checkout。技能链接指向同一源目录；登录、provider 和模型绑定仍按客户端隔离。[完整安装 / 更新步骤](../skills/strata/references/install.md)。

| 内容 | Codex 全局 | 项目级 |
|---|---|---|
| Skill | `~/.agents/skills/strata` 或客户端已发现的位置 | `.agents/skills/strata` |
| 配置与角色 | 实际 `CODEX_HOME/config.toml`、`agents/` | `.codex/config.toml`、`.codex/agents/` |
| 规则 | 实际 `CODEX_HOME/AGENTS.md` | `AGENTS.md` |

每个客户端分别核对目录、备份并增量合并。不要覆盖主控模型 / effort / 上下文、认证、provider、权限、MCP 和 hooks。新规则只保留共享 skill 的指针，避免各项目重复固定型号表。项目本机配置遵循项目的忽略和提交规则。

可直接给 Codex 这段安装任务：

```text
使用 strata 安装或升级当前客户端的全局编排配置。
先读实际 CODEX_HOME 和现有定制，备份并增量合并。
主控始终跟随当前及后续 CLI/App 选择，不写入主控 model/effort。
子任务按复杂度选择模型和 effort，不设置 Strata 数字并发上限。
验证共享技能发现、角色绑定、权限和配置；不改认证/provider，不重启活动任务。
```

远端 main 的更新不会自动流入本地链接。维护时先检查工作树，再 fetch 和快进；有本地修改或分歧先检查，不 reset / stash 覆盖。技能数据改变后，为需要命名角色的客户端重新生成独立绑定并核验重载。没有后台更新或每轮联网开销。

Claude 的安装与角色策略保持独立，见 [Claude 配置](../skills/strata/references/claude.md)。验证命令与生效等级统一见 [validation.md](../skills/strata/references/validation.md)。卸载依据备份只撤回本次管理的链接和配置，不删除用户后续定制。
