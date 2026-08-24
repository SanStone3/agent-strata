# 安装与作用域

本页区分三件事：安装 skill、安装 Agent 定义、合并客户端配置。只有三者都完成，主会话才能稳定地自主分层编排。

## 前置条件

- 已安装并登录 Codex 或 Claude Code。
- Node.js 环境能运行 `npx skills`；也可以完全手工安装。
- 使用模板中的模型前，账号与组织策略允许访问对应模型。
- 修改全局配置会影响本机当前用户的所有项目；修改项目配置应由仓库维护者确认并提交。

## 推荐：让 AI 安装

### 第一步：安装 skill

全局安装到两端：

```bash
npx -y skills@1.5.23 add SanStone3/agent-strata \
  -g -a codex claude-code -s layered-orchestration -y
```

项目级安装：

```bash
cd /path/to/project
npx -y skills@1.5.23 add SanStone3/agent-strata \
  -a codex claude-code -s layered-orchestration -y
```

### 第二步：分别让客户端合并配置

在 Codex 中：

```text
使用 layered-orchestration skill，把 Agent Strata 配置安装到 Codex，全局生效。
检查现有 ~/.codex/config.toml、~/.codex/agents 和全局 AGENTS.md；
先备份，再按 skill 中的 Codex 模板增量合并。不要删除或覆盖现有项目、MCP、hooks、权限和其他模型配置。
写代码的 Worker 必须使用 xhigh；完成后运行只读校验并显示实际变更。
```

在 Claude Code 中：

```text
使用 layered-orchestration skill，把 Agent Strata 配置安装到 Claude Code，全局生效。
检查现有 ~/.claude/settings.json、~/.claude/agents 和 ~/.claude/CLAUDE.md；
先备份，再按 skill 中的 Claude 模板增量合并。默认 Opus 1M + xhigh，保留 Fable 显式角色；
不要覆盖现有 permissions、plugins、hooks 或 MCP。完成后运行只读校验并显示实际变更。
```

项目级安装时，把目标路径换成仓库根目录下的 `.codex/`、`.claude/`、`AGENTS.md` 与 `CLAUDE.md`。

## 合并规则

AI 或人工安装都必须遵守：

1. 先读取当前文件，确认格式与既有内容。
2. 任何写入前创建带时间戳的备份；新建文件无需备份。
3. TOML 和 JSON 做键级合并，不整文件替换。
4. Agent 文件若同名存在，先比较；有用户定制时报告冲突，不静默覆盖。
5. `AGENTS.md` / `CLAUDE.md` 追加一个清晰、可移除的章节，不改写项目规则。
6. 不新增权限白名单、不降低 sandbox、不启用 bypass permissions。
7. 不配置跨厂商调用、API 密钥、后台桥接或互相启动 CLI。
8. 模型不可用时保留原配置并说明，不擅自换成另一个收费层级。
9. 修改后解析 TOML / JSON / YAML frontmatter，再进行客户端级 smoke check。
10. 用客户端状态确认实际 resolved model 与 effort。若 Claude alias 落到不支持 `xhigh` 的模型，pin 组织批准且支持 `xhigh` 的完整 ID，或明确报告安装未满足“代码 Worker xhigh”这一约束；不能只凭模板内容宣称成功。

## 手工安装

模板位于 `skills/layered-orchestration/assets/templates/`。以下命令展示目标位置，不建议在已有文件上直接 `cp`。

### Codex 全局

| 内容 | 源模板 | 目标 |
|---|---|---|
| Skill | `skills/layered-orchestration/` | `~/.agents/skills/layered-orchestration/` |
| 主配置片段 | `codex/config-snippet.toml` | 合并到 `~/.codex/config.toml` |
| Agent 定义 | `codex/agents/*.toml` | `~/.codex/agents/` |
| 编排规则 | `codex/AGENTS-snippet.md` | 合并到 `~/.codex/AGENTS.md` |

Codex 官方当前将个人 skill 位置定义为 `~/.agents/skills/`，项目位置为 `.agents/skills/`。一些既有安装器或旧环境仍可能显示 `~/.codex/skills/`；优先使用当前客户端和 `npx skills list -g --json` 实际报告的位置。

