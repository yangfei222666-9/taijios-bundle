"""
LLM 调用适配层。
优先级：Claude API > OpenAI-compat (DeepSeek/Kimi/Qwen/etc) > ollama > mock
开发者零配置也能跑（mock 模式兜底）。

2026-04-19 补丁: 原只支持 Claude + ollama · 朋友填 DEEPSEEK_API_KEY 也走 mock 导致"对话不行".
现加 OpenAI-compat 支持: 检测 DEEPSEEK_API_KEY / OPENAI_API_KEY / KIMI_API_KEY 等 → 对应 base URL.
"""

import json
import os
import logging
import pathlib
from typing import Optional

logger = logging.getLogger("taijios.llm")


# OpenAI-compatible provider 预设 (只要有对应 env key, 自动选)
# 朋友在 setup.py 配 DEEPSEEK_API_KEY + LLM_PROVIDER=deepseek · Soul 也能读到
_OPENAI_COMPAT_PROVIDERS = [
    ("DEEPSEEK_API_KEY",   "https://api.deepseek.com/v1",                               "deepseek-chat"),
    ("KIMI_API_KEY",       "https://api.moonshot.cn/v1",                                "moonshot-v1-32k"),
    ("QWEN_API_KEY",       "https://dashscope.aliyuncs.com/compatible-mode/v1",         "qwen-plus"),
    ("ZHIPU_API_KEY",      "https://open.bigmodel.cn/api/paas/v4",                      "glm-4-plus"),
    ("YI_API_KEY",         "https://api.lingyiwanwu.com/v1",                            "yi-large"),
    ("OPENAI_API_KEY",     None,                                                         "gpt-4o"),  # base 从 OPENAI_API_BASE 或默认
]


def _load_zhuge_env():
    """
    朋友在 setup.py 把 key 写进了 zhuge-skill/.env · Soul 独立 package 默认读不到.
    主动 load 一下, 让 DEEPSEEK_API_KEY 等能被 Soul 检测.
    """
    # 尝试多个候选路径 (bundle 结构: TaijiOS/taijios-soul/src/taijios/llm.py → bundle_root/zhuge-skill/.env)
    here = pathlib.Path(__file__).resolve()
    candidates = [
        here.parent.parent.parent.parent.parent / "zhuge-skill" / ".env",  # bundle
        here.parent.parent.parent.parent / "zhuge-skill" / ".env",
        pathlib.Path.cwd() / "zhuge-skill" / ".env",
        pathlib.Path.cwd() / ".env",
    ]
    for env_f in candidates:
        if env_f.exists():
            try:
                for line in env_f.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip()
                    if k and v and k not in os.environ:
                        os.environ[k] = v
                logger.info(f"LLM: loaded {env_f}")
                return
            except Exception as e:
                logger.warning(f"read .env failed: {e}")


_load_zhuge_env()


