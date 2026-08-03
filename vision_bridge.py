#!/usr/bin/env python3
"""codex-free-vision-bridge: free vision for text-only Codex models.

Two modes:

  see    -- CLI: describe/analyze local images via an OpenAI-compatible
            vision API. Defaults to Zhipu GLM-4V-Flash (free).

  proxy  -- local HTTP proxy that rewrites image content to text before
            forwarding the request to a text-only upstream (DeepSeek etc.).
            Codex points its base_url at this proxy; the proxy passes the
            original Authorization header through, so the DeepSeek key stays
            in Codex's existing config.

All vision calls use only Python standard library (urllib).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


ENV_FILE = Path(__file__).resolve().parent / ".env"
DEFAULT_VISION_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_VISION_MODEL = "glm-4v-flash"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGES_PER_REQUEST = 3
DEFAULT_DESCRIBE_PROMPT = (
    "Describe this image with exact facts: all visible text, UI elements, "
    "layout, colors, error messages, and any data you can read. "
    "Do not guess. Reply in Chinese unless the user asks otherwise."
)

PROVIDERS: dict[str, dict[str, str]] = {
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4v-flash",
        "cost": "free",
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-vl-max",
        "cost": "paid",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "cost": "paid",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
        "cost": "free-tier",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "qwen/qwen3.6-27b",
        "cost": "free-plan",
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen2.5-VL-72B-Instruct",
        "cost": "free-quota",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "qwen/qwen3-vl:free",
        "cost": "free-or-paid",
    },
}

CUSTOM_PROVIDERS_FILE = Path(__file__).resolve().parent / "providers.json"


def load_dotenv(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE file; skip comments and blank lines."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            result[key] = value
    return result


_DOTENV = load_dotenv(ENV_FILE)
_ENV = {**_DOTENV, **os.environ}


def cfg(name: str, default: str = "") -> str:
    value = _ENV.get(name)
    return value if value not in (None, "") else default


def load_custom_providers() -> dict[str, dict[str, str]]:
    """Load user-defined provider presets from providers.json."""
    result: dict[str, dict[str, str]] = {}
    if not CUSTOM_PROVIDERS_FILE.exists():
        return result
    try:
        data = json.loads(CUSTOM_PROVIDERS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"warning: cannot load {CUSTOM_PROVIDERS_FILE}: {error}", file=sys.stderr)
        return result
    items = data if isinstance(data, list) else data.get("providers", [])
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        result[str(item["id"])] = {
            "base_url": str(item.get("base_url", "")).strip(),
            "model": str(item.get("model", "")).strip(),
            "cost": str(item.get("cost", "")).strip(),
            "note": str(item.get("note", "")).strip(),
        }
    return result


def all_providers() -> dict[str, dict[str, str]]:
    merged = dict(PROVIDERS)
    merged.update(load_custom_providers())
    return merged


def resolve_provider(
    provider: str | None,
    base_url: str | None,
    model: str | None,
) -> tuple[str, str]:
    """Resolve base_url and model from --provider, explicit flags, then .env."""
    if provider:
        preset = all_providers().get(provider)
        if not preset:
            raise ValueError(f"unknown provider: {provider}")
        resolved_base = base_url or preset.get("base_url") or cfg("VISION_BASE_URL", DEFAULT_VISION_BASE_URL)
        resolved_model = model or preset.get("model") or cfg("VISION_MODEL", DEFAULT_VISION_MODEL)
    else:
        resolved_base = base_url or cfg("VISION_BASE_URL", DEFAULT_VISION_BASE_URL)
        resolved_model = model or cfg("VISION_MODEL", DEFAULT_VISION_MODEL)
    return resolved_base, resolved_model


def guess_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    if mime and mime.startswith("image/"):
        return mime
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }.get(Path(path).suffix.lower(), "image/png")


def encode_image(path: str) -> tuple[str, str]:
    mime = guess_mime(path)
    with open(path, "rb") as handle:
        data = handle.read()
    if not data:
        raise ValueError(f"empty image file: {path}")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"image too large: {len(data) / 1024 / 1024:.1f} MB")
    return mime, base64.b64encode(data).decode("ascii")


def data_url_from_bytes(mime: str, data: bytes) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def call_vision_model(
    *,
    mime: str,
    b64: str,
    prompt: str,
    base_url: str,
    api_key: str,
    model: str,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> str:
    """Call an OpenAI-compatible chat completions vision endpoint."""
    if not api_key:
        raise RuntimeError(
            "VISION_API_KEY is not configured; set it in .env or the environment"
        )
    base = base_url.rstrip("/")
    url = base if base.endswith("/chat/completions") else base + "/chat/completions"
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    if "glm" in model.lower():
        payload["thinking"] = {"type": "enabled"}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    retryable = {429, 500, 502, 503, 504}
    last_error = ""
    result = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            last_error = f"HTTP {error.code}: {detail}"
            if error.code not in retryable:
                break
        except urllib.error.URLError as error:
            last_error = f"network error: {error.reason}"
        else:
            if isinstance(result, dict) and result.get("error"):
                last_error = "api error: " + json.dumps(result["error"], ensure_ascii=False)[:500]
                if not str(result["error"]).strip():
                    break
            else:
                break
        if attempt < 3:
            wait = 3 * (attempt + 1)
            print(f"vision retry {attempt + 1} after {wait}s: {last_error}", file=sys.stderr)
            time.sleep(wait)
            continue
        raise RuntimeError(last_error)
    if result is None:
        raise RuntimeError(last_error or "vision call failed")
    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("vision model returned an unparsable result")
    if isinstance(content, list):
        return "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    return str(content or "")


_CACHE: OrderedDict[str, str] = OrderedDict()
_CACHE_MAX = 256


def _cache_key(data: bytes, prompt: str, model: str) -> str:
    digest = hashlib.sha256(data).hexdigest()
    return f"{digest}|{model}|{prompt}"


def _cache_get(key: str) -> str | None:
    if key not in _CACHE:
        return None
    _CACHE.move_to_end(key)
    return _CACHE[key]


def _cache_set(key: str, value: str) -> None:
    _CACHE[key] = value
    _CACHE.move_to_end(key)
    while len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)


def describe_bytes(
    data: bytes,
    mime: str,
    prompt: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    use_cache: bool = True,
) -> str:
    model = model or cfg("VISION_MODEL", DEFAULT_VISION_MODEL)
    api_key = api_key or cfg("VISION_API_KEY")
    base_url = base_url or cfg("VISION_BASE_URL", DEFAULT_VISION_BASE_URL)
    key = _cache_key(data, prompt, model)
    if use_cache:
        cached = _cache_get(key)
        if cached is not None:
            return cached
    b64 = base64.b64encode(data).decode("ascii")
    description = call_vision_model(
        mime=mime,
        b64=b64,
        prompt=prompt,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
    if use_cache:
        _cache_set(key, description)
    return description


def describe_file(
    path: str,
    prompt: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    use_cache: bool = True,
) -> str:
    mime, b64 = encode_image(path)
    data = base64.b64decode(b64)
    return describe_bytes(
        data,
        mime,
        prompt,
        model=model,
        api_key=api_key,
        base_url=base_url,
        use_cache=use_cache,
    )


DATA_URL_RE = re.compile(r"^data:(image/[A-Za-z0-9.+-]+);base64,(.+)$", re.DOTALL)


def image_url_from_part(part: object) -> str | None:
    if not isinstance(part, dict):
        return None
    ptype = part.get("type")
    url = part.get("image_url") or part.get("url") or ""
    if isinstance(url, dict):
        url = url.get("url") or ""
    if not isinstance(url, str) or not url.startswith("data:image/"):
        return None
    if ptype in ("image_url", "input_image") or isinstance(part.get("image_url"), str):
        return url
    return None


def _focus_text(content: list[object]) -> str:
    parts = []
    for part in content:
        if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
            parts.append(part["text"])
    return " ".join(parts).strip()


class _Rewrite:
    def __init__(
        self,
        max_images: int = MAX_IMAGES_PER_REQUEST,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.replaced = 0
        self.max_images = max_images
        self.model = model
        self.base_url = base_url

    def describe_data_url(self, data_url: str, focus: str) -> str | None:
        match = DATA_URL_RE.match(data_url)
        if not match:
            return None
        mime, b64 = match.group(1), match.group(2)
        try:
            data = base64.b64decode(b64)
        except Exception:
            return None
        if not data or len(data) > MAX_IMAGE_BYTES:
            return None
        prompt = DEFAULT_DESCRIBE_PROMPT
        if focus:
            prompt = (
                f"The user's request is: {focus[:500]}\n\n"
                + DEFAULT_DESCRIBE_PROMPT
            )
        try:
            return describe_bytes(
                data,
                mime,
                prompt,
                model=self.model,
                base_url=self.base_url,
            )
        except Exception as error:
            print(f"vision rewrite failed, passing image through: {error}", file=sys.stderr)
            return None

    def rewrite_content(self, content: object, chat: bool) -> object:
        if not isinstance(content, list):
            return content
        focus = _focus_text(content)
        out: list[object] = []
        for part in content:
            url = image_url_from_part(part)
            if url and self.replaced < self.max_images:
                description = self.describe_data_url(url, focus)
                if description:
                    self.replaced += 1
                    text_type = "text" if chat else "input_text"
                    out.append(
                        {
                            "type": text_type,
                            "text": "[image described by vision model] " + description.strip(),
                        }
                    )
                    continue
            out.append(part)
        return out


def rewrite_body(
    body: bytes,
    max_images: int = MAX_IMAGES_PER_REQUEST,
    model: str | None = None,
    base_url: str | None = None,
) -> tuple[bytes, int]:
    """Replace image content parts with text. Returns (body, replaced_count)."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return body, 0
    if not isinstance(payload, dict):
        return body, 0
    rewrite = _Rewrite(max_images=max_images, model=model, base_url=base_url)
    for item in payload.get("input") or []:
        if isinstance(item, dict) and isinstance(item.get("content"), list):
            item["content"] = rewrite.rewrite_content(item["content"], chat=False)
    for message in payload.get("messages") or []:
        if isinstance(message, dict) and isinstance(message.get("content"), list):
            message["content"] = rewrite.rewrite_content(message["content"], chat=True)
    if rewrite.replaced == 0:
        return body, 0
    return json.dumps(payload, ensure_ascii=False).encode("utf-8"), rewrite.replaced


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _forward(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        new_body, _ = (
            rewrite_body(
                body,
                max_images=self.server.max_images,
                model=getattr(self.server, "model", None),
                base_url=getattr(self.server, "base_url", None),
            )
            if body
            else (body, 0)
        )
        headers: dict[str, str] = {}
        for key, value in self.headers.items():
            lower = key.lower()
            if lower in ("host", "content-length", "connection", "transfer-encoding"):
                continue
            headers[key] = value
        headers["Content-Length"] = str(len(new_body))
        parsed = urlparse(self.server.upstream)
        if parsed.scheme == "https":
            conn: http.client.HTTPConnection = http.client.HTTPSConnection(
                parsed.hostname or "127.0.0.1",
                parsed.port or 443,
                timeout=300,
            )
        else:
            conn = http.client.HTTPConnection(
                parsed.hostname or "127.0.0.1",
                parsed.port or 80,
                timeout=300,
            )
        try:
            conn.request(self.command, self.path, body=new_body, headers=headers)
            response = conn.getresponse()
        except Exception as error:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(str(error))))
            self.end_headers()
            self.wfile.write(str(error).encode("utf-8", errors="replace"))
            return
        self.send_response(response.status)
        for key, value in response.getheaders():
            lower = key.lower()
            if lower in ("content-length", "transfer-encoding", "connection"):
                continue
            self.send_header(key, value)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        try:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
                self.wfile.write(chunk)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            response.close()
            conn.close()

    do_POST = _forward
    do_GET = _forward
    do_PUT = _forward
    do_DELETE = _forward
    do_OPTIONS = _forward

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def run_proxy(listen: str, upstream: str, max_images: int, provider: str | None = None) -> int:
    if not cfg("VISION_API_KEY"):
        print("warning: VISION_API_KEY not configured; images will pass through unchanged", file=sys.stderr)
    try:
        base_url, model = resolve_provider(provider, None, None)
    except ValueError as error:
        raise SystemExit(str(error))
    host, _, port = listen.rpartition(":")
    parsed = urlparse(upstream)
    if parsed.scheme not in ("http", "https"):
        raise SystemExit("--upstream must be http:// or https:// origin, e.g. https://api.deepseek.com")
    server = ThreadingHTTPServer((host or "127.0.0.1", int(port or 19100)), ProxyHandler)
    server.upstream = upstream.rstrip("/")
    server.max_images = max_images
    server.model = model
    server.base_url = base_url
    print(f"vision bridge proxy listening on {listen} -> {upstream}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def cmd_see(args: argparse.Namespace) -> int:
    exit_code = 0
    try:
        base_url, model = resolve_provider(args.provider, args.base_url, args.model)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    for index, image in enumerate(args.images, start=1):
        label = image if len(args.images) == 1 else f"[{index}/{len(args.images)}] {image}"
        try:
            text = describe_file(
                image,
                args.question,
                model=model,
                api_key=args.api_key,
                base_url=base_url,
                use_cache=not args.no_cache,
            )
        except (OSError, ValueError, RuntimeError) as error:
            print(f"failed {label}: {error}", file=sys.stderr)
            exit_code = 1
            continue
        print(f"===== {label} =====")
        print((text or "").strip())
        print()
    return exit_code


def cmd_doctor(_args: argparse.Namespace) -> int:
    print("vision base url:", cfg("VISION_BASE_URL", DEFAULT_VISION_BASE_URL))
    print("vision model:   ", cfg("VISION_MODEL", DEFAULT_VISION_MODEL))
    print("api key set:    ", "yes" if cfg("VISION_API_KEY") else "no")
    return 0 if cfg("VISION_API_KEY") else 1


def cmd_providers(_args: argparse.Namespace) -> int:
    providers = all_providers()
    if not providers:
        print("no providers configured")
        return 0
    width = max(len(pid) for pid in providers)
    for pid in sorted(providers):
        preset = providers[pid]
        cost = preset.get("cost") or "n/a"
        note = preset.get("note") or ""
        print(f"{pid:<{width}}  model={preset.get('model') or '-'}  cost={cost}  {note}".rstrip())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vision_bridge", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    see = sub.add_parser("see", help="describe/analyze local images")
    see.add_argument("images", nargs="+", help="image file paths")
    see.add_argument("-q", "--question", default=DEFAULT_DESCRIBE_PROMPT, help="question for the vision model")
    see.add_argument("--model", default=None)
    see.add_argument("--base-url", default=None)
    see.add_argument("--api-key", default=None)
    see.add_argument("--provider", default=None, help="provider preset id, see `providers`")
    see.add_argument("--no-cache", action="store_true")
    see.set_defaults(handler=cmd_see)

    proxy = sub.add_parser("proxy", help="run the local image-strip proxy")
    proxy.add_argument("--listen", default="127.0.0.1:19100")
    proxy.add_argument("--upstream", required=True, help="origin to forward to, e.g. https://api.deepseek.com")
    proxy.add_argument("--max-images", type=int, default=MAX_IMAGES_PER_REQUEST)
    proxy.add_argument("--provider", default=None, help="provider preset id, see `providers`")
    proxy.set_defaults(handler=run_proxy)

    doctor = sub.add_parser("doctor", help="check vision config")
    doctor.set_defaults(handler=cmd_doctor)

    providers = sub.add_parser("providers", help="list available vision provider presets")
    providers.set_defaults(handler=cmd_providers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "proxy":
        return args.handler(args.listen, args.upstream, args.max_images, args.provider)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