Codex 新建 Agent 目录后，重新启动会话以确保发现全部定义。

### Codex 项目级

| 内容 | 目标 |
|---|---|
| Skill | `<repo>/.agents/skills/layered-orchestration/` |
| 主配置片段 | `<repo>/.codex/config.toml` |
| Agent 定义 | `<repo>/.codex/agents/` |
| 编排规则 | `<repo>/AGENTS.md` |

Codex 仅为受信任项目加载项目 `.codex/` 配置层。不要通过模板替用户扩大信任范围。

### Claude Code 全局

| 内容 | 源模板 | 目标 |
|---|---|---|
| Skill | `skills/layered-orchestration/` | `~/.claude/skills/layered-orchestration/` |
| 主配置片段 | `claude/settings-snippet.json` | 合并到 `~/.claude/settings.json` |
| Agent 定义 | `claude/agents/*.md` | `~/.claude/agents/` |
| 编排规则 | `claude/CLAUDE-snippet.md` | 合并到 `~/.claude/CLAUDE.md` |

Claude Code 会监视已存在的 skill 和 Agent 目录。若会话启动时目录尚不存在，首次创建后应重启 Claude Code。

### Claude Code 项目级

| 内容 | 目标 |
|---|---|
| Skill | `<repo>/.claude/skills/layered-orchestration/` |
| 主配置片段 | `<repo>/.claude/settings.json` |
| Agent 定义 | `<repo>/.claude/agents/` |
| 编排规则 | `<repo>/CLAUDE.md` |

项目 `.claude/settings.json` 适合团队共享；个人试验与本机权限放在 `.claude/settings.local.json`，并确保它被忽略。

## 配置选择

### 推荐基线

- Codex 主会话：`gpt-5.6-sol`，`xhigh`，1M context，900k auto compact。
- Codex 默认子 Agent：`gpt-5.6-terra`，`xhigh`；Scout 显式覆盖为 Luna `medium`。
- Claude 默认主会话：`opus[1m]`，`xhigh`。
- Claude 常规实现：Sonnet `xhigh`；复杂实现/审查：Opus `xhigh`。
- Claude Fable：只作为显式 controller / worker / reviewer 使用。

### 什么时候不应照搬

- 账号没有 1M context 或对应模型访问权限。
- 组织通过 managed settings 限定模型或 effort。
- 项目对成本、延迟或数据驻留有更严格要求。
- 已有更具体、经过评测的模型路由。

此时应保留用户现状，只安装角色与编排规则，或把模板模型替换为组织批准的等价层级。

## 验证与卸载

验证仓库或已复制的模板：

```bash
python3 skills/layered-orchestration/scripts/validate.py --repo .
npx -y skills@1.5.23 list -g --json
```

验证本机已安装的活配置（模型、effort、工具列表、核心政策）：

```bash
python3 skills/layered-orchestration/scripts/validate.py --repo . --codex-home ~/.codex
python3 skills/layered-orchestration/scripts/validate.py --repo . --claude-home ~/.claude
```

客户端 smoke check：

- Codex：启动新会话，确认 skill 可见；让主会话列出可用 custom agents，不执行写入。
- Claude Code：运行 `/doctor`、`/status`，确认 skill 和 Agents 可发现；`/model` 检查实际模型与 effort。
- 若通过第三方 provider 使用 Claude，核对 alias 的实际模型版本；4.6 等不支持 `xhigh` 的模型会降到 `high`，此时不得把该层标记为已满足。
- 使用一个只读任务，要求 Scout 返回 3 个带文件证据的发现。
- 使用一个临时目录中的小改动，确认同一时刻只有一个 Worker 写入。

只卸载 skill：

```bash
npx -y skills@1.5.23 remove layered-orchestration -g -y
```

Agent 文件、配置片段和规则文件是独立安装的，卸载 skill 不会自动删除它们。应根据安装前备份与变更清单逐项回滚，避免删除同名但已被用户定制的内容。

本文使用的 `skills@1.5.23` 来自 [vercel-labs/skills](https://github.com/vercel-labs/skills)。固定版本是为了让安装行为可复现；升级 CLI 后应重新做临时项目安装测试。