class LLMCaller:
    """
    LLM 调用适配器。三级 fallback：Claude → ollama → mock。

    用法:
        llm = LLMCaller()                          # 自动探测
        llm = LLMCaller(api_key="sk-ant-...")       # 强制 Claude
        llm = LLMCaller(ollama_url="http://...")    # 指定 ollama
    """

    def __init__(
        self,
        api_key: str = None,
        ollama_url: str = None,
        model: str = None,
    ):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self._ollama_url = (ollama_url or "http://localhost:11434").rstrip("/")
        self._default_model = model
        self._check_available()

    def _check_available(self):
        self.available = False
        self.backend = "mock"
        self._oa_base = None
        self._oa_key = None
        self._oa_model = None

        # 1 · Claude (optimal)
        if self._api_key:
            self.available = True
            self.backend = "claude"
            logger.info("LLM backend: claude")
            return

        # 2 · OpenAI-compatible (DeepSeek / Kimi / Qwen / OpenAI 等)
        for env_key, default_base, default_model in _OPENAI_COMPAT_PROVIDERS:
            val = os.environ.get(env_key, "").strip()
            if not val:
                continue
            base = default_base or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
            # 允许 OPENAI_API_BASE + OPENAI_MODEL 做本地 Ollama 覆盖
            if env_key == "OPENAI_API_KEY":
                base = os.environ.get("OPENAI_API_BASE", default_base or "https://api.openai.com/v1")
            model = os.environ.get(f"{env_key.split('_')[0]}_MODEL", "").strip() \
                or os.environ.get("OPENAI_MODEL", "").strip() or default_model
            self.available = True
            self.backend = "openai_compat"
            self._oa_base = base
            self._oa_key = val
            self._oa_model = model
            logger.info(f"LLM backend: openai_compat · base={base} · model={model}")
            return

        # 3 · Ollama (local)
        try:
            import urllib.request
            req = urllib.request.Request(f"{self._ollama_url}/api/tags")
            resp = urllib.request.urlopen(req, timeout=2)
            if resp.status == 200:
                self.available = True
                self.backend = "ollama"
                logger.info("LLM backend: ollama")
                return
        except Exception:
            pass

        # 4 · mock (fallback)
        logger.info("LLM backend: mock (no LLM available)")

    def call(
        self,
        system_prompt: str,
        user_message: str,
        model: str = None,
        force_claude: bool = False,
        history: list = None,
        max_tokens: int = 1024,
        image_base64: str = "",
    ) -> str:
        """
        调用 LLM。force_claude=True 强制走 Claude API（重要场景）。
        """
        if force_claude and self._api_key:
            return self._call_claude(system_prompt, user_message, history, max_tokens, image_base64)
        if self.backend == "claude":
            return self._call_claude(system_prompt, user_message, history, max_tokens, image_base64)
        if self.backend == "openai_compat":
            return self._call_openai_compat(system_prompt, user_message, history, max_tokens)
        if self.backend == "ollama":
            if image_base64:
                logger.warning("ollama 不支持图片输入，忽略图片")
            return self._call_ollama(
                system_prompt, user_message,
                model or self._default_model or "qwen2.5:7b",
                history=history,
            )
        return self._mock_response(system_prompt, user_message)

    def _call_openai_compat(self, system: str, user: str, history: list = None,
                            max_tokens: int = 1024) -> str:
        """OpenAI chat/completions 兼容 · DeepSeek/Kimi/Qwen/Yi/Zhipu/OpenAI 都走这里."""
        import urllib.request, urllib.error
        messages = [{"role": "system", "content": system}]
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user})

        payload = {
            "model": self._oa_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        try:
            req = urllib.request.Request(
                f"{self._oa_base}/chat/completions",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self._oa_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:200]
            logger.error(f"openai_compat {e.code}: {body}")
            return self._mock_response(system, user)
        except Exception as e:
            logger.error(f"openai_compat failed: {e}")
            return self._mock_response(system, user)

    def _call_claude(self, system: str, user: str, history: list = None,
                     max_tokens: int = 1024, image_base64: str = "") -> str:
        import httpx
        try:
            messages = []
            if history:
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role in ("user", "assistant") and content:
                        messages.append({"role": role, "content": content})

            if image_base64:
                if image_base64.startswith("/9j/"):
                    media_type = "image/jpeg"
                elif image_base64.startswith("iVBOR"):
                    media_type = "image/png"
                elif image_base64.startswith("R0lGOD"):
                    media_type = "image/gif"
                elif image_base64.startswith("UklGR"):
                    media_type = "image/webp"
                else:
                    media_type = "image/jpeg"
                user_content = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": user or "分析这张图片"},
                ]
                messages.append({"role": "user", "content": user_content})
            else:
                messages.append({"role": "user", "content": user})

            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._default_model or "claude-sonnet-4-20250514",
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": messages,
                },
                timeout=60 if image_base64 else 30,
            )
            data = resp.json()
            if resp.status_code != 200:
                error_msg = data.get("error", {}).get("message", str(data))
                logger.error("Claude API %d: %s", resp.status_code, error_msg)
                return self._call_ollama_fallback(system, user)
            return data["content"][0]["text"]
        except Exception as e:
            logger.error("Claude API call failed: %s", e)
            return self._call_ollama_fallback(system, user)

    def _call_ollama_fallback(self, system: str, user: str) -> str:
        try:
            return self._call_ollama(system, user, self._default_model or "qwen2.5:7b")
        except Exception:
            return self._mock_response(system, user)

    def _call_ollama(self, system: str, user: str, model: str,
                     history: list = None) -> str:
        import urllib.request

        # nudge: 根据 system prompt 模式微调
        if "【主线】危机" in system:
            nudge = "\n（提醒：用户明确说了很崩溃，先一句共情再帮忙解决）"
        elif "生成内容" in system or "取消3句话限制" in system:
            nudge = "\n（提醒：完整输出用户要的内容，不要截断）"
        elif "闲聊" in system or "损友" in system:
            import random as _rnd
            _all_examples = []
            try:
                from taijios.engine.style_library import STYLE_LAYERS
                for layer in STYLE_LAYERS.values():
                    _all_examples.extend(layer.get("examples", []))
            except Exception:
                pass
            if _all_examples:
                sample = _rnd.choice(_all_examples)
                nudge = f"\n（提醒：你是有趣的军师，参考这种风格：「{sample}」emoji放句首或句中，别堆末尾。禁止猜用户心情不好。）"
            else:
                nudge = "\n（提醒：像老友聊天，适当带emoji。禁止猜用户心情不好。）"
        else:
            nudge = "\n（提醒：直接回答问题，语气干练专业。禁止猜测用户心情，禁止说「看来你心情不好」「我理解你的感受」之类的话。）"

        messages = [{"role": "system", "content": system}]
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user + nudge})

        payload = json.dumps({
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": 1024},
        }).encode()
        req = urllib.request.Request(
            f"{self._ollama_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error("Ollama call failed: %s", e)
            return self._mock_response(system, user)

    def _mock_response(self, system: str, user: str) -> str:
        """模拟回复——根据 system prompt 关键词调整风格"""
        if "战友模式" in system or "情绪护盾" in system:
            return f"没事，我们一起看看。关于「{user[:20]}」——先别急，一步步来。"
        if "直率" in system:
            return f"说实话，「{user[:20]}」——这里有问题，但能改。我直接说思路。"
        if "bonded" in system or "老朋友" in system:
            return f"又来了？行吧，「{user[:20]}」——我看看。"
        return f"收到。关于「{user[:20]}」——让我帮你分析一下。"
