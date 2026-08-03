# Agent Installation Guide

This project is designed so that anyone who can chat with an AI agent can install and configure it. No shell or programming skills are required.

## One-line prompt for the user

Paste this into your agent (Codex, Claude, etc.):

```text
Set up codex-free-vision-bridge for me. Read AGENT_INSTALL.md and follow it end to end. Use the free Zhipu provider unless I choose another one.
```

## Checklist for the agent

1. Locate the repository or clone it locally. Do not modify files outside the project unless a step below explicitly requires a backed-up Codex config change.
2. Ask the user which vision provider they want: `zhipu` (free), `dashscope`, `openai`, `gemini`, `groq`, `siliconflow`, or `openrouter`. Ask the user to provide the matching API key, or let them paste it into `.env` themselves.
3. Copy `.env.example` to `.env`, write `VISION_API_KEY`, and set `VISION_BASE_URL` / `VISION_MODEL` from the chosen preset (see `python vision_bridge.py providers`). Prefer using `--provider <id>` at runtime so no endpoint values need to be hardcoded.
4. Verify the pipeline:

   ```bash
   python vision_bridge.py doctor
   python vision_bridge.py see examples/sample-error-dialog.png -q "What error is shown?"
   ```

5. Optional: enable pasted screenshots in Codex.
   - Back up `~/.codex/config.toml` before changing it.
   - Point only the DeepSeek provider `base_url` at `http://127.0.0.1:19100/v1`.
   - If the desktop client rejects pasted images, the model catalog marks the model text-only. With a backup, set `input_modalities` to `["text", "image"]` for the model entry (CC Switch users: `cc-switch-model-catalog.custom.json`).
   - Start the proxy hidden and verify the port:

     ```bash
     python vision_bridge.py proxy --listen 127.0.0.1:19100 --upstream https://api.deepseek.com
     ```

   - Confirm `127.0.0.1:19100` is listening, then ask the user to fully quit and restart Codex.
6. Custom provider: if the user wants a provider not in the presets, create `providers.json` from `providers.example.json` with their endpoint, then use `--provider <id>`. Do not ask the user to write JSON; the agent creates and validates it.
7. Never commit or upload `.env`. Report the chosen provider, the verification result, and any files that were backed up.

## Rollback

- Codex config: restore the `config.toml` backup.
- Model catalog: restore the `cc-switch-model-catalog.custom.json` backup.
- Proxy: stop the process listening on `127.0.0.1:19100`.

## Rules for the agent

- Ask before changing global Codex configuration; never do it silently.
- Keep API keys inside the local `.env`; never print them.
- If verification fails, stop and explain the error instead of guessing.
