# Agent Strata

Strata 为 Codex 和 Claude Code 编排原生子代理。先满足代码质量和工程验收要求，再比较能通过验收的方案，尽量缩短交付时间，节省 token 和代理额度。

## Codex 怎么选模型

| 任务 | 首选模型与强度 | 角色 |
|---|---|---|
| 已知路径的短操作、小型顺序改动 | 主控直接完成 | — |
| 定位调用方或测试、提取日志证据、执行明确命令 | GPT-6 Luna `low/medium` | `scout` / `executor` |
| 需要读代码、修改并跑测试的常规修复、功能和重构 | GPT-6.1 Sol `medium` | `worker` |
| 改法已知、可快速验收的小改动 | GPT-6.1 Sol `low` 或显式选择 Terra `medium` | 按任务派发 |
| 范围明确的写作、视觉和计算机操作 | GPT-6.1 Terra `medium/high` | 按任务派发 |
| 复杂实现、跨模块根因分析 | GPT-6.1 Sol `high`，首轮直接用 | `deep_worker` |
| 不变量不明、证据冲突、回滚代价高或需要关键独立审查 | GPT-6.1 Sol `xhigh` | `deep_worker` / `reviewer` |

主控始终跟随你在 CLI 或 App 中当前选定的模型和推理强度。Astra 仅供你手动选择为主控。子代理按任务使用 Luna、Terra 或 Sol。Claude Code 使用独立的原生角色配置。 [Claude Code 配置](skills/strata/references/claude.md)

## 成本、耗时和输出 token

以下是 2026-11-13 核对的 Artificial Analysis Intelligence Index v5.0.1 数据。三项用量均按基准单任务统计，输出包含推理和回答。 [完整数据与来源](skills/strata/references/cost-control.md)

| 模型与强度 | Intelligence Index | 成本（美元） | 耗时（分钟） | 输出 token |
|---|---:|---:|---:|---:|
| Luna low | 10 | 0.01 | 0.6 | 3.3k |
| Luna medium | 18 | 0.04 | 3.5 | 19.8k |
| Sol low | 35 | 0.16 | 2.0 | 5.84k |
| Terra medium | 38 | 0.17 | 2.9 | 10.9k |
| Sol medium | 46 | 0.36 | 4.5 | 13.5k |
| Sol high | 50 | 0.59 | 7.7 | 22.6k |
| Sol xhigh | 52 | 0.76 | 10.5 | 30.2k |

Sol medium 在 Terminal-Bench 4.0 上为 48.0%，Terra medium 为 32.3%。Terra medium 在 FrontierCode-AA 2.0 略高。结合实际修复耗时，普通修复默认用 Sol medium，按首次验收、重试和交付总耗时校准。基准美元成本与客户端额度分别统计。 [编码基准对照](https://artificialanalysis.ai/models/comparisons/gpt-6-1-terra-medium-vs-gpt-6-1-sol-medium)

## 怎么并行

先明确验收命令和写入范围。普通修复可让 Luna 查找既有用例，同时让 Sol medium 处理独立的实现工作。若实现依赖根因结论，先完成诊断。提交前由主控整合并执行所需检查。

并行耗时按最长依赖路径估算，加上交接、整合和验证。用量合计主控、子代理与重试。默认一个写入者，多写入者须拥有互不重叠的路径、固定的共享契约和独立验证。任务包只带相关证据和文件位置。 [详细编排规则](docs/orchestration.md)

## 安装与更新

快照安装适合单个客户端：

```bash
npx -y skills@1.5.23 add SanStone3/agent-strata -g -a codex -s strata -y
```

多个 CLI、App 和项目共用时，建议将技能目录链接到同一个跟踪 GitHub `main` 的 checkout。发布后同步一次，所有链接都会指向新版。需要在首次使用时跟进其他机器的发布，可在客户端全局规则里加一条同步指令。各登录入口保留自己的 `CODEX_HOME`、代理定义和模型绑定。 [共享安装和更新步骤](docs/installation.md)

安装后可对 Codex 说「用 `$strata` 编排这个任务」。如果要同时启用命名角色，先按目标客户端解析并生成暂存配置，再增量合并。技能安装只负责发现技能，命名角色需要单独配置。 [命名角色配置与验证](skills/strata/references/install.md)

## 解析与验证

```bash
# 读取当前客户端的模型清单，解析子代理绑定。
python3 skills/strata/scripts/resolve_models.py --discover

# 已有同客户端目录时，为高风险实现指定 Sol xhigh。
python3 skills/strata/scripts/resolve_models.py --catalog /path/to/models.json \
  --role deep_worker --effort deep_worker=xhigh

# 在仓库干净副本中校验发布内容与路由。
python3 -m pip install -r requirements-dev.txt
python3 skills/strata/scripts/validate.py --repo .
python3 -m unittest discover -s tests
```

解析器验证模型与强度是否受当前清单支持。用 `--output-dir` 生成命名角色配置，配置合并后读回实际绑定。实际推理能力通过获准的原生任务验证。 [解析参数](skills/strata/references/model-routing.md) · [验证等级](skills/strata/references/validation.md)

[MIT License](LICENSE)
