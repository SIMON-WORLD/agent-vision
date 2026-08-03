# Agent 安装指南

这个项目设计的初衷就是：用户只要会跟 AI Agent 对话，就能完成安装和配置，不需要懂命令行或编程。

## 用户只需复制这一句话

把下面这句话发给你的 Agent（Codex、Claude 等都可以）：

```text
帮我安装并配置 codex-free-vision-bridge。请阅读 AGENT_INSTALL.zh-CN.md 并从头到尾执行。默认使用智谱免费服务，除非我指定其他服务商。
```

## Agent 执行清单

1. 找到或克隆本仓库。除下列明确要求且已备份的 Codex 配置改动外，不要修改项目以外的文件。
2. 询问用户想用哪个视觉服务商：`zhipu`（免费）、`dashscope`、`openai`、`gemini`、`groq`、`siliconflow`、`openrouter`。请用户提供对应的 API Key，或让用户自己把 Key 粘进 `.env`。
3. 复制 `.env.example` 为 `.env`，写入 `VISION_API_KEY`，并根据 `python vision_bridge.py providers` 的输出设置 `VISION_BASE_URL` / `VISION_MODEL`。优先用 `--provider <id>` 运行时指定，避免硬编码接口地址。
4. 验证链路：

   ```bash
   python vision_bridge.py doctor
   python vision_bridge.py see examples/sample-error-dialog.png -q "这个截图里有什么错误"
   ```

5. 可选：启用 Codex 粘贴图片。
   - 修改 `~/.codex/config.toml` 前先备份。
   - 只把 DeepSeek provider 的 `base_url` 指向 `http://127.0.0.1:19100/v1`。
   - 如果桌面端仍提示“不支持图片输入”，说明模型目录把该模型标成纯文本；备份后把对应模型条目的 `input_modalities` 改为 `["text", "image"]`（CC Switch 用户文件为 `cc-switch-model-catalog.custom.json`）。
   - 后台启动代理并确认端口：

     ```bash
     python vision_bridge.py proxy --listen 127.0.0.1:19100 --upstream https://api.deepseek.com
     ```

   - 确认 `127.0.0.1:19100` 在监听，然后请用户完全退出并重启 Codex。
6. 自定义服务商：如果用户要用的服务不在预设里，由 Agent 根据 `providers.example.json` 创建 `providers.json` 并校验，然后使用 `--provider <id>`。不要让用户手写 JSON。
7. 绝不提交或上传 `.env`。最后向用户汇报：选择了哪个服务商、验证结果、备份了哪些文件。

## 回滚

- Codex 配置：恢复 `config.toml` 备份。
- 模型目录：恢复 `cc-switch-model-catalog.custom.json` 备份。
- 代理：停止监听 `127.0.0.1:19100` 的进程。

## Agent 必须遵守

- 修改全局 Codex 配置前必须征求用户同意，不能静默修改。
- API Key 只留在本地 `.env`，不要打印出来。
- 验证失败时停下来解释错误，不要猜测。
