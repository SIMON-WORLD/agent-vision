# Agent 安装指南

仓库地址：https://github.com/SIMON-WORLD/codex-deepseek-vision

这个项目设计给“只要会和 AI Agent 聊天”的用户：不需要会终端，也不需要会编程。

## 用户一句话指令

把下面这句话发给你的 Agent（Codex、OpenCode 等）：

```text
帮我安装并配置 agent-vision。请阅读 AGENT_INSTALL.zh-CN.md 并从头到尾执行。默认使用智谱免费服务，除非我指定其他服务商。
```

## Agent 执行清单

1. 从 PyPI 安装（最简单）；如果 PyPI 不可达，再克隆仓库从源码安装：

   ```bash
   pip install agent-vision
   # 或
   git clone https://github.com/SIMON-WORLD/codex-deepseek-vision.git
   cd codex-deepseek-vision
   pip install .
   ```

   除非下面步骤明确要求修改 Agent 配置，否则所有写入都留在项目目录内。

3. 询问用户选择视觉服务商：`zhipu`（免费）、`dashscope`、`openai`、`gemini`、`groq`、`siliconflow`、`openrouter`，或自定义 OpenAI 兼容接口。请用户提供对应的 API Key，或让用户自己粘贴到用户配置目录的 `.env`（`~/.agent-vision/.env`，Windows 为 `%USERPROFILE%\.agent-vision\.env`）。
4. 运行引导式配置：

   ```bash
   agent-vision setup
   ```

   向导会自动检测已安装的 Agent，在用户配置目录写入 `.env`（自定义服务商还会写 `providers.json`），启动本地运行时并验证视觉 API。对 Codex 会先备份，且只改写当前活动 provider 的 `base_url`（绝不改 `wire_api`、模型或 Key）；若 Codex 通过本地模型目录（如 cc-switch）加载模型列表，还会为当前模型声明图片输入，客户端才会允许粘贴图片（同样带备份）。对 OpenCode 会自动添加 OpenAI 兼容 provider。
5. 明确验证链路：

   ```bash
   agent-vision status
   agent-vision see <图片路径> -q "What is in this image?"
   agent-vision see https://example.com/image.png --task ocr
   agent-vision see --latest
   ```

   对 Codex，还建议让用户粘贴一张图片，或让 Agent 用内置 `view_image` 打开本地图片；两者都会经过本地代理，应返回文字描述而不是 modality 报错。

6. 如果用户之后要求回滚被自动修改的 Agent：

   ```bash
   agent-vision rollback codex
   agent-vision rollback opencode
   ```

7. 对 Claude Code 和 Cursor，执行 `agent-vision setup --agent claude --dry-run` 与 `agent-vision setup --agent cursor --dry-run` 会打印官方手动步骤。不要为这两个 Agent 编造配置键。
8. 绝不提交或上传 `.env`。API Key 只放在用户配置目录，不要放进仓库。最后向用户汇报：选择的服务商、验证结果、备份了哪些文件。

## Agent 守则

- 修改全局 Agent 配置前必须先征得用户同意；每次自动修改前都会先生成带时间戳的备份。
- API Key 只放在本地 `.env`，绝不打印。
- 验证失败就停下来解释原因，不要猜测。
