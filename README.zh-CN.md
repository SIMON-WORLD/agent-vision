# agent-vision

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Release](https://img.shields.io/badge/release-v1.0.0-brightgreen)](https://github.com/SIMON-WORLD/agent-vision/releases)

**给任何 AI Agent 加上看图能力。** 当你的 Agent 主模型是纯文本模型（DeepSeek V4、GLM、MiMo 等）时，agent-vision 通过一个 OpenAI 兼容的免费视觉 API 把图片转成文字，主模型继续负责推理。不需要 Ollama、不需要 GPU、不需要换模型。

[English](README.md) | **中文**

## 为什么需要

纯文本模型看不到你粘贴的截图、本地图片、图表和报错弹窗。换模型通常意味着更高成本或改变整个工作流。agent-vision 位于 Agent 和模型服务之间，自动完成转换：

- 在 Agent 里粘贴图片，本地代理会在请求到达纯文本模型之前把图片改写成文字。
- 让 Agent 查看文件时，`see` 命令会把图片发给视觉 API，返回可验证的事实描述。
- 保留你现有的模型、API Key 和工作流。全部本地化、可回滚，默认免费。

## Demo

![订单成功](examples/sample-order-success.png)
![报错弹窗](examples/sample-error-dialog.png)

```bash
agent-vision see examples/sample-order-success.png -q "What is the order number and amount?"
```

```text
===== examples/sample-order-success.png =====
The order number is 202608030013, and the amount is 520.00 yuan.
```

```bash
agent-vision see examples/sample-error-dialog.png -q "What error is shown and what is the error code?"
```

```text
===== examples/sample-error-dialog.png =====
The error shown is "Unauthorized" with the error code 401.
```

## 架构

```mermaid
flowchart LR
  U[用户粘贴图片] --> A[任意 AI Agent]
  A -->|带图片的请求| P[agent-vision 代理 :19100]
  P --> V[OpenAI 兼容视觉 API]
  V -->|文字描述| P
  P -->|纯文本请求| M[DeepSeek / 纯文本模型]
```

`see` 模式不需要代理：直接把图片路径发给视觉 API，把返回文字交给 Agent 使用。

## 支持的 Agent

| Agent | 接入方式 | 状态 |
|---|---|---|
| Codex | 自动修改 `~/.codex/config.toml`，一键配置、备份、回滚 | 全自动 |
| OpenCode | 自动在 `opencode.json` 里添加 OpenAI 兼容 provider | 全自动 |
| Claude Code | 检测并给出指引；Claude 使用 Anthropic 协议，需要协议兼容网关 | 提供手动步骤 |
| Cursor | 检测并给出指引；Cursor 只在 Settings -> Models 里提供 Base URL 覆盖开关 | 提供手动步骤 |

## 支持的视觉服务商

agent-vision 接受任意 OpenAI 兼容视觉 API。内置常见服务商预设，也支持自定义接口。

| 服务商 | 模型示例 | 费用 |
|---|---|---|
| 智谱 | `glm-4v-flash`, `glm-4.6v-flash` | 免费 |
| 阿里百炼 | `qwen-vl-max`, `qwen3-vl-flash` | 按量 / 免费额度 |
| OpenAI | `gpt-4o-mini`, `gpt-4o` | 按量 |
| Google Gemini | `gemini-2.0-flash` | 有免费层 |
| Groq | Qwen 视觉模型 | 有免费计划 |
| 硅基流动 | Qwen2.5-VL 系列 | 新用户免费额度 |
| OpenRouter | 免费和付费视觉模型 | 混合 |
| 自部署 vLLM / Ollama | 任意 VLM | 仅硬件成本 |

## 安装

### 一键配置（推荐）

不需要懂终端。安装 Python 3.9+，克隆仓库后运行：

```bash
git clone https://github.com/SIMON-WORLD/agent-vision.git
cd agent-vision
pip install .
agent-vision setup
```

向导会自动检测你的 Agent，让你选择 Free / Quality / Custom 视觉服务，带备份写入配置，启动本地运行时，验证连接，最后输出健康状态。

也可以把下面这句话发给你的 AI Agent，让它替你完成：

```text
帮我安装并配置 agent-vision。请阅读 AGENT_INSTALL.zh-CN.md 并从头到尾执行。默认使用智谱免费服务，除非我指定其他服务商。
```

### 运行时管理

```bash
agent-vision start      # 后台启动本地视觉代理
agent-vision status     # 查看安装、运行时、服务商、Agent、视觉状态
agent-vision restart    # 重启本地代理
agent-vision stop       # 停止本地代理
```

### 回滚

```bash
agent-vision rollback codex
agent-vision rollback opencode
```

每次自动修改前都会先生成带时间戳的备份，`rollback` 会完整恢复。

## 配置

把 `.env.example` 复制为 `.env` 并填写视觉 API Key。智谱 Key 格式为 `{API Key ID}.{secret}`，不需要加引号；脚本会自动去掉值两侧的引号和空格。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `VISION_API_KEY` | - | 视觉 API Key（必填） |
| `VISION_BASE_URL` | `https://open.bigmodel.cn/api/paas/v4` | OpenAI 兼容接口地址 |
| `VISION_MODEL` | `glm-4v-flash` | 视觉模型名 |
| `VISION_PROXY_UPSTREAM` | - | 可选：本地代理转发的上游地址 |
| `VISION_PROXY_LISTEN` | `127.0.0.1:19100` | 可选：本地代理监听地址 |

需要自定义服务商时，让 Agent 在 `providers.json` 里添加即可，不需要改代码。同 id 的条目会覆盖内置预设。

## CLI 参考

```bash
# 按需识图
agent-vision see <图片路径>... [-q "问题"] [--provider ID] [--no-cache]

# 前台运行本地图片转文字代理
agent-vision proxy --listen 127.0.0.1:19100 --upstream <上游地址>

# 引导式配置
agent-vision setup [--agent codex|opencode|claude|cursor] [--dry-run]

# 健康状态
agent-vision status [--test]

# 运行时生命周期
agent-vision start | restart | stop

# 配置检查
agent-vision doctor

# 查看视觉服务商预设
agent-vision providers
```

## 测试

```bash
python -m unittest discover -s tests -v
```

## FAQ

- **需要 GPU 或 Ollama 吗？** 不需要。视觉部分由远程 OpenAI 兼容 API 完成，默认智谱 `glm-4v-flash` 免费。
- **主模型 API Key 会泄露吗？** 不会。代理原样透传 Authorization，主模型 Key 仍然只存在 Agent 原有配置里。
- **可以用付费服务吗？** 可以。在 setup 里选 Quality 或 Custom，或者直接改 `.env` / `providers.json`。
- **视觉 API 挂了会怎样？** 代理模式 fail-open，原请求原样转发，不会阻塞正常聊天。
- **图片隐私如何？** 图片只会发送到你配置的服务商（默认智谱）。发送敏感截图前请先查看对方隐私政策。`.env` 已被 `.gitignore` 排除，不要提交或分享。

## License

MIT
