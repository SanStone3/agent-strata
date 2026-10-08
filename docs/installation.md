# 安装与作用域

本页区分三件事：安装 skill、安装 Agent 定义、合并客户端配置。只有三者都完成，主会话才能稳定地自主分层编排。

## 前置条件

- 已安装并登录 Codex 或 Claude Code。
- Node.js 环境能运行 `npx skills`；也可以完全手工安装。
- Codex 路由脚本需要 Python 3.10+，使用当前调用工具目录或匹配的 CLI `model/list`；账号与组织策略应允许所选模型。
- 修改全局配置会影响本机当前用户的所有项目；修改项目配置应由仓库维护者确认并提交。

## 推荐：让 AI 安装

### 第一步：安装 skill

全局安装到两端：

```bash
npx -y skills@1.5.23 add SanStone3/agent-strata \
  -g -a codex claude-code -s strata -y
```

项目级安装：

```bash
cd /path/to/project
npx -y skills@1.5.23 add SanStone3/agent-strata \
  -a codex claude-code -s strata -y
```

### 第二步：分别让客户端合并配置

在 Codex 中：

```text
使用 strata skill，把 Agent Strata 配置安装到 Codex，全局生效。
检查现有 ~/.codex/config.toml、~/.codex/agents 和全局 AGENTS.md；
先备份，再读取当前目录、保留用户固定型号，按 skill 的模型路由流程生成绑定并增量合并。不要删除或覆盖现有项目、MCP、hooks、权限和其他模型配置。
写代码的 Worker 必须使用 xhigh；保持默认并发预算（3 个子线程、1 个写入者），并核验实际生效的并行度。
完成后带 --bindings 运行只读校验并显示实际变更。主控设为最强可用深度层 + xhigh，尊重明确固定选择，保留上下文配置。
```

在 Claude Code 中：

```text
使用 strata skill，把 Agent Strata 配置安装到 Claude Code，全局生效。
检查现有 ~/.claude/settings.json、~/.claude/agents 和 ~/.claude/CLAUDE.md；
先备份，再按 skill 中的 Claude 模板增量合并。默认 Opus 1M + xhigh，保留 Fable 显式角色；
把 CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH 设为 1，并发上限保持客户端默认；
不要覆盖现有 permissions、plugins、hooks、env 或 MCP。完成后运行只读校验并显示实际变更。
```

项目级安装时，把目标路径换成仓库根目录下的 `.codex/`、`.claude/`、`AGENTS.md` 与 `CLAUDE.md`。

## 合并规则

AI 或人工安装都必须遵守：

1. 先读取当前文件，确认格式与既有内容。
2. 任何写入前创建带时间戳的备份；新建文件无需备份。
3. TOML 和 JSON 做键级合并，不整文件替换；环境变量写进已有的 `env` 对象内部，不替换整个对象。
4. Agent 文件若同名存在，先比较；有用户定制时报告冲突，不静默覆盖。
5. `AGENTS.md` / `CLAUDE.md` 追加一个清晰、可移除的章节，不改写项目规则。
6. 不新增权限白名单、不降低 sandbox、不启用 bypass permissions。
7. 并发控制按客户端处理：Codex 固定 `agents.max_concurrent_threads_per_session = 3` 并核验实际并行度；Claude Code 把 `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` 设为 `1`，并发上限保持客户端默认。除用户明确要求，不把上限调到默认预算之上，也不为了让某个上限生效而开启无关的 feature flag。
8. 不配置跨厂商调用、API 密钥、后台桥接或互相启动 CLI。
9. 模型不可用时保留原配置并说明，不擅自换成另一个收费层级。
10. 修改后解析 TOML / JSON / YAML frontmatter，再进行客户端级 smoke check。
11. 用客户端状态确认实际 resolved model 与 effort。若 Claude alias 落到不支持 `xhigh` 的模型，pin 组织批准且支持 `xhigh` 的完整 ID，或明确报告安装未满足“代码 Worker xhigh”这一约束；不能只凭模板内容宣称成功。
12. 报告里同时给出实际生效的并发上限与嵌套深度，而不只是写进配置的请求值。

## 手工安装

模板位于 `skills/strata/assets/templates/`。以下命令展示目标位置，不建议在已有文件上直接 `cp`。

### Codex 全局

| 内容 | 源模板 | 目标 |
|---|---|---|
| Skill | `skills/strata/` | `~/.agents/skills/strata/` |
| 主配置片段 | 解析器生成的 `config-snippet.toml` | 合并到 `~/.codex/config.toml` |
| Agent 定义 | 解析器生成的 `agents/*.toml` | `~/.codex/agents/` |
| 编排规则 | `codex/AGENTS-snippet.md` | 合并到 `~/.codex/AGENTS.md` |

Codex 官方当前将个人 skill 位置定义为 `~/.agents/skills/`，项目位置为 `.agents/skills/`。一些既有安装器或旧环境仍可能显示 `~/.codex/skills/`；优先使用当前客户端和 `npx skills list -g --json` 实际报告的位置。

Codex 安装前按 [模型路由流程](../skills/strata/references/model-routing.md) 运行解析器并生成暂存目录；不要直接复制未绑定模型的源码模板。合并时应用主控绑定（明确保留时除外），保留上下文设置和无关用户定制，连同路由引用一起迁移旧角色名。新建 Agent 目录后，重新启动会话以确保发现全部定义。

