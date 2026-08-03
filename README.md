# codex-free-vision-bridge

给 Codex 里的 DeepSeek 等纯文本模型补“看图”能力的免费最小方案。

原理：图片交给免费视觉模型（默认智谱 `glm-4v-flash`）转成文字描述，DeepSeek 只负责推理。不使用 Ollama，不需要 GPU，不需要换模型。

## 两种用法

### 1. 命令行按需识图（最简单）

```bash
python vision_bridge.py see 截图.png -q "描述这张图"
```

把 `vision_bridge.py` 所在目录复制到项目里，或在 Codex 中按 `SKILL.md` 让 agent 自动调用。

### 2. 本地代理自动转文字（粘贴图片无感）

```bash
python vision_bridge.py proxy \
  --listen 127.0.0.1:19100 \
  --upstream https://api.deepseek.com
```

然后把 Codex 的 `base_url` 指向 `http://127.0.0.1:19100/v1`，重启 Codex。代理会：

- 把请求里的图片内容块交给视觉模型，替换成文字描述后再转发给 DeepSeek；
- 原样透传 Codex 的 Authorization，DeepSeek key 不用二次保存；
- 相同图片+问题只调用一次视觉 API（进程内缓存）；
- 视觉服务不可用时 fail-open，原请求原样转发，不影响正常聊天。

## 免费视觉 Key

1. 注册 [智谱 BigModel 开放平台](https://open.bigmodel.cn/)；
2. 创建 API Key；
3. 复制 `.env.example` 为 `.env`，填入 `VISION_API_KEY`。

默认 `glm-4v-flash` 免费；高峰期限流可换 `glm-4.6v-flash` 或回到 `glm-4v-flash`。也可以把 `.env` 换成其他 OpenAI 兼容视觉服务（OpenAI、DashScope、SiliconFlow、本地 vLLM 等）。

## 快速体验（1 分钟）

```bash
python vision_bridge.py doctor
python vision_bridge.py see examples/sample-error-dialog.png -q "这个截图里有什么错误，错误码是什么"
python vision_bridge.py see examples/sample-order-success.png -q "订单号和金额是多少"
```

第一次运行需要先在 `.env` 里填好免费 Key。`examples/` 里有两张程序生成的测试图：一张是登录报错对话框（“401 Unauthorized”是画在图片里的内容，不是 API 报错），一张是支付成功页；模型能准确读出里面的文字就说明链路已通。

### `.env` 里 Key 要不要加引号

不用加引号，直接写 `VISION_API_KEY={API Key ID}.{secret}` 即可；脚本会自动去掉值两侧的引号和空格。智谱的完整 Key 是 `API Key ID` 和 `secret` 用点连接，例如 `VISION_API_KEY=abc123.xxxxxxxx`。

## 常见问题

### 为什么零第三方依赖？

OpenAI 兼容接口本质就是“往 HTTP 地址 POST 一段 JSON”。Python 标准库里的 `urllib`、`json`、`http.server` 足够完成发请求、解析响应和本地代理，所以不需要安装 requests、openai 等任何包，也就不存在环境依赖冲突。

### 效果会很差吗？

识别质量由你配置的视觉模型决定，桥接层只负责转述，不会额外拉低效果。免费 `glm-4v-flash` 对清晰截图、界面文字、报错信息表现不错；复杂图表、小字体、密集布局会差一些。如果实际效果不满足，把 `.env` 里的 `VISION_MODEL` 换成 `glm-4.6v-flash`（免费）、`qwen-vl-max` 或 `gpt-4o-mini` 再对比即可，桥不用改。

### 免费模型限流怎么办？

`glm-4v-flash` 高峰期可能返回 429。脚本会自动指数退避重试 3 次；仍然失败时代理模式会 fail-open，把原请求直接转发给 DeepSeek，不影响正常聊天。

## 验证

```bash
python vision_bridge.py doctor
python vision_bridge.py see 任意图片.png -q "描述这张图"
python -m unittest discover -s tests -v
```

## 与本机现有方案的差异

- 不修改全局 `~/.codex/config.toml`，不写开机自启，不装 hooks；代理或命令都只在项目内运行。
- 单文件 Python，零第三方依赖，Windows / macOS / Linux 通用。
- 不依赖 Ollama 等本地模型服务。
- 内置按“图片内容 + 问题”的进程内缓存，同一张图不会反复调用视觉 API。

## License

MIT
