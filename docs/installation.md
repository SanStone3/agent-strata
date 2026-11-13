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

## 跟踪 GitHub 主分支

发布后同步一次共享 checkout。所有项目链接都指向同步后的文件。先确认 checkout 在 `main`，`origin` 指向目标仓库，工作树干净，再快进并核对提交。

```bash
git -C /path/to/agent-strata pull --ff-only origin main
git -C /path/to/agent-strata rev-parse HEAD origin/main
```

需要自动跟进其他机器的发布时，在客户端全局规则里指定共享路径。每个新任务首次使用 Strata 时执行上述检查和快进，同一任务后续直接复用。遇到离线、本地改动或分歧，保留现场并说明实际使用的版本。项目规则只引用共享技能。

技能链接随 checkout 更新。命名角色由各客户端加载，角色或模型策略变更时分别生成绑定并核验重载。 [客户端合并步骤](../skills/strata/references/install.md#merge-client-configuration)

Claude 的安装与角色策略保持独立，见 [Claude 配置](../skills/strata/references/claude.md)。验证命令与生效等级统一见 [validation.md](../skills/strata/references/validation.md)。卸载依据备份只撤回本次管理的链接和配置，不删除用户后续定制。
