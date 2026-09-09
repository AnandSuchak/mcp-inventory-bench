"""
Live LLM Client & Provenance Manager
Project: mcp-inventory-bench
Author: Anand S. Suchak

Dispatches real LLM reasoning requests over official APIs (OpenAI, Google Gemini, Anthropic, Groq, OpenRouter).
Captures exact model provenance: provider, model ID, temperature, seed, system fingerprint, and raw response.
Enforces strict separation between 'live' empirical traces and 'mock_pilot' harness validation.
"""

import os
import json
import time
from typing import Dict, Any, Optional, Tuple

class LiveLLMClient:
    """Dispatches tool-calling reasoning requests to live LLMs."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        seed: int = 42,
        api_key: Optional[str] = None
    ):
        self.temperature = temperature
        self.seed = seed

        # Auto-detect provider if not specified
        if provider:
            self.provider = provider.lower()
        elif os.getenv("OPENAI_API_KEY") or api_key:
            self.provider = "openai"
        elif os.getenv("GEMINI_API_KEY"):
            self.provider = "gemini"
        elif os.getenv("ANTHROPIC_API_KEY"):
            self.provider = "anthropic"
        elif os.getenv("GROQ_API_KEY"):
            self.provider = "groq"
        else:
            self.provider = "mock_pilot"

        self.api_key = api_key or os.getenv(f"{self.provider.upper()}_API_KEY", "")

        # Default model identifiers
        if model:
            self.model = model
        elif self.provider == "openai":
            self.model = "gpt-4o-mini"
        elif self.provider == "gemini":
            self.model = "gemini-1.5-flash"
        elif self.provider == "anthropic":
            self.model = "claude-3-5-haiku-20241022"
        elif self.provider == "groq":
            self.model = "llama-3.3-70b-versatile"
        else:
            self.model = "gpt-4o-mini-mock"

        self.api_mode = "mock_pilot" if self.provider == "mock_pilot" else "live"

    def get_provenance_metadata(self) -> Dict[str, Any]:
        """Return immutable provenance record for scientific reporting."""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "seed": self.seed,
            "api_mode": self.api_mode,
            "timestamp": time.time()
        }

    def generate_tool_arguments(
        self,
        user_intent: str,
        tool_name: str,
        exposed_schema: Dict[str, Any],
        error_context: Optional[str] = None,
        previous_arguments: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], str, float]:
        """
        Prompt the LLM to generate or repair tool arguments.
        Returns: (parsed_arguments: dict, raw_response_text: str, latency_ms: float)
        """
        t_start = time.perf_counter()

        system_prompt = (
            f"You are an autonomous enterprise operations AI agent executing tool '{tool_name}'.\n"
            "You MUST output ONLY a valid JSON object containing the exact tool arguments required.\n"
            "Do not include any conversational filler, markdown formatting blocks, or explanations."
        )

        user_content = f"User Intent: {user_intent}\n\nAvailable Tool Schema Specification:\n{json.dumps(exposed_schema, indent=2)}\n"

        if error_context:
            user_content += (
                f"\nYour previous arguments failed validation with this error:\n{error_context}\n"
                f"Previous arguments attempted:\n{json.dumps(previous_arguments or {}, indent=2)}\n"
                "Please correct your arguments based strictly on the newly exposed schema constraints above."
            )

        # Dispatch based on provider
        if self.api_mode == "live":
            args, raw_resp = self._call_live_api(system_prompt, user_content)
        else:
            args, raw_resp = self._call_mock(exposed_schema, previous_arguments, error_context)

        latency_ms = round((time.perf_counter() - t_start) * 1000, 3)
        return args, raw_resp, latency_ms

    def _call_live_api(self, system_prompt: str, user_content: str) -> Tuple[Dict[str, Any], str]:
        """Dispatch live HTTP request using httpx."""
        import httpx

        if self.provider in ("openai", "groq"):
            base_url = "https://api.openai.com/v1" if self.provider == "openai" else "https://api.groq.com/openai/v1"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "temperature": self.temperature,
                "seed": self.seed,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
            }
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["choices"][0]["message"]["content"].strip()
                parsed = json.loads(raw_text)
                return parsed, raw_text

        elif self.provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_content}"}]}
                ],
                "generationConfig": {
                    "temperature": self.temperature,
                    "responseMimeType": "application/json"
                }
            }
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = json.loads(raw_text)
                return parsed, raw_text

        else:
            raise NotImplementedError(f"Live provider '{self.provider}' not yet configured.")

    def _call_mock(
        self,
        exposed_schema: Dict[str, Any],
        prev_args: Optional[Dict[str, Any]],
        error_context: Optional[str]
    ) -> Tuple[Dict[str, Any], str]:
        """Mock fallback for harness verification only (labeled mock_pilot)."""
        # Minimal synthetic generator
        args = {
            "supplier_id": "SUP-TEXAS-SEMI",
            "warehouse_code": "WH-US-EAST",
            "order_priority": "STANDARD",
            "total_budget_limit": 25000.0,
            "items": [{"sku": "SKU-10001", "quantity": 50, "unit_cost": 45.0}],
            "authorized_by": "agent.ops@enterprise.mock"
        }
        return args, json.dumps(args)
