# Agent Installation Guide

Repository: https://github.com/SIMON-WORLD/codex-deepseek-vision

This project is designed so that anyone who can chat with an AI agent can install and configure it. No shell or programming skills are required.

## One-line prompt for the user

Paste this into your agent (Codex, OpenCode, etc.):

```text
Set up agent-vision for me. Read AGENT_INSTALL.md and follow it end to end. Use the free Zhipu provider unless I choose another one.
```

## Checklist for the agent

1. Locate the repository or clone it locally. Keep all writes inside the project unless a step below explicitly requires a backed-up agent config change.
2. Install the package:

   ```bash
   pip install .
   ```

3. Ask the user which vision provider they want: `zhipu` (free), `dashscope`, `openai`, `gemini`, `groq`, `siliconflow`, `openrouter`, or a custom OpenAI-compatible endpoint. Ask the user to provide the matching API key, or let them paste it into the user config directory's `.env` themselves (`~/.agent-vision/.env`, or `%USERPROFILE%\.agent-vision\.env` on Windows).
4. Run the guided setup:

   ```bash
   agent-vision setup
   ```

   The wizard detects the installed agent, writes `.env` (and `providers.json` for custom providers) into the user config directory, starts the local runtime, and verifies the vision API. For Codex it backs up and only rewrites the active provider's `base_url` (never `wire_api`, model or keys); when Codex loads its model list from a local model catalog (e.g. cc-switch), it also declares image input for the active model so the client accepts pasted images (with a backup). For OpenCode it adds the OpenAI-compatible provider automatically.
5. Verify the pipeline explicitly:

   ```bash
   agent-vision status
   agent-vision see <image-path> -q "What is in this image?"
   agent-vision see https://example.com/image.png --task ocr
   agent-vision see --latest
   ```

   For Codex, also ask the user to paste an image or ask the agent to open a local image with the built-in `view_image`; both go through the local proxy and should return a text description instead of a modality error.

6. If the user later asks to roll back an auto-patched agent:

   ```bash
   agent-vision rollback codex
   agent-vision rollback opencode
   ```

7. For Claude Code and Cursor, `agent-vision setup --agent claude --dry-run` and `agent-vision setup --agent cursor --dry-run` print the official manual steps. Do not invent config keys for these agents.
8. Never commit or upload `.env`. Keep API keys in the user config directory, not in the repository. Report the chosen provider, the verification result, and any files that were backed up.

## Rules for the agent

- Ask before changing global agent configuration; every auto-patch creates a timestamped backup first.
- Keep API keys inside the local `.env`; never print them.
- If verification fails, stop and explain the error instead of guessing.
