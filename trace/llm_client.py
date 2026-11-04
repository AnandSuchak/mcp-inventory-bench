"""
Live LLM Client & Provenance Manager
Project: mcp-inventory-bench
Author: Anand S. Suchak

Dispatches real LLM reasoning requests over official APIs (Google Gemini, OpenAI, Anthropic, Groq).
Captures exact model provenance: provider, model ID, resolved modelVersion, temperature, seed,
system fingerprint, raw response envelope, granular usageMetadata, and separate network vs logical timing.
Enforces strict separation between 'live' empirical traces and 'mock_pilot' harness validation.
"""

import os
import json
import time
import uuid
import hashlib
import datetime
from typing import Dict, Any, Optional, Tuple, List
import subprocess

def get_git_commit_hash() -> str:
    """Retrieve current Git commit hash for provenance."""
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "unknown"

class ToolCallResult(tuple):
    """
    Subclass of tuple for backwards compatibility with 6-tuple unpack:
    (args, raw_resp, latency_ms, resp_id, p_tok, c_tok) = result
    while also exposing structured call_record and complete usage attributes.
    """
    def __new__(cls, args: Dict[str, Any], raw_resp: str, latency_ms: float, resp_id: str, p_tok: int, c_tok: int, call_record: Optional[Dict[str, Any]] = None):
        return super().__new__(cls, (args, raw_resp, latency_ms, resp_id, p_tok, c_tok))

    def __init__(self, args: Dict[str, Any], raw_resp: str, latency_ms: float, resp_id: str, p_tok: int, c_tok: int, call_record: Optional[Dict[str, Any]] = None):
        self.args = args
        self.raw_resp = raw_resp
        self.latency_ms = latency_ms
        self.resp_id = resp_id
        self.p_tok = p_tok
        self.c_tok = c_tok
        self.call_record = call_record or {}
        self.provider_total_tokens = self.call_record.get("usage_metadata", {}).get("provider_total_tokens")
        self.recorded_prompt_candidate_tokens = p_tok + c_tok