### Codex 项目级

| 内容 | 目标 |
|---|---|
| Skill | `<repo>/.agents/skills/strata/` |
| 主配置片段 | `<repo>/.codex/config.toml` |
| Agent 定义 | `<repo>/.codex/agents/` |
| 编排规则 | `<repo>/AGENTS.md` |

Codex 仅为受信任项目加载项目 `.codex/` 配置层。不要通过模板替用户扩大信任范围。

### Claude Code 全局

| 内容 | 源模板 | 目标 |
|---|---|---|
| Skill | `skills/strata/` | `~/.claude/skills/strata/` |
| 主配置片段 | `claude/settings-snippet.json` | 合并到 `~/.claude/settings.json` |
| Agent 定义 | `claude/agents/*.md` | `~/.claude/agents/` |
| 编排规则 | `claude/CLAUDE-snippet.md` | 合并到 `~/.claude/CLAUDE.md` |

Claude Code 会监视已存在的 skill 和 Agent 目录。若会话启动时目录尚不存在，首次创建后应重启 Claude Code。

### Claude Code 项目级

| 内容 | 目标 |
|---|---|
| Skill | `<repo>/.claude/skills/strata/` |
| 主配置片段 | `<repo>/.claude/settings.json` |
| Agent 定义 | `<repo>/.claude/agents/` |
| 编排规则 | `<repo>/CLAUDE.md` |

项目 `.claude/settings.json` 适合团队共享；个人试验与本机权限放在 `.claude/settings.local.json`，并确保它被忽略。

## 配置选择

### 推荐基线

- Codex 主会话：最强可用深度层 `controller` + `xhigh`；明确固定型号时用 `--pin controller=MODEL`，保留原主模型与 effort 时用 `--preserve-primary`；context 与 auto compact 始终保留。
- Codex 默认子 Agent：当前目录解析出的 `worker` 模型，`xhigh`；Scout / Executor 为效率层 `medium`，复杂实现与审查为深度层 `xhigh`。
- Claude 默认主会话：`opus[1m]`，`xhigh`。
- Claude 常规实现：Sonnet `xhigh`；复杂实现/审查：Opus `xhigh`。
- Claude Fable：只作为显式 controller / worker / reviewer 使用。
- 并发预算：3 个活跃子 Agent、1 个写入者；Codex 侧把 `agents.max_concurrent_threads_per_session` 固定为 3（该客户端默认本就是 4 线程含主线程），Claude Code 侧保持客户端默认的 20 并发上限，由编排规则约束实际用量。
- 嵌套深度：Claude Code `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH = 1`，让“子 Agent 不再派生孙 Agent”由客户端强制；Codex 无对应开关，只能靠 Agent 定义与规则章节。

### 什么时候不应照搬

- 账号没有 1M context 或对应模型访问权限。
- 组织通过 managed settings 限定模型或 effort。
- 项目对成本、延迟或数据驻留有更严格要求。
- 已有更具体、经过评测的模型路由。
- 团队工作流确实需要更宽的并行写入，此时应先按 `references/scaling.md` 的写域清单评估，再决定调高上限，并记录实际生效值。

此时应保留用户现状。Codex 使用用户 pins 或组织批准的路由策略重新解析；未满足的角色保持不可委派，不安装会继承未知模型的空模板。Claude 独立使用其原生配置。

## 验证与卸载

验证仓库或已复制的模板：

```bash
python3 skills/strata/scripts/validate.py --repo .
npx -y skills@1.5.23 list -g --json
```

验证本机已安装的活配置（模型、effort、工具列表、并发上限、嵌套深度、核心政策）：

```bash
python3 skills/strata/scripts/validate.py --repo . --codex-home ~/.codex \
  --bindings /path/to/model-bindings.json
python3 skills/strata/scripts/validate.py --repo . --claude-home ~/.claude
```

客户端 smoke check：

- Codex：启动新会话，确认 skill 可见；让主会话列出可用 custom agents，不执行写入。
- Claude Code：运行 `/doctor`、`/status`，确认 skill 和 Agents 可发现；`/model` 检查实际模型与 effort。
- 若通过第三方 provider 使用 Claude，核对 alias 的实际模型版本；4.6 等不支持 `xhigh` 的模型会降到 `high`，此时不得把该层标记为已满足。
- 使用一个只读任务，要求 Scout 返回 3 个带文件证据的发现。
- 使用一个临时目录中的小改动，确认同一时刻只有一个 Worker 写入。
- 派一个「比预算多一个 Agent」的只读波次，观察客户端真实并行度与拒绝行为（Claude Code 会返回 `Concurrent subagent limit reached` 并要求不要重试）。不要用写入者做这个测试。

只卸载 skill：

```bash
npx -y skills@1.5.23 remove strata -g -y
```

Agent 文件、配置片段和规则文件是独立安装的，卸载 skill 不会自动删除它们。应根据安装前备份与变更清单逐项回滚，避免删除同名但已被用户定制的内容。

本文使用的 `skills@1.5.23` 来自 [vercel-labs/skills](https://github.com/vercel-labs/skills)。固定版本是为了让安装行为可复现；升级 CLI 后应重新做临时项目安装测试。
