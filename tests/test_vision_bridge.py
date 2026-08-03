import base64
import io
import json
import unittest
from unittest import mock

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vision_bridge as vb


def png_bytes() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


def data_url() -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes()).decode("ascii")


class RewriteTests(unittest.TestCase):
    def test_chat_completions_image_replaced(self):
        body = json.dumps(
            {
                "model": "deepseek-v4-flash",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "看这张报错图"},
                            {"type": "image_url", "image_url": {"url": data_url()}},
                        ],
                    }
                ],
            }
        ).encode("utf-8")
        with mock.patch.object(vb, "describe_bytes", return_value="错误：TypeError at line 42"):
            new_body, replaced = vb.rewrite_body(body)
        self.assertEqual(replaced, 1)
        payload = json.loads(new_body.decode("utf-8"))
        parts = payload["messages"][0]["content"]
        self.assertEqual(parts[1]["type"], "text")
        self.assertIn("TypeError", parts[1]["text"])

    def test_responses_api_image_replaced(self):
        body = json.dumps(
            {
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_image", "image_url": data_url()},
                        ],
                    }
                ]
            }
        ).encode("utf-8")
        with mock.patch.object(vb, "describe_bytes", return_value="一张示意图"):
            new_body, replaced = vb.rewrite_body(body)
        self.assertEqual(replaced, 1)
        payload = json.loads(new_body.decode("utf-8"))
        part = payload["input"][0]["content"][0]
        self.assertEqual(part["type"], "input_text")
        self.assertIn("一张示意图", part["text"])

    def test_fail_open_when_vision_fails(self):
        body = json.dumps(
            {
                "messages": [
                    {"role": "user", "content": [{"type": "image_url", "image_url": {"url": data_url()}}]}
                ]
            }
        ).encode("utf-8")
        with mock.patch.object(vb, "describe_bytes", side_effect=RuntimeError("boom")):
            new_body, replaced = vb.rewrite_body(body)
        self.assertEqual(replaced, 0)
        self.assertEqual(new_body, body)

    def test_invalid_body_passes_through(self):
        body = b"not json"
        new_body, replaced = vb.rewrite_body(body)
        self.assertEqual(replaced, 0)
        self.assertEqual(new_body, body)


class CacheTests(unittest.TestCase):
    def test_same_image_and_prompt_cached(self):
        vb._CACHE.clear()
        data = png_bytes()
        calls = {"n": 0}

        def fake_call(**kwargs):
            calls["n"] += 1
            return "cached description"

        with mock.patch.object(vb, "call_vision_model", side_effect=fake_call):
            first = vb.describe_bytes(data, "image/png", "是什么？")
            second = vb.describe_bytes(data, "image/png", "是什么？")
        self.assertEqual(first, "cached description")
        self.assertEqual(second, "cached description")
        self.assertEqual(calls["n"], 1)
        vb._CACHE.clear()

    def test_different_prompt_not_cached(self):
        vb._CACHE.clear()
        data = png_bytes()
        calls = {"n": 0}

        def fake_call(**kwargs):
            calls["n"] += 1
            return "ok"

        with mock.patch.object(vb, "call_vision_model", side_effect=fake_call):
            vb.describe_bytes(data, "image/png", "问题一")
            vb.describe_bytes(data, "image/png", "问题二")
        self.assertEqual(calls["n"], 2)
        vb._CACHE.clear()


class CallVisionTests(unittest.TestCase):
    def test_builds_payload_and_parses_text(self):
        captured = {}

        class FakeResponse:
            def read(self):
                return json.dumps(
                    {"choices": [{"message": {"content": "画面里有文字"}}]}
                ).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout=180):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text = vb.call_vision_model(
                mime="image/png",
                b64="x",
                prompt="描述",
                base_url="https://example.com/v1",
                api_key="sk-test",
                model="glm-4v-flash",
            )
        self.assertEqual(text, "画面里有文字")
        self.assertTrue(captured["url"].endswith("/chat/completions"))
        self.assertEqual(captured["headers"]["Authorization"], "Bearer sk-test")
        self.assertEqual(captured["body"]["model"], "glm-4v-flash")


class CliTests(unittest.TestCase):
    def test_see_prints_description(self):
        path = str(Path(__file__).resolve().parent / "sample.png")
        Path(path).write_bytes(png_bytes())
        with mock.patch.object(vb, "describe_file", return_value="描述结果"):
            with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
                code = vb.main(["see", path, "-q", "什么"])
        self.assertEqual(code, 0)
        self.assertIn("描述结果", out.getvalue())

    def test_doctor_checks_key(self):
        with mock.patch.dict(vb._ENV, {"VISION_API_KEY": "sk-test"}, clear=False):
            self.assertEqual(vb.cmd_doctor(mock.Mock()), 0)
        with mock.patch.dict(vb._ENV, {"VISION_API_KEY": ""}, clear=False):
            self.assertEqual(vb.cmd_doctor(mock.Mock()), 1)


if __name__ == "__main__":
    unittest.main()
