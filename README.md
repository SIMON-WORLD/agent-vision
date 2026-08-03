# codex-free-vision-bridge

Give text-only Codex models (DeepSeek V4, GLM, MiMo) image understanding through a free OpenAI-compatible vision API. The vision model turns images into text; the main model keeps reasoning. No Ollama, no GPU, no model swap.

## Features

- Single-file Python, zero third-party dependencies
- On-demand `see` CLI and a local image-strip proxy for pasted screenshots
- Defaults to Zhipu `glm-4v-flash` (free); any OpenAI-compatible vision API works
- Passes the original Authorization header through, so the DeepSeek key stays in Codex config
- Per-image + prompt cache, fail-open behavior, UTF-8 safe on Windows
- Unit-tested image rewriting for OpenAI Chat Completions and Responses payloads

## Architecture

```text
Codex (text-only model)
  |
  |-- see mode: image path -> vision_bridge.py see -> vision model -> text -> model reasons
  |
  |-- proxy mode: Codex -> http://127.0.0.1:19100 -> image rewritten to text -> DeepSeek upstream
```

Both modes share the same `.env` and vision API key. Proxy mode automates the image-to-text step inside the request path.

## Quick Start

### Prerequisites

- Python 3.8+
- An OpenAI-compatible vision API key (Zhipu `glm-4v-flash` is free)

### 1. Configure `.env`

```bash
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```

```bash
VISION_API_KEY=your-full-key
VISION_BASE_URL=https://open.bigmodel.cn/api/paas/v4
VISION_MODEL=glm-4v-flash
```

Zhipu keys use the `{API Key ID}.{secret}` format. Do not add quotes; the loader strips surrounding quotes and whitespace.

### 2. Verify the pipeline

```bash
python vision_bridge.py doctor
python vision_bridge.py see examples/sample-error-dialog.png -q "What error is shown and what is the error code?"
python vision_bridge.py see examples/sample-order-success.png -q "What is the order number and amount?"
```

`examples/` contains two generated screenshots: an error dialog and an order-success page. If the model reads them correctly, the key and pipeline work.

### 3. Enable pasted screenshots in Codex (optional)

This requires editing the global `~/.codex/config.toml`. The repository never modifies that file automatically; back it up first.

1. Start the proxy:

   ```bash
   python vision_bridge.py proxy \
     --listen 127.0.0.1:19100 \
     --upstream https://api.deepseek.com
   ```

2. Back up and edit `~/.codex/config.toml`, then point the DeepSeek provider `base_url` at the proxy:

   ```toml
   base_url = "http://127.0.0.1:19100/v1"
   ```

3. Restart Codex and paste a screenshot.
4. To roll back, restore the original `base_url` or the backup from step 2.

Known limitation: whether the Codex desktop client delivers pasted images to the API depends on the client implementation. If it still reports `unknown variant image_url` or blocks `view_image`, use `see` mode with `SKILL.md` instead.

## CLI Reference

```bash
# On-demand image analysis
python vision_bridge.py see <image>... [-q "question"] [--model MODEL] [--base-url URL] [--api-key KEY] [--no-cache]

# Local image-strip proxy
python vision_bridge.py proxy --listen 127.0.0.1:19100 --upstream <origin>

# Configuration check
python vision_bridge.py doctor
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `VISION_API_KEY` | - | Vision API key (required) |
| `VISION_BASE_URL` | `https://open.bigmodel.cn/api/paas/v4` | OpenAI-compatible endpoint |
| `VISION_MODEL` | `glm-4v-flash` | Vision model name |

## Model Selection

The free `glm-4v-flash` handles clear screenshots, UI text and error messages well. For dense charts or small text, switch to a stronger model without touching the bridge:

```bash
VISION_MODEL=glm-4.6v-flash        # free, may hit rate limits
VISION_MODEL=qwen-vl-max           # DashScope
VISION_MODEL=gpt-4o-mini           # OpenAI
```

Update `VISION_BASE_URL` to the matching OpenAI-compatible endpoint.

## Testing

```bash
python -m unittest discover -s tests -v
```

## Troubleshooting

- **HTTP 429**: the free model is rate limited; retries are built in, or switch back to `glm-4v-flash` / a different model.
- **Garbled Chinese output on Windows**: the script forces UTF-8 on stdout/stderr; if other tools misbehave, run `chcp 65001` or set `PYTHONIOENCODING=utf-8`.
- **Vision API unreachable**: check `HTTP_PROXY` / `HTTPS_PROXY`; `urllib` reads them by default.
- **Pasted image still rejected**: the client rejected the image before the proxy saw it; use `see` mode.
- **Vision service failure**: proxy mode fails open and forwards the original request unchanged.

## Privacy & Security

Images are sent only to the configured vision provider (Zhipu by default). Do not send sensitive screenshots before reviewing the provider policy. `.env` is gitignored; never commit or share it.

## Roadmap

- Client-side hooks fallback for clients that reject pasted images
- English and Chinese docs parity
- CI pipeline for unit tests
- Additional free vision backends

## License

MIT