class LiveLLMClient:
    """Dispatches tool-calling reasoning requests to live LLMs with complete provenance capture."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        seed: int = 42,
        api_key: Optional[str] = None,
        fail_closed: bool = False
    ):
        self.temperature = temperature
        self.seed = seed
        self.git_commit = get_git_commit_hash()
        self.fail_closed = fail_closed
        self.last_call_record: Optional[Dict[str, Any]] = None

        # Resolve API keys from env or Windows registry if on Windows
        resolved_gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not resolved_gemini_key and os.name == "nt":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as reg_key:
                    resolved_gemini_key, _ = winreg.QueryValueEx(reg_key, "GEMINI_API_KEY")
                    if resolved_gemini_key:
                        os.environ["GEMINI_API_KEY"] = resolved_gemini_key
            except Exception:
                pass

        # Auto-detect provider if not specified
        if provider:
            self.provider = provider.lower()
        elif os.getenv("GEMINI_API_KEY") or resolved_gemini_key:
            self.provider = "gemini"
        elif os.getenv("OPENAI_API_KEY") or api_key:
            self.provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            self.provider = "anthropic"
        elif os.getenv("GROQ_API_KEY"):
            self.provider = "groq"
        else:
            if self.fail_closed:
                raise RuntimeError("FAIL_CLOSED: Live provider requested but no API credentials configured.")
            self.provider = "mock_pilot"

        self.api_key = api_key or os.getenv(f"{self.provider.upper()}_API_KEY", "")
        if self.provider == "gemini" and not self.api_key and resolved_gemini_key:
            self.api_key = resolved_gemini_key

        if self.provider != "mock_pilot" and not self.api_key and self.fail_closed:
            raise RuntimeError(f"FAIL_CLOSED: API key missing for live provider '{self.provider}'.")

        # Default model identifiers
        if model:
            self.model = model
        elif self.provider == "openai":
            self.model = "gpt-4o-mini"
        elif self.provider == "gemini":
            self.model = "gemini-3.5-flash-lite"
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
            "git_commit": self.git_commit,
            "schema_version": "2026-07-28/draft-2020-12",
            "prompt_version": "v1.0-level1-dynamic-repair",
            "timestamp": time.time()
        }

    def generate_tool_arguments(
        self,
        user_intent: str,
        tool_name: str,
        exposed_schema: Dict[str, Any],
        error_context: Optional[str] = None,
        previous_arguments: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        arm_name: Optional[str] = None,
        replicate_id: int = 0,
        attempt_id: int = 1
    ) -> ToolCallResult:
        """
        Prompt the LLM to generate or repair tool arguments.
        Returns ToolCallResult which unpacks as:
        (parsed_arguments, raw_response_text, latency_ms, response_id, prompt_tokens, completion_tokens)
        and provides .call_record with full telemetry.
        """
        t_logical_start = time.perf_counter()
        t_start_epoch = time.time()
        t_start_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        call_id = str(uuid.uuid4())

        system_prompt = (
            f"You are an autonomous enterprise operations AI agent executing tool '{tool_name}'.\n"
            "You MUST output ONLY a valid JSON object containing the exact tool arguments required.\n"
            "Do not include any conversational filler, markdown formatting blocks, or explanations."
        )

        schema_serialized = json.dumps(exposed_schema, indent=2, sort_keys=True)
        schema_sha256 = hashlib.sha256(schema_serialized.encode("utf-8")).hexdigest()
        schema_exposure_tok = max(1, len(schema_serialized) // 4)

        user_content = f"User Intent: {user_intent}\n\nAvailable Tool Schema Specification:\n{schema_serialized}\n"

        if error_context:
            user_content += (
                f"\nYour previous arguments failed validation with this error:\n{error_context}\n"
                f"Previous arguments attempted:\n{json.dumps(previous_arguments or {}, indent=2, sort_keys=True)}\n"
                "Please correct your arguments based strictly on the newly exposed schema constraints above."
            )

        full_prompt_text = f"{system_prompt}\n\n{user_content}"
        prompt_sha256 = hashlib.sha256(full_prompt_text.encode("utf-8")).hexdigest()
        schema_present = schema_serialized in user_content

        # Dispatch based on provider
        if self.api_mode == "live":
            (args, raw_resp, resp_id, p_tok, c_tok, total_tok, usage_meta,
             resolved_model, net_latency_ms, pacing_ms, retries_count, retry_log,
             parse_outcome, parse_error, raw_envelope) = self._call_live_api(
                system_prompt=system_prompt,
                user_content=user_content,
                tool_name=tool_name
            )
        else:
            (args, raw_resp, resp_id, p_tok, c_tok, total_tok, usage_meta,
             resolved_model, net_latency_ms, pacing_ms, retries_count, retry_log,
             parse_outcome, parse_error, raw_envelope) = self._call_mock(
                exposed_schema=exposed_schema,
                previous_arguments=previous_arguments,
                error_context=error_context
            )

        t_logical_end = time.perf_counter()
        t_end_epoch = time.time()
        t_end_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        logical_latency_ms = round((t_logical_end - t_logical_start) * 1000, 3)

        call_record = {
            "call_id": call_id,
            "task_id": task_id or "unknown",
            "arm_name": arm_name or "unknown",
            "replicate_id": replicate_id,
            "attempt_id": attempt_id,
            "provider": self.provider,
            "requested_model": self.model,
            "provider_resolved_model_version": resolved_model or self.model,
            "timestamps": {
                "start_iso": t_start_iso,
                "end_iso": t_end_iso,
                "t_start_epoch": t_start_epoch,
                "t_end_epoch": t_end_epoch
            },
            "timing": {
                "network_latency_ms": net_latency_ms,
                "logical_call_latency_ms": logical_latency_ms,
                "pacing_sleep_ms": pacing_ms
            },
            "parameters": {
                "temperature": self.temperature,
                "response_mime_type": "application/json",
                "seed_requested": self.seed,
                "seed_sent": True if self.provider == "gemini" else False,
                "seed_support_status": "SENT_IN_GENERATION_CONFIG" if self.provider == "gemini" else "NOT_TRANSMITTED"
            },
            "request": {
                "prompt_sha256": prompt_sha256,
                "schema_sha256": schema_sha256,
                "schema_serialized_bytes": len(schema_serialized.encode("utf-8")),
                "schema_present_in_prompt": schema_present
            },
            "usage_metadata": {
                "provider_prompt_tokens": p_tok,
                "provider_candidate_tokens": c_tok,
                "provider_total_tokens": total_tok,
                "recorded_prompt_candidate_tokens": p_tok + c_tok,
                "estimated_schema_exposure_tokens": schema_exposure_tok,
                "raw_usage_metadata": usage_meta
            },
            "response": {
                "response_id": resp_id,
                "raw_response_text": raw_resp,
                "parse_outcome": parse_outcome,
                "parse_error": parse_error,
                "raw_response_envelope": raw_envelope
            },
            "transport": {
                "retries_count": retries_count,
                "status_code": 200 if parse_outcome != "HTTP_ERROR" else 500,
                "retry_log": retry_log
            }
        }

        self.last_call_record = call_record

        return ToolCallResult(
            args=args,
            raw_resp=raw_resp,
            latency_ms=logical_latency_ms,
            resp_id=resp_id,
            p_tok=p_tok,
            c_tok=c_tok,
            call_record=call_record
        )

    def _call_live_api(self, system_prompt: str, user_content: str, tool_name: str) -> Tuple[
        Dict[str, Any], str, str, int, int, Optional[int], Dict[str, Any],
        str, float, float, int, List[Dict[str, Any]], str, Optional[str], Dict[str, Any]
    ]:
        """Dispatch live HTTP request with network timing, retry tracking, and secret-free headers."""
        import urllib.request
        import urllib.error
        import re

        def extract_json(text: str) -> Tuple[Dict[str, Any], str, Optional[str]]:
            text = text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
                text = re.sub(r"\s*```$", "", text)
            try:
                return json.loads(text.strip()), "SUCCESS", None
            except Exception as e:
                return {}, "PARSE_ERROR", str(e)

        retries_count = 0
        retry_log: List[Dict[str, Any]] = []

        if self.provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_content}"}]}
                ],
                "generationConfig": {
                    "temperature": self.temperature,
                    "responseMimeType": "application/json",
                    "seed": self.seed
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )

            max_retries = 15
            last_err = None
            data = None
            net_latency_ms = 0.0

            for attempt_idx in range(max_retries):
                t_net_start = time.perf_counter()
                try:
                    with urllib.request.urlopen(req, timeout=60.0) as resp:
                        resp_bytes = resp.read()
                        net_latency_ms = round((time.perf_counter() - t_net_start) * 1000, 3)
                        data = json.loads(resp_bytes.decode("utf-8"))
                        break
                except urllib.error.HTTPError as e:
                    net_latency_ms = round((time.perf_counter() - t_net_start) * 1000, 3)
                    last_err = e
                    retries_count += 1
                    status_code = e.code
                    sleep_seconds = 2 ** attempt_idx + 2
                    if status_code == 429:
                        body_text = ""
                        try:
                            body_bytes = e.read()
                            body_text = body_bytes.decode("utf-8")
                            err_data = json.loads(body_text)
                            details = err_data.get("details", []) or err_data.get("error", {}).get("details", [])
                            for d in details:
                                if "retryDelay" in d:
                                    delay_str = str(d["retryDelay"]).rstrip("s")
                                    sleep_seconds = max(sleep_seconds, float(delay_str) + 1.0)
                        except Exception:
                            sleep_seconds = max(sleep_seconds, 20.0)

                        # Detect daily quota exhaustion vs transient RPM limit
                        is_daily_quota = any(term in body_text.lower() for term in (
                            "daily", "perday", "queries per day", "resource has been exhausted", "quota exceeded for quota metric 'queries'"
                        )) or sleep_seconds > 180.0

                        if is_daily_quota:
                            raise RuntimeError(f"DAILY_QUOTA_EXHAUSTED: Google Gemini daily request quota reached (retryDelay={sleep_seconds}s). Body: {body_text[:200]}")
                    retry_log.append({
                        "attempt": attempt_idx + 1,
                        "status_code": status_code,
                        "sleep_seconds": sleep_seconds,
                        "timestamp": time.time()
                    })
                    if status_code in (429, 500, 502, 503, 504) and attempt_idx < max_retries - 1:
                        time.sleep(sleep_seconds)
                        continue
                    raise
                except (urllib.error.URLError, TimeoutError, OSError) as e:
                    net_latency_ms = round((time.perf_counter() - t_net_start) * 1000, 3)
                    last_err = e
                    retries_count += 1
                    sleep_seconds = 2 ** attempt_idx + 2
                    retry_log.append({
                        "attempt": attempt_idx + 1,
                        "error": str(e),
                        "sleep_seconds": sleep_seconds,
                        "timestamp": time.time()
                    })
                    if attempt_idx < max_retries - 1:
                        time.sleep(sleep_seconds)
                        continue
                    raise

            if not data and last_err:
                raise last_err

            # Pacing sleep
            t_pace_start = time.perf_counter()
            time.sleep(2.0)
            pacing_ms = round((time.perf_counter() - t_pace_start) * 1000, 3)

            # Extract fields
            candidates = data.get("candidates", [])
            raw_text = ""
            if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
                parts = candidates[0]["content"]["parts"]
                if parts and "text" in parts[0]:
                    raw_text = parts[0]["text"].strip()

            resp_id = data.get("responseId", "")
            resolved_model = data.get("modelVersion", self.model)
            meta = data.get("usageMetadata", {})

            p_tok = meta.get("promptTokenCount", 0)
            c_tok = meta.get("candidatesTokenCount", 0)
            total_tok = meta.get("totalTokenCount")

            parsed, parse_outcome, parse_error = extract_json(raw_text)

            # Sanitize raw envelope (ensure no secrets)
            raw_envelope = copy_sanitize_dict(data)

            return (
                parsed, raw_text, resp_id, p_tok, c_tok, total_tok, meta,
                resolved_model, net_latency_ms, pacing_ms, retries_count, retry_log,
                parse_outcome, parse_error, raw_envelope
            )

        elif self.provider in ("openai", "groq"):
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1" if self.provider == "openai" else "https://api.groq.com/openai/v1").rstrip("/")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            chat_payload = {
                "model": self.model,
                "temperature": self.temperature,
                "seed": self.seed,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
            }

            req = urllib.request.Request(
                f"{base_url}/chat/completions",
                data=json.dumps(chat_payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )

            t_net_start = time.perf_counter()
            with urllib.request.urlopen(req, timeout=60.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            net_latency_ms = round((time.perf_counter() - t_net_start) * 1000, 3)

            raw_text = data["choices"][0]["message"]["content"].strip()
            resp_id = data.get("id", "")
            usage = data.get("usage", {})
            p_tok = usage.get("prompt_tokens", 0)
            c_tok = usage.get("completion_tokens", 0)
            total_tok = usage.get("total_tokens")
            resolved_model = data.get("model", self.model)
            parsed, parse_outcome, parse_error = extract_json(raw_text)
            raw_envelope = copy_sanitize_dict(data)

            return (
                parsed, raw_text, resp_id, p_tok, c_tok, total_tok, usage,
                resolved_model, net_latency_ms, 0.0, 0, [],
                parse_outcome, parse_error, raw_envelope
            )

        else:
            raise NotImplementedError(f"Live provider '{self.provider}' not supported.")

    def _call_mock(
        self,
        exposed_schema: Dict[str, Any],
        previous_arguments: Optional[Dict[str, Any]],
        error_context: Optional[str]
    ) -> Tuple[
        Dict[str, Any], str, str, int, int, Optional[int], Dict[str, Any],
        str, float, float, int, List[Dict[str, Any]], str, Optional[str], Dict[str, Any]
    ]:
        """Mock fallback for harness verification only (labeled mock_pilot)."""
        args = {
            "supplier_id": "SUP-TEXAS-SEMI",
            "warehouse_code": "WH-US-EAST",
            "order_priority": "STANDARD",
            "total_budget_limit": 25000.0,
            "items": [{"sku": "SKU-10001", "quantity": 50, "unit_cost": 45.0}],
            "authorized_by": "agent.ops@enterprise.mock"
        }
        raw_text = json.dumps(args)
        resp_id = f"mock-resp-{uuid.uuid4().hex[:8]}"
        p_tok = 120
        c_tok = 45
        total_tok = 165
        usage = {
            "promptTokenCount": p_tok,
            "candidatesTokenCount": c_tok,
            "totalTokenCount": total_tok,
            "serviceTier": "mock"
        }
        envelope = {
            "responseId": resp_id,
            "modelVersion": "gpt-4o-mini-mock",
            "usageMetadata": usage,
            "mock": True
        }
        return (
            args, raw_text, resp_id, p_tok, c_tok, total_tok, usage,
            "gpt-4o-mini-mock", 1.5, 0.0, 0, [],
            "SUCCESS", None, envelope
        )

def copy_sanitize_dict(d: Any) -> Any:
    """Recursively scrub any keys containing key, secret, token, authorization, or password."""
    if isinstance(d, dict):
        sanitized = {}
        for k, v in d.items():
            k_lower = str(k).lower()
            if any(secret_term in k_lower for secret_term in ("key", "secret", "token", "auth", "pass", "cred")):
                if k in ("promptTokenCount", "candidatesTokenCount", "totalTokenCount", "tokenCount", "promptTokensDetails"):
                    sanitized[k] = copy_sanitize_dict(v)
                else:
                    sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = copy_sanitize_dict(v)
        return sanitized
    elif isinstance(d, list):
        return [copy_sanitize_dict(x) for x in d]
    return d
