# codex-free-vision-bridge

给 Codex 里的 DeepSeek 等纯文本模型补“看图”能力的免费最小方案：图片交给免费视觉模型（默认智谱 `glm-4v-flash`）转成文字，DeepSeek 只负责推理。不用 Ollama、不用 GPU、不用换模型。

> 说明：项目里的测试图 `sample-error-dialog.png` 本身画有“401 Unauthorized”，视觉模型读出的只是图片内容，不是 API 报错。

## 架构

```text
Codex（DeepSeek 纯文本模型）
  |
  |-- see 模式：图片路径 -> vision_bridge.py see -> 视觉模型 -> 文字 -> DeepSeek 推理
  |
  |-- proxy 模式：Codex -> http://127.0.0.1:19100 -> 图片转文字 -> DeepSeek 上游
```

两种模式共用同一个 `.env` 和同一个视觉 API key；代理模式只是把“图片转文字”自动放进请求链路。

## 快速开始

### 前置要求

- Python 3.8+（只用标准库，无需 pip 安装任何包）
- 一个 OpenAI 兼容视觉 API key；默认智谱 `glm-4v-flash`（免费）

### 1. 配置 `.env`

```bash
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```

打开 `.env`，填入 `VISION_API_KEY`：

```bash
VISION_API_KEY=你的完整Key
VISION_BASE_URL=https://open.bigmodel.cn/api/paas/v4
VISION_MODEL=glm-4v-flash
```

智谱 Key 格式是 `{API Key ID}.{secret}`，**不需要加引号**，脚本会自动去掉值两侧的引号和空格。

### 2. 按需识图（先验证链路）

```bash
python vision_bridge.py doctor
python vision_bridge.py see examples/sample-error-dialog.png -q "这个截图里有什么错误，错误码是什么"
python vision_bridge.py see examples/sample-order-success.png -q "订单号和金额是多少"
```

`examples/` 里有两张程序生成的测试图（登录报错对话框、支付成功页）。模型能准确读出里面的文字，就说明 key 和调用链路都已打通。

### 3. 接入 Codex 粘贴图片（可选，需要改全局配置）

这一步让“在 Codex 输入框直接贴截图”也能自动转文字。它需要修改全局 `~/.codex/config.toml`，本仓库**不会自动修改**，请先备份再手动改。

1. 启动本地代理：

   ```bash
   python vision_bridge.py proxy \
     --listen 127.0.0.1:19100 \
     --upstream https://api.deepseek.com
   ```

2. 备份并编辑 `~/.codex/config.toml`，把你当前 DeepSeek provider 的 `base_url` 改成：

   ```toml
   base_url = "http://127.0.0.1:19100/v1"
   ```

3. 重启 Codex，粘贴一张截图测试。
4. 想回滚时，把 `base_url` 恢复为原值，或直接还原步骤 2 的备份。

代理会原样透传 Codex 的 Authorization，所以 DeepSeek key 不需要在代理里再保存一份；相同图片+问题只调用一次视觉 API；视觉服务不可用时 fail-open，原请求原样转发，不影响正常聊天。

注意：Codex 桌面端是否允许纯文本模型接收“粘贴图片”，取决于客户端实现。如果粘贴仍报 `unknown variant image_url` 或 `view_image is not allowed`，说明客户端在更早的层级拒绝了图片；此时请用 `see` 模式（给 agent 配 `SKILL.md`），或参考“方案来源”里的 hooks 方案。

## CLI 参考

```bash
# 按需识图
python vision_bridge.py see <图片路径>... [-q "问题"] [--model xxx] [--base-url xxx] [--api-key xxx] [--no-cache]

# 本地图片转文字代理
python vision_bridge.py proxy --listen 127.0.0.1:19100 --upstream <DeepSeek或本地relay地址>

# 检查配置
python vision_bridge.py doctor
```

## 换视觉模型

免费 `glm-4v-flash` 对清晰截图、界面文字、报错信息表现不错；复杂图表、小字体、密集布局会差一些。可以在 `.env` 里切换：

```bash
VISION_MODEL=glm-4.6v-flash        # 免费，高峰期可能 429
VISION_MODEL=qwen-vl-max           # DashScope，按量
VISION_MODEL=gpt-4o-mini           # OpenAI，按量
```

同时把 `VISION_BASE_URL` 换成对应服务的 OpenAI 兼容地址即可，桥接代码不用改。

## 常见问题

### 为什么零第三方依赖？

OpenAI 兼容接口本质是“往 HTTP 地址 POST 一段 JSON”。Python 标准库的 `urllib`、`json`、`http.server` 足够完成发请求、解析响应和本地代理，所以不需要安装 requests、openai 等任何包。

### 效果会很差吗？

识别质量由视觉模型决定，桥接层只负责转述，不会额外拉低效果。觉得不够就换更强或更贵的模型对比。

### 免费模型限流怎么办？

`glm-4v-flash` 高峰期可能返回 429。脚本自动指数退避重试 3 次；仍失败时代理模式 fail-open，把原请求直接转发给 DeepSeek。

### 中文乱码 / UnicodeEncodeError？

Windows 控制台默认编码可能不是 UTF-8；脚本启动时会强制 `stdout/stderr` 使用 UTF-8。如果你手动调用其他脚本仍有问题，先运行 `chcp 65001` 或设置 `PYTHONIOENCODING=utf-8`。

### 视觉 API 请求不通？

本机有代理时，检查 `HTTP_PROXY` / `HTTPS_PROXY` 是否设置；`urllib` 默认会读取这些环境变量。也可以先用 `python vision_bridge.py doctor` 确认 key 已读取。

## 隐私

图片只会发送到你配置的视觉服务商（默认智谱）。敏感截图（含 token、聊天记录、密钥）请先自行评估；`.env` 已被 `.gitignore` 排除，不要提交或分享。

## 验证

```bash
python vision_bridge.py doctor
python vision_bridge.py see 任意图片.png -q "描述这张图"
python -m unittest discover -s tests -v
```

## 方案来源与致谢

“本地代理 + 把 Codex base_url 指向代理 + 图片转文字”这个架构不是本仓库原创，参考了：

- [Anionex/codex-vision-proxy](https://github.com/Anionex/codex-vision-proxy)：Codex 请求经本地代理改写图片、透传 Authorization、同图缓存；
- [tkr520521/codex-vision-bridge](https://github.com/tkr520521/codex-vision-bridge)：同样使用 `127.0.0.1:19100` 与 base_url 指向代理，并补 hooks 兜底；
- [ErlichLiu/deepseek-vision](https://github.com/ErlichLiu/deepseek-vision)：OpenAI / Anthropic 兼容代理思路；
- [Jedeiah/codex-read-image](https://github.com/Jedeiah/codex-read-image)：图片转视觉 API 的脚本思路。

本仓库的价值是做了一个更小、可自测、不自动改全局配置的实现：`see` CLI、UTF-8 修复、缓存、fail-open、单元测试和中文文档。

## License

MIT
