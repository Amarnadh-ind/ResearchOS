"""
Quota-Aware LLM Client
Async client with model routing, retry logic, and structured output parsing.
All routing is delegated to LLMManager with quota-aware failover.
"""

import json

import httpx
import structlog

from config.models import AgentRole, get_model_config

logger = structlog.get_logger()


class LLMClient:
    """Async LLM client with quota-aware routing via LLMManager."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def complete(
        self,
        role: AgentRole,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """Route completion to LLMManager with quota-aware multi-model failover.
        
        The LLMManager handles:
        - Dynamic model discovery
        - Quota-aware routing with cooldowns
        - Automatic failover on 429/RESOURCE_EXHAUSTED/timeout
        - Mock fallback guarantee (pipeline never stops)
        """
        from services.llm_manager import get_llm_manager
        from services.quota_tracker import get_quota_tracker
        
        mgr = get_llm_manager()
        tracker = get_quota_tracker()
        
        # Load defaults from role configuration if not overridden
        config = get_model_config(role)
        temp = temperature if temperature is not None else config.temperature
        max_tok = max_tokens if max_tokens is not None else config.max_tokens

        # ── Pre-call logging: show routing telemetry ──
        telemetry = tracker.get_telemetry()
        online_count = telemetry["summary"]["online"]
        cooldown_count = telemetry["summary"]["cooldown"]
        
        logger.info(
            "llm_call_start",
            role=role.value,
            models_online=online_count,
            models_cooldown=cooldown_count,
            prompt_len=len(user_prompt),
        )

        # Delegate to LLMManager with quota-aware routing
        return await mgr.generate(
            prompt=user_prompt,
            role=role,
            provider=None,
            system_prompt=system_prompt,
            temperature=temp,
            max_tokens=max_tok,
            json_mode=json_mode,
        )

    async def complete_json(
        self,
        role: AgentRole,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Complete and parse as JSON with robust extraction, repair (max_attempts=1)."""
        raw = await self.complete(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
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
        
        # ── Attempt 1: Extract and parse (max_attempts=1) ──
        try:
            return self._parse_json_response(raw, role)
        except Exception as e:
            raise ValueError(
                f"JSON parsing failed for {role.value} (max_attempts=1). Error: {e}."
            ) from e

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from LLM responses that may include markdown, prose, or code fences.
        
        Handles:
        - ```json ... ``` wrappers
        - ``` ... ``` wrappers
        - Leading/trailing prose text around JSON
        - Multiple JSON blocks (takes the first complete one)
        - Concatenated JSON objects (extracts first complete one)
        - Extra trailing closing delimiters
        """
        import re
        
        text = text.strip()
        
        # 1. Remove markdown code fences
        fence_pattern = re.compile(r'```(?:json)?\s*\n?(.*?)\n?\s*```', re.DOTALL)
        fence_match = fence_pattern.search(text)
        if fence_match:
            text = fence_match.group(1).strip()
        
        # 2. Try to find the first { or [ and extract balanced content from there
        first_brace = text.find('{')
        first_bracket = text.find('[')
        
        if first_brace == -1 and first_bracket == -1:
            return text  # Let json.loads raise the error
        
        start = first_brace if first_bracket == -1 else (
            first_bracket if first_brace == -1 else min(first_brace, first_bracket)
        )
        
        # 3. Use stack-based balancing to find the exact end of FIRST complete JSON
        candidate = text[start:]
        return LLMClient._extract_first_complete_json(candidate)

    @staticmethod
    def _extract_first_complete_json(text: str) -> str:
        """Extract the first complete JSON object/array from potentially concatenated JSON.
        
        Handles cases where LLM returns multiple JSON objects concatenated like:
        {"a":1}{"b":2} or {"a":1} {"b":2}
        """
        if not text:
            return text
            
        text = text.strip()
        if not (text.startswith('{') or text.startswith('[')):
            return text
            
        # Use a stack-based approach to find the first complete JSON structure
        in_string = False
        escaped = False
        stack = []
        
        for i, ch in enumerate(text):
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
            if ch == '{' or ch == '[':
                stack.append(ch)
            elif ch == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
                    if not stack:  # First complete object found
                        return text[:i+1]
            elif ch == ']':
                if stack and stack[-1] == '[':
                    stack.pop()
                    if not stack:  # First complete array found
                        return text[:i+1]
        
        # If we couldn't find a complete structure, return original and let parser handle it
        return text

    @staticmethod
    def _repair_json(text: str) -> str:
        """Attempt to repair common JSON issues from LLM responses.
        
        Fixes:
        - Trailing commas before } or ]
        - Unterminated strings (adds closing quote)
        - Unclosed objects and arrays
        - Single quotes instead of double quotes
        - Control characters in strings
        - Extraneous trailing closing delimiters
        
        Uses a stack-based approach to track all open structures and close them.
        """
        import re
        
        text = text.strip()
        
        # If no JSON structure, return as-is
        if not text.startswith('{') and not text.startswith('['):
            return text
        
        # Remove trailing commas before } or ]
        text = re.sub(r',\s*([}\]])', r'\1', text)
        
        # Replace single-quoted keys/values with double quotes
        if '"' not in text and "'" in text:
            text = text.replace("'", '"')
        
        # Remove control characters except \n, \r, \t
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        
        # ── Stack-based structure tracking with extraneous closer removal ──
        in_string = False
        escaped = False
        stack = []
        result_chars = []
        
        for ch in text:
            if escaped:
                escaped = False
                result_chars.append(ch)
                continue
            if ch == '\\' and in_string:
                escaped = True
                result_chars.append(ch)
                continue
            if ch == '"':
                in_string = not in_string
                result_chars.append(ch)
                continue
            if in_string:
                result_chars.append(ch)
                continue
            if ch == '{':
                stack.append('{')
                result_chars.append(ch)
            elif ch == '[':
                stack.append('[')
                result_chars.append(ch)
            elif ch == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
                    result_chars.append(ch)
                # else: extraneous closer — skip it
            elif ch == ']':
                if stack and stack[-1] == '[':
                    stack.pop()
                    result_chars.append(ch)
                # else: extraneous closer — skip it
            else:
                result_chars.append(ch)
        
        text = ''.join(result_chars).rstrip()
        
        # If everything is balanced, return as-is
        if not in_string and not stack:
            return text
        
        # ── Repair truncated output ──
        if in_string:
            if text.endswith('\\'):
                text = text[:-1]
            text += '"'
        
        text = re.sub(r':\s*$', ': null', text)
        text = re.sub(r',\s*$', '', text)
        
        for delimiter in reversed(stack):
            text = re.sub(r',\s*$', '', text)
            if delimiter == '{':
                text += '}'
            elif delimiter == '[':
                text += ']'
        
        return text

    def _parse_json_response(self, raw: str, role: AgentRole) -> dict:
        """Extract, repair, and parse JSON from an LLM response."""
        def _try_parse(text: str) -> dict | None:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return None
        
        # Step 1: Extract JSON from wrappers
        extracted = self._extract_json(raw)
        parsed = _try_parse(extracted)
        if parsed is not None:
            return parsed
        
        # Step 2: Try with repair
        repaired = self._repair_json(extracted)
        parsed = _try_parse(repaired)
        if parsed is not None:
            return parsed
        
        # Step 3: If extracted text has no JSON delimiters, search raw text
        # for any {…} or […] pattern using regex (catches JSON in markdown)
        import re
        if '{' not in extracted and '[' not in extracted:
            for pattern in [r'(\{.*\})', r'(\[.*\])']:
                match = re.search(pattern, raw, re.DOTALL)
                if match:
                    candidate = match.group(1)
                    parsed = _try_parse(candidate)
                    if parsed is not None:
                        return parsed
                    repaired = self._repair_json(candidate)
                    parsed = _try_parse(repaired)
                    if parsed is not None:
                        return parsed
        
        raise ValueError(
            f"JSON parse error for {role.value}: No valid JSON found. "
            f"Response length: {len(raw)}, "
            f"Extracted length: {len(extracted)}"
        )

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
