"""
OpenRouter LLM Client
Async client with model routing, retry logic, and structured output parsing.
"""

import json
import structlog
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import get_settings
from config.models import AgentRole, get_model_config, FALLBACK_MODELS, ModelConfig

logger = structlog.get_logger()


class LLMClient:
    """Async OpenRouter client with intelligent model routing."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client

    async def complete(
        self,
        role: AgentRole,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """Route completion to LLMManager with multi-provider failover.
        
        Mock mode is DISABLED. All calls go through real providers.
        If all providers fail, the error propagates with full diagnostics.
        """
        from services.llm_manager import get_llm_manager
        
        mgr = get_llm_manager()
        
        # ── Pre-call logging: print active provider and model ──
        candidates = mgr._get_provider_chain(role)
        available = [(p, m) for p, m in candidates if getattr(mgr.settings, f"{p}_api_key", "")]
        primary_prov = available[0][0] if available else "none"
        primary_model = available[0][1] if available else "none"
        
        logger.info(
            "llm_call_start",
            role=role.value,
            primary_provider=primary_prov,
            primary_model=primary_model,
            available_providers=[p for p, _ in available],
            prompt_len=len(user_prompt),
        )

        # Delegate to LLMManager — never fall back to mock
        return await mgr.generate(
            prompt=user_prompt,
            role=role,
            provider=None,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode
        )

    async def _complete_api(
        self,
        role: AgentRole,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """Send a completion request routed through the priority models and fallback chain."""
        import time
        from config.models import ROLE_PRIORITY_MODELS, ModelConfig, get_model_config

        config = get_model_config(role)
        client = await self._get_client()

        # Build list of candidate models in priority order
        candidates = list(ROLE_PRIORITY_MODELS.get(role, []))
        for fm in FALLBACK_MODELS:
            if fm not in candidates:
                candidates.append(fm)
        if config.model_id not in candidates:
            candidates.insert(0, config.model_id)

        last_error = None
        for model_id in candidates:
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature or config.temperature,
                "max_tokens": max_tokens or config.max_tokens,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            logger.info(
                "llm_request_attempt",
                model=model_id,
                role=role.value,
                prompt_len=len(user_prompt),
            )

            start_time = time.monotonic()
            try:
                response = await client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                latency_ms = int((time.monotonic() - start_time) * 1000)

                usage = data.get("usage", {})
                tokens_in = usage.get("prompt_tokens", 0)
                tokens_out = usage.get("completion_tokens", 0)

                logger.info(
                    "llm_response_success",
                    model=model_id,
                    role=role.value,
                    response_len=len(content),
                    tokens=usage,
                    latency_ms=latency_ms,
                )

                # Log to Postgres and emit real-time WebSocket debug event
                await self._log_execution_and_emit_debug(
                    role=role,
                    user_prompt=user_prompt,
                    content=content,
                    model_id=model_id,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=latency_ms,
                )

                return content

            except Exception as e:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                logger.warning(
                    "llm_request_failed_trying_next",
                    model=model_id,
                    error=str(e),
                    latency_ms=latency_ms,
                )
                await self._log_failure(role, user_prompt, model_id, str(e), latency_ms)
                last_error = e
                continue

        # If all candidates failed, raise RuntimeError
        raise RuntimeError(f"All routed and fallback models failed. Last error: {str(last_error)}")

    def _estimate_cost(self, model_id: str, tokens_in: int, tokens_out: int) -> float:
        m = model_id.lower()
        if "gpt-4o-mini" in m:
            return (tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000
        elif "gpt-4o" in m:
            return (tokens_in * 2.50 + tokens_out * 10.00) / 1_000_000
        elif "opus" in m:
            return (tokens_in * 15.00 + tokens_out * 75.00) / 1_000_000
        else:
            return (tokens_in * 0.50 + tokens_out * 1.50) / 1_000_000

    async def _log_execution_and_emit_debug(
        self,
        role: AgentRole,
        user_prompt: str,
        content: str,
        model_id: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
    ):
        from config.settings import active_session_id_var, active_topic_var
        session_id = active_session_id_var.get()
        topic = active_topic_var.get() or "Autonomous Multi-Agent Systems"

        cost = self._estimate_cost(model_id, tokens_in, tokens_out)

        if session_id:
            # 1. Emit real-time debug event to session memory (for WebSocket)
            try:
                from memory.session import get_session_memory
                session_mem = get_session_memory()
                await session_mem.push_event(session_id, {
                    "agent": role.value,
                    "type": "debug",
                    "data": {
                        "topic": topic,
                        "prompt": user_prompt,
                        "response": content,
                        "model": model_id,
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "cost": cost,
                        "latency": latency_ms,
                    }
                })
                # Cache raw output
                await session_mem.set_state(session_id, {
                    "raw_llm_output": content,
                    "writer_prompt": user_prompt if role == AgentRole.WRITER else None
                })
            except Exception as e:
                logger.warning("failed_pushing_debug_event", error=str(e))

            # 2. Log execution details to PostgreSQL
            try:
                from memory.metadata import get_metadata_store
                metadata = get_metadata_store()
                await metadata.log_agent_execution(
                    session_id=session_id,
                    agent_name=role.value,
                    status="success",
                    input_data={"prompt": user_prompt},
                    output_data={"response": content},
                    tokens_used=tokens_in + tokens_out,
                    duration_ms=latency_ms,
                    error=None,
                    model_name=model_id,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost=cost,
                    latency=latency_ms,
                )
            except Exception as e:
                logger.warning("failed_logging_llm_execution", error=str(e))

    async def _log_failure(
        self,
        role: AgentRole,
        user_prompt: str,
        model_id: str,
        error_msg: str,
        latency_ms: int,
    ):
        from config.settings import active_session_id_var
        session_id = active_session_id_var.get()
        if session_id:
            try:
                from memory.metadata import get_metadata_store
                metadata = get_metadata_store()
                await metadata.log_agent_execution(
                    session_id=session_id,
                    agent_name=role.value,
                    status="error",
                    input_data={"prompt": user_prompt},
                    output_data=None,
                    tokens_used=0,
                    duration_ms=latency_ms,
                    error=error_msg,
                    model_name=model_id,
                    tokens_in=0,
                    tokens_out=0,
                    cost=0.0,
                    latency=latency_ms,
                )
            except Exception as e:
                logger.warning("failed_logging_llm_failure", error=str(e))

    async def complete_json(
        self,
        role: AgentRole,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """Complete and parse as JSON with robust extraction, repair, and retry.
        
        Pipeline:
        1. Get raw LLM response
        2. Log diagnostics (length, first/last 500 chars)
        3. Extract JSON from markdown/prose wrappers
        4. Attempt parse with repair logic
        5. On failure: save raw to file, retry once with strict JSON prompt
        """
        raw = await self.complete(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )
        
        # ── Diagnostic logging ──
        logger.info(
            "complete_json_raw_response",
            role=role.value,
            response_length=len(raw),
            first_500=raw[:500],
            last_500=raw[-500:] if len(raw) > 500 else raw,
        )
        
        # ── Attempt 1: Extract and parse ──
        try:
            return self._parse_json_response(raw, role)
        except Exception as first_error:
            logger.warning(
                "json_parse_failed_attempt_1",
                role=role.value,
                error=str(first_error),
                response_length=len(raw),
            )
            
            # Save the failed response for debugging
            self._save_failed_response(raw, role, first_error)
            
            # ── Attempt 2: Retry with strict JSON-only prompt ──
            logger.info("json_retry_with_strict_prompt", role=role.value)
            try:
                retry_prompt = (
                    f"{user_prompt}\n\n"
                    "CRITICAL: Return ONLY valid JSON. No markdown. No explanations. "
                    "No code fences. No text before or after the JSON. "
                    "Ensure all strings are properly terminated and escaped."
                )
                raw_retry = await self.complete(
                    role=role,
                    system_prompt=system_prompt + "\n\nYou MUST return ONLY valid, parseable JSON. No markdown, no explanations.",
                    user_prompt=retry_prompt,
                    json_mode=True,
                )
                
                logger.info(
                    "complete_json_retry_response",
                    role=role.value,
                    response_length=len(raw_retry),
                    first_500=raw_retry[:500],
                )
                
                return self._parse_json_response(raw_retry, role)
            except Exception as retry_error:
                logger.error(
                    "json_parse_failed_all_attempts",
                    role=role.value,
                    first_error=str(first_error),
                    retry_error=str(retry_error),
                )
                self._save_failed_response(raw_retry if 'raw_retry' in dir() else raw, role, retry_error, suffix="_retry")
                raise ValueError(
                    f"JSON parsing failed for {role.value} after retry. "
                    f"First error: {first_error}. Retry error: {retry_error}. "
                    f"Response saved to {role.value}_failed.json"
                ) from retry_error

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from LLM responses that may include markdown, prose, or code fences.
        
        Handles:
        - ```json ... ``` wrappers
        - ``` ... ``` wrappers
        - Leading/trailing prose text around JSON
        - Multiple JSON blocks (takes the first complete one)
        """
        import re
        
        text = text.strip()
        
        # 1. Remove markdown code fences
        # Match ```json\n...\n``` or ```\n...\n```
        fence_pattern = re.compile(r'```(?:json)?\s*\n?(.*?)\n?\s*```', re.DOTALL)
        fence_match = fence_pattern.search(text)
        if fence_match:
            text = fence_match.group(1).strip()
        
        # 2. If it already starts with { or [, use as-is
        if text.startswith('{') or text.startswith('['):
            return text
        
        # 3. Try to find the first { or [ and extract from there
        first_brace = text.find('{')
        first_bracket = text.find('[')
        
        if first_brace == -1 and first_bracket == -1:
            return text  # Let json.loads raise the error
        
        # Pick the earlier of { or [
        start = first_brace if first_bracket == -1 else (
            first_bracket if first_brace == -1 else min(first_brace, first_bracket)
        )
        
        # Find the matching closing brace/bracket from the end
        if text[start] == '{':
            end = text.rfind('}')
        else:
            end = text.rfind(']')
        
        if end > start:
            return text[start:end + 1]
        
        return text[start:]

    @staticmethod
    def _repair_json(text: str) -> str:
        """Attempt to repair common JSON issues from LLM responses.
        
        Fixes:
        - Trailing commas before } or ]
        - Unterminated strings (adds closing quote)
        - Unclosed objects and arrays
        - Single quotes instead of double quotes
        - Control characters in strings
        
        Uses a stack-based approach to track all open structures and close them.
        """
        import re
        
        # Remove trailing commas before } or ]
        text = re.sub(r',\s*([}\]])', r'\1', text)
        
        # Replace single-quoted keys/values with double quotes
        if '"' not in text and "'" in text:
            text = text.replace("'", '"')
        
        # Remove control characters except \n, \r, \t
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        
        # ── Stack-based structure tracking ──
        # Walk the text and track: are we in a string? what structures are open?
        in_string = False
        escaped = False
        stack = []  # Stack of open delimiters: '{', '['
        
        for ch in text:
            if escaped:
                escaped = False
                continue
            if ch == '\\' and in_string:
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            # Outside strings: track structure
            if ch == '{':
                stack.append('{')
            elif ch == '[':
                stack.append('[')
            elif ch == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
            elif ch == ']':
                if stack and stack[-1] == '[':
                    stack.pop()
        
        # If everything is balanced, return as-is
        if not in_string and not stack:
            return text
        
        # ── Repair truncated output ──
        text = text.rstrip()
        
        if in_string:
            # Close the unterminated string
            # Strip any trailing partial escape sequence
            if text.endswith('\\'):
                text = text[:-1]
            text += '"'
        
        # Remove dangling colon (partial key-value pair like  "key":  )
        text = re.sub(r':\s*$', ': null', text)
        
        # Remove trailing comma
        text = re.sub(r',\s*$', '', text)
        
        # Close all open structures in reverse order
        for delimiter in reversed(stack):
            # Before closing, remove any trailing comma
            text = re.sub(r',\s*$', '', text)
            if delimiter == '{':
                text += '}'
            elif delimiter == '[':
                text += ']'
        
        return text

    def _parse_json_response(self, raw: str, role: AgentRole) -> dict:
        """Extract, repair, and parse JSON from an LLM response."""
        # Step 1: Extract JSON from wrappers
        extracted = self._extract_json(raw)
        
        # Step 2: Try parsing directly
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass
        
        # Step 3: Try with repair
        repaired = self._repair_json(extracted)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"JSON parse error for {role.value}: {e}. "
                f"Response length: {len(raw)}, "
                f"Extracted length: {len(extracted)}"
            ) from e

    @staticmethod
    def _save_failed_response(raw: str, role: AgentRole, error: Exception, suffix: str = ""):
        """Save a failed LLM response to disk for debugging."""
        import os
        import traceback
        
        filename = f"{role.value}_failed{suffix}.json"
        filepath = os.path.join(os.path.dirname(__file__), "..", filename)
        
        try:
            debug_data = {
                "role": role.value,
                "error": str(error),
                "error_type": type(error).__name__,
                "traceback": traceback.format_exc(),
                "response_length": len(raw),
                "raw_response": raw,
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            logger.info("saved_failed_response", path=filepath, role=role.value)
        except Exception as save_err:
            logger.warning("failed_saving_response", error=str(save_err))

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
