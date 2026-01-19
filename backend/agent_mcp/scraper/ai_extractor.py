"""LLM-powered extraction helpers."""
from __future__ import annotations

import logging
import os
import json
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class AIExtractor:
    def __init__(self) -> None:
        self.api_base = os.environ.get("LLM_API_BASE")
        self.api_key = os.environ.get("LLM_API_KEY")
        self.model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.timeout = float(os.environ.get("LLM_TIMEOUT", 60))

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        # Ollama (local) does not require auth; avoid sending marker keys.
        api_base = (self.api_base or "").lower()
        is_local_ollama = "localhost:11434" in api_base or "127.0.0.1:11434" in api_base
        if self.api_key and not is_local_ollama and self.api_key != "ollama":
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def _extract_error_message(body: str) -> str:
        if not body:
            return ""
        try:
            payload = json.loads(body)
            if isinstance(payload, dict):
                if isinstance(payload.get("error"), str):
                    return payload["error"]
                if isinstance(payload.get("message"), str):
                    return payload["message"]
        except Exception:
            pass
        return body

    @classmethod
    def _is_ollama_insufficient_memory_error(cls, body: str) -> bool:
        msg = cls._extract_error_message(body).lower()
        return (
            "requires more system memory" in msg
            or "not enough memory" in msg
            or "insufficient memory" in msg
        )

    def _ollama_fallback_models(self) -> list[str]:
        env_value = os.environ.get("OLLAMA_FALLBACK_MODELS", "").strip()
        if env_value:
            return [m.strip() for m in env_value.split(",") if m.strip()]
        return ["llama3.2", "llama3.2:latest", "llama3.2:3b", "llama3.2:1b"]

    def summarize(
        self,
        content: str,
        instructions: Optional[str] = None,
        max_words: int = 200,
    ) -> Dict[str, Any]:
        if not self.api_base:
            snippet = content[: max_words * 5]
            return {
                "success": False,
                "error": "LLM_API_BASE not configured",
                "fallback": snippet,
            }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": instructions
                    or "Summarize the provided webpage content in concise bullet points.",
                },
                {
                    "role": "user",
                    "content": content[: 8000],
                },
            ],
            "max_tokens": max(200, int(max_words * 3)),
            "temperature": 0.2,
        }
        try:
            response = requests.post(
                f"{self.api_base.rstrip('/')}/chat/completions",
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]["content"]
            return {"success": True, "summary": message}
        except requests.HTTPError as exc:
            resp = exc.response
            body = resp.text if resp is not None else ""
            if resp is not None and resp.status_code == 500 and self._is_ollama_insufficient_memory_error(body):
                for fallback_model in self._ollama_fallback_models():
                    if fallback_model == self.model:
                        continue
                    try:
                        retry_payload = dict(payload)
                        retry_payload["model"] = fallback_model
                        retry = requests.post(
                            f"{self.api_base.rstrip('/')}/chat/completions",
                            json=retry_payload,
                            headers=self._build_headers(),
                            timeout=self.timeout,
                        )
                        retry.raise_for_status()
                        data = retry.json()
                        message = data["choices"][0]["message"]["content"]
                        return {"success": True, "summary": message, "model": fallback_model}
                    except Exception:
                        continue
            logger.warning("AI summarization failed: %s", exc)
            return {"success": False, "error": str(exc), "fallback": content[: max_words * 5]}
        except Exception as exc:
            logger.warning("AI summarization failed: %s", exc)
            return {"success": False, "error": str(exc), "fallback": content[: max_words * 5]}

    def extract_structured(
        self,
        content: str,
        schema_description: str,
        max_tokens: int = 600,
    ) -> Dict[str, Any]:
        if not self.api_base:
            return {
                "success": False,
                "error": "LLM_API_BASE not configured",
            }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract the requested data and respond with JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Schema: {schema_description}\n\nContent:\n{content[:8000]}",
                },
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        try:
            response = requests.post(
                f"{self.api_base.rstrip('/')}/chat/completions",
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]["content"].strip()
            return {"success": True, "extracted": message}
        except requests.HTTPError as exc:
            resp = exc.response
            body = resp.text if resp is not None else ""
            if resp is not None and resp.status_code == 500 and self._is_ollama_insufficient_memory_error(body):
                for fallback_model in self._ollama_fallback_models():
                    if fallback_model == self.model:
                        continue
                    try:
                        retry_payload = dict(payload)
                        retry_payload["model"] = fallback_model
                        retry = requests.post(
                            f"{self.api_base.rstrip('/')}/chat/completions",
                            json=retry_payload,
                            headers=self._build_headers(),
                            timeout=self.timeout,
                        )
                        retry.raise_for_status()
                        data = retry.json()
                        message = data["choices"][0]["message"]["content"].strip()
                        return {"success": True, "extracted": message, "model": fallback_model}
                    except Exception:
                        continue
            logger.warning("AI extraction failed: %s", exc)
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.warning("AI extraction failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def ask(
        self,
        question: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.api_base:
            return {
                "success": False,
                "error": "LLM_API_BASE not configured",
            }
        
        messages = [
            {
                "role": "system",
                "content": "You are a helpful AI assistant. Answer the user's question clearly and concisely.",
            }
        ]
        
        if context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            })
        else:
            messages.append({
                "role": "user",
                "content": question
            })

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7,
        }
        try:
            response = requests.post(
                f"{self.api_base.rstrip('/')}/chat/completions",
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]["content"]
            return {"success": True, "answer": message}
        except requests.HTTPError as exc:
            resp = exc.response
            body = resp.text if resp is not None else ""
            if resp is not None and resp.status_code == 500 and self._is_ollama_insufficient_memory_error(body):
                for fallback_model in self._ollama_fallback_models():
                    if fallback_model == self.model:
                        continue
                    try:
                        retry_payload = dict(payload)
                        retry_payload["model"] = fallback_model
                        retry = requests.post(
                            f"{self.api_base.rstrip('/')}/chat/completions",
                            json=retry_payload,
                            headers=self._build_headers(),
                            timeout=self.timeout,
                        )
                        retry.raise_for_status()
                        data = retry.json()
                        message = data["choices"][0]["message"]["content"]
                        return {"success": True, "answer": message, "model": fallback_model}
                    except Exception:
                        continue
            logger.warning("AI ask failed: %s", exc)
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.warning("AI ask failed: %s", exc)
            return {"success": False, "error": str(exc)}


aiextractor = AIExtractor()
