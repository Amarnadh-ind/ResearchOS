"""
Multi-Provider LLM Manager — Quota-Aware Auto Routing
Handles dynamic model discovery, quota-aware failover, cooldown management,
and intelligent routing with guaranteed output via mock fallback.
"""

import time

import httpx
import structlog

from config.models import (
    EXCLUDED_MODEL_PATTERNS,
    AgentRole,
    compute_model_priority,
    get_role_strategy,
)
from config.settings import get_settings
from services.quota_tracker import get_quota_tracker

logger = structlog.get_logger()

# Cost per 1M tokens: (input, output) in USD
COST_METRICS = {
    "gemma-4-31b": (0.10, 0.40),
    "gemma-4-26b": (0.075, 0.30),
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-2.5-flash-lite": (0.0375, 0.15),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-3": (0.10, 0.40),
    "nemotron-3-ultra": (0.00, 0.00),  # Free tier via NVIDIA API
    "default": (0.10, 0.40),
}


class LLMManager:
    """Manages quota-aware multi-model LLM routing with automatic failover."""

    # ── Discovered model pools (class-level, populated once at startup) ──
    _discovered_gemma_models: list[str] = []
    _discovered_gemini_models: list[str] = []
    _discovered_other_models: list[str] = []  # Any other generateContent models
    _routing_pool: list[str] = []  # Ordered by priority
    _discovery_completed: bool = False
    _discovered_status: dict[str, str] = {}
    _model_diagnostics: dict[str, dict] = {}

    _default_gemma_models: list[str] = ["gemma-4-31b-it", "gemma-4-26b-a4b-it"]
    _default_gemini_models: list[str] = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

    @classmethod
    async def discover_google_models(cls):
        """Discovers Google (Gemini and Gemma) models dynamically via ListModels API."""
        settings = get_settings()
        key = settings.gemini_api_key or settings.gemma_api_key
        if not key:
            logger.info("skip_google_discovery_no_key")
            cls._discovery_completed = True
            cls._build_routing_pool()
            return

        cls._discovered_gemma_models = []
        cls._discovered_gemini_models = []
        cls._discovered_other_models = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                resp = await client.get(url)

                if resp.status_code == 200:
                    data = resp.json()
                    models_list = data.get("models", [])

                    model_names = [m.get("name") for m in models_list]
                    logger.info("google_discovered_models", count=len(model_names), models=model_names)
                    print(f"google_discovered_models={model_names}", flush=True)

                    for m in models_list:
                        name = m.get("name", "")
                        methods = m.get("supportedGenerationMethods", [])
                        if "generateContent" not in methods:
                            continue

                        # Strip models/ prefix
                        model_id = name.split("/")[-1] if "/" in name else name

                        if "gemma" in model_id.lower():
                            cls._discovered_gemma_models.append(model_id)
                        elif "gemini" in model_id.lower():
                            cls._discovered_gemini_models.append(model_id)
                        else:
                            cls._discovered_other_models.append(model_id)

                elif resp.status_code == 429:
                    logger.error("google_discovery_quota_exceeded")
                elif resp.status_code in (400, 403):
                    logger.error("google_discovery_failed_key", status=resp.status_code, error=resp.text)
                else:
                    logger.error("google_discovery_failed_status", status=resp.status_code, error=resp.text)

        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            logger.error("google_discovery_connection_error", error=str(e))
        except Exception as e:
            logger.error("google_discovery_unexpected_error", error=str(e))

        cls._discovery_completed = True
        cls._build_routing_pool()

    @classmethod
    def _build_routing_pool(cls):
        """
        Build the ordered routing pool from discovered models.
        Priority is computed via pattern matching — no hardcoded names.
        Excludes models incompatible with system instructions / JSON mode.
        """
        tracker = get_quota_tracker()

        # Collect all discovered models
        all_models = []
        for model_id in cls._discovered_gemini_models:
            all_models.append(("gemini", model_id))
        for model_id in cls._discovered_gemma_models:
            all_models.append(("gemma", model_id))
        for model_id in cls._discovered_other_models:
            all_models.append(("gemini", model_id))  # Use gemini API for other Google models

        # If discovery found nothing, use defaults
        if not all_models:
            logger.info("routing_pool_using_defaults")
            for model_id in cls._default_gemini_models:
                all_models.append(("gemini", model_id))
            for model_id in cls._default_gemma_models:
                all_models.append(("gemma", model_id))

        # Filter out excluded models (TTS, image-only, etc.)
        filtered_models = []
        for provider, model_id in all_models:
            model_lower = model_id.lower()
            excluded = any(pattern in model_lower for pattern in EXCLUDED_MODEL_PATTERNS)
            if excluded:
                logger.info("model_excluded_from_routing", model=model_id, reason="incompatible_capabilities")
                continue
            filtered_models.append((provider, model_id))

        all_models = filtered_models

        # Collect static configured models for other providers if keys are present
        settings = get_settings()
        if settings.manus_api_key:
            all_models.append(("manus", "manus"))
        if settings.grok_api_key:
            all_models.append(("grok", "grok-4.3"))
            all_models.append(("grok", "grok-latest"))
        if settings.openai_api_key:
            all_models.append(("openai", "gpt-4o-mini"))
            all_models.append(("openai", "gpt-4o"))
        if settings.openrouter_api_key:
            all_models.append(("openrouter", "openai/gpt-4o-mini"))
            all_models.append(("openrouter", "openai/gpt-4o"))
            all_models.append(("openrouter", "meta-llama/llama-3.1-8b-instruct"))
        if settings.nemotron_api_key:
            all_models.append(("nemotron", "nemotron-3-ultra"))

        # Compute priority for each model and register in tracker
        prioritized = []
        for provider, model_id in all_models:
            priority = compute_model_priority(model_id)
            tracker.register_model(model_id, provider, priority)
            prioritized.append((priority, model_id))

        # Sort by priority (lower = better)
        prioritized.sort(key=lambda x: (x[0], x[1]))
        cls._routing_pool = [model_id for _, model_id in prioritized]

        # Print routing pool
        pool_display = []
        for priority, model_id in prioritized:
            pool_display.append(f"  P{priority}: {model_id}")

        print("\n" + "=" * 70)
        print("         ResearchOS Model Routing Pool (Priority Order)")
        print("=" * 70)
        for line in pool_display:
            print(line)
        print(f"\n  Total models: {len(cls._routing_pool)}")
        print("  Mock fallback: always available")
        print("=" * 70 + "\n", flush=True)

        logger.info(
            "routing_pool_built",
            pool=cls._routing_pool,
            total=len(cls._routing_pool),
        )

    @classmethod
    def get_provider_diagnostics(cls) -> dict:
        """Return per-model diagnostics from the quota tracker."""
        tracker = get_quota_tracker()
        return tracker.get_telemetry()

    @classmethod
    async def verify_startup_health(cls):
        """Run startup diagnostics: discover models, build pool, test health."""
        import os
        settings = get_settings()

        # ── Startup Diagnostics Banner ──
        print("\n" + "=" * 70)
        print("         ResearchOS LLM Provider Startup Diagnostics")
        print("=" * 70)
        print("Verifying Environment Variables:")
        for var in ["GEMINI_API_KEY", "GEMMA_API_KEY", "NEMOTRON_API_KEY"]:
            val = os.getenv(var, "")
            present = "true" if val else "false"
            masked = val[:12] + "..." if val else ""
            print(f"  - {var}: present={present} {f'({masked})' if val else ''}")

        # Discover models dynamically
        await cls.discover_google_models()

        print("\nDiscovered Models:")
        print(f"  - Gemini: {cls._discovered_gemini_models}")
        print(f"  - Gemma:  {cls._discovered_gemma_models}")
        if settings.nemotron_api_key:
            print("  - Nemotron: nemotron-3-ultra")
        print("=" * 70 + "\n", flush=True)

        logger.info("llm_manager_startup_verification")

        # Test health of top models in the routing pool
        key = settings.gemini_api_key or settings.gemma_api_key
        if key:
            for model_id in cls._routing_pool[:4]:  # Test top 4 only
                tracker = get_quota_tracker()
                record = tracker.get_model_record(model_id)
                provider = record.provider if record else "gemini"
                await cls.test_model_health(provider, model_id)
        else:
            logger.info("startup_health_skip", reason="No API key")

    @classmethod
    async def test_model_health(cls, provider: str, model: str) -> bool:
        """Run a health check for a specific model."""
        settings = get_settings()
        
        # Get appropriate key
        if provider == "gemini":
            key = settings.gemini_api_key
        elif provider == "gemma":
            key = settings.gemma_api_key
        else:
            key = getattr(settings, f"{provider}_api_key", "")
            
        if not key:
            tracker = get_quota_tracker()
            tracker.mark_failure(model, "invalid API key", 403)
            cls._model_diagnostics[model] = {
                "connected": False,
                "last_status": 403,
                "latency": 0,
                "last_error": "invalid API key",
                "provider": provider,
            }
            return False

        start_time = time.monotonic()
        connected = False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                if provider in ("gemini", "gemma"):
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                    resp = await client.post(
                        url,
                        json={
                            "contents": [{"parts": [{"text": "ping"}]}],
                            "generationConfig": {"maxOutputTokens": 5}
                        }
                    )
                else:
                    headers = {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    }
                    if provider == "openai":
                        url = "https://api.openai.com/v1/chat/completions"
                    elif provider == "openrouter":
                        url = f"{settings.openrouter_base_url}/chat/completions"
                    elif provider == "grok":
                        url = "https://api.x.ai/v1/chat/completions"
                    elif provider == "manus":
                        url = f"{settings.manus_base_url.rstrip('/')}/chat/completions"
                    elif provider == "nemotron":
                        url = f"{settings.nemotron_base_url.rstrip('/')}/chat/completions"
                    else:
                        raise ValueError(f"Unknown provider: {provider}")

                    resp = await client.post(
                        url,
                        headers=headers,
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 5,
                        }
                    )
                
                latency_ms = int((time.monotonic() - start_time) * 1000)

                if resp.status_code == 200:
                    connected = True
                    tracker = get_quota_tracker()
                    tracker.mark_success(model, latency_ms)
                    cls._model_diagnostics[model] = {
                        "connected": True,
                        "last_status": 200,
                        "latency": latency_ms,
                        "last_error": "",
                        "provider": provider,
                    }
                else:
                    tracker = get_quota_tracker()
                    tracker.mark_failure(model, resp.text[:300], resp.status_code)
                    cls._model_diagnostics[model] = {
                        "connected": False,
                        "last_status": resp.status_code,
                        "latency": latency_ms,
                        "last_error": resp.text[:300],
                        "provider": provider,
                    }

        except Exception as e:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            tracker = get_quota_tracker()
            tracker.mark_failure(model, f"{type(e).__name__}: {str(e)}", 0)
            cls._model_diagnostics[model] = {
                "connected": False,
                "last_status": 0,
                "latency": latency_ms,
                "last_error": f"{type(e).__name__}: {str(e)}",
                "provider": provider,
            }

        return connected

    @classmethod
    async def test_provider_health(cls, provider: str) -> bool:
        """Test health for the first model of a given provider type."""
        if provider == "gemini":
            m = cls._discovered_gemini_models[0] if cls._discovered_gemini_models else "gemini-2.5-flash"
            return await cls.test_model_health("gemini", m)
        elif provider == "gemma":
            m = cls._discovered_gemma_models[0] if cls._discovered_gemma_models else "gemma-4-31b-it"
            return await cls.test_model_health("gemma", m)
        elif provider == "nemotron":
            return await cls.test_model_health("nemotron", "nemotron-3-ultra")
        return False

    def __init__(self):
        self.settings = get_settings()

    def _get_quota_aware_chain(self, role: AgentRole, preferred_provider: str | None = None) -> list[tuple[str, str]]:
        """
        Returns ordered list of (provider, model) to try, filtered by quota
        availability and ordered by the role's strategy.

        Always appends mock-fallback at end for output guarantee.
        """
        settings = get_settings()
        prov = (preferred_provider or settings.llm_provider or "auto").lower()

        # If mock is forced, skip everything
        if prov == "mock":
            return [("mock", "mock-fallback")]

        strategy = get_role_strategy(role)
        tracker = get_quota_tracker()

        # Get all candidate model IDs from routing pool
        if not self._routing_pool:
            self._build_routing_pool()
        all_candidates = list(self._routing_pool)

        # Apply provider filter if specific provider requested
        if prov not in ("auto", "mock"):
            filtered = []
            for model_id in all_candidates:
                record = tracker.get_model_record(model_id)
                if record and record.provider == prov:
                    filtered.append(model_id)
            all_candidates = filtered

        # Get ordered candidates based on strategy and availability
        ordered = tracker.get_ordered_candidates(strategy, all_candidates)

        # Build (provider, model) tuples
        candidates = []
        for model_id in ordered:
            record = tracker.get_model_record(model_id)
            if record:
                candidates.append((record.provider, model_id))

        # Limit fallback chain to prevent cascading failures (max 5 real models + mock)
        max_real_models = 5
        if len(candidates) > max_real_models:
            candidates = candidates[:max_real_models]

        # Always append mock fallback
        candidates.append(("mock", "mock-fallback"))

        return candidates

    # Keep backward compatibility
    def _get_provider_chain(self, role: AgentRole, preferred_provider: str | None = None) -> list[tuple[str, str]]:
        """Backward-compatible wrapper around _get_quota_aware_chain."""
        return self._get_quota_aware_chain(role, preferred_provider)

    async def generate(
        self,
        prompt: str,
        role: AgentRole,
        provider: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False
    ) -> str:
        """Single-attempt LLM call — no provider failover (optimized for speed)."""
        candidates = self._get_quota_aware_chain(role, provider)
        tracker = get_quota_tracker()

        # Try first available real provider (at most 1 attempt), then fallback to mock
        for idx, (prov, model) in enumerate(candidates):
            print(f"provider_attempt={model}", flush=True)

            # Handle mock fallback immediately
            if prov == "mock":
                from config.settings import active_topic_var
                from services.mock_llm import generate_mock_completion
                topic = active_topic_var.get() or prompt
                content = generate_mock_completion(role, system_prompt or "", prompt, topic)
                latency_ms = 10
                cost = 0.0
                tokens_in = len(prompt.split()) * 4 // 3
                tokens_out = len(content.split()) * 4 // 3
                print("provider_success=true", flush=True)
                await self._log_execution_and_emit_debug(
                    role=role, prompt=prompt, content=content,
                    provider="mock", model="mock-fallback",
                    tokens_in=tokens_in, tokens_out=tokens_out,
                    cost=cost, latency_ms=latency_ms,
                )
                return content

            # Skip cooldown models
            if not tracker.is_available(model):
                continue

            # Single attempt on first available provider
            key = getattr(self.settings, f"{prov}_api_key", "") or self.settings.gemini_api_key or self.settings.gemma_api_key
            start_time = time.monotonic()

            try:
                content, tokens_in, tokens_out, status = await self._call_provider_api(
                    provider=prov, model=model, key=key,
                    prompt=prompt, system_prompt=system_prompt,
                    temperature=temperature, max_tokens=max_tokens,
                    json_mode=json_mode,
                )
                if json_mode:
                    from services.llm import get_llm_client
                    get_llm_client()._parse_json_response(content, role)

                latency_ms = int((time.monotonic() - start_time) * 1000)
                tracker.mark_success(model, latency_ms)
                LLMManager._model_diagnostics[model] = {
                    "connected": True,
                    "last_status": status,
                    "latency": latency_ms,
                    "last_error": "",
                    "provider": prov,
                }
                print("provider_success=true", flush=True)
                return content

            except Exception as e:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                status_code = 500
                if hasattr(e, 'response') and e.response is not None:
                    status_code = getattr(e.response, 'status_code', 500)
                elif isinstance(e, httpx.HTTPStatusError):
                    status_code = e.response.status_code
                tracker.mark_failure(model, str(e), status_code)
                LLMManager._model_diagnostics[model] = {
                    "connected": False,
                    "last_status": status_code,
                    "latency": latency_ms,
                    "last_error": str(e),
                    "provider": prov,
                }
                print(f"provider_failed={status_code}", flush=True)
                
                # Log fallback
                next_idx = idx + 1
                if next_idx < len(candidates):
                    _, next_model = candidates[next_idx]
                    print(f"fallback_to={next_model}", flush=True)
                else:
                    print("fallback_to=none", flush=True)
                # Fall through to next candidate (mock or next provider)

        # Final fallback: mock is always available
        from config.settings import active_topic_var
        from services.mock_llm import generate_mock_completion
        topic = active_topic_var.get() or prompt
        content = generate_mock_completion(role, system_prompt or "", prompt, topic)
        print("provider_success=true", flush=True)
        return content

    async def _call_provider_api(
        self,
        provider: str,
        model: str,
        key: str,
        prompt: str,
        system_prompt: str | None,
        temperature: float | None,
        max_tokens: int | None,
        json_mode: bool,
    ) -> tuple[str, int, int, int]:
        """Performs raw network requests to LLM provider APIs."""
        from config.settings import get_settings
        _settings = get_settings()
        _provider_timeout = _settings.fast_mode_provider_timeout if _settings.fast_mode else 20.0
        async with httpx.AsyncClient(timeout=_provider_timeout) as client:
            temp = temperature if temperature is not None else 0.2
            max_tok = max_tokens if max_tokens is not None else 2000

            if provider in ("gemini", "gemma"):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temp,
                        "maxOutputTokens": max_tok,
                    },
                }
                if system_prompt:
                    payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
                if json_mode:
                    payload["generationConfig"]["responseMimeType"] = "application/json"

                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    raise httpx.HTTPStatusError(
                        f"{provider.upper()} API error {resp.status_code}: {resp.text[:300]}",
                        request=resp.request,
                        response=resp,
                    )
                data = resp.json()

                # Parse Gemini/Gemma response
                content = data["candidates"][0]["content"]["parts"][0]["text"]

                usage = data.get("usageMetadata", {})
                tokens_in = usage.get("promptTokenCount", len(prompt.split()) * 4 // 3)
                tokens_out = usage.get("candidatesTokenCount", len(content.split()) * 4 // 3)

                return content, tokens_in, tokens_out, resp.status_code

            elif provider in ("openai", "openrouter", "grok", "manus", "nemotron"):
                if provider == "manus":
                    headers = {
                        "API_KEY": key,
                        "Content-Type": "application/json",
                    }
                else:
                    headers = {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    }
                
                if provider == "openai":
                    url = "https://api.openai.com/v1/chat/completions"
                elif provider == "openrouter":
                    url = f"{self.settings.openrouter_base_url}/chat/completions"
                elif provider == "grok":
                    url = "https://api.x.ai/v1/chat/completions"
                elif provider == "manus":
                    url = f"{self.settings.manus_base_url.rstrip('/')}/chat/completions"
                elif provider == "nemotron":
                    url = f"{self.settings.nemotron_base_url.rstrip('/')}/chat/completions"
                else:
                    raise ValueError(f"Unknown provider: {provider}")

                payload = {
                    "model": model,
                    "messages": [],
                    "temperature": temp,
                    "max_tokens": max_tok,
                }
                if system_prompt:
                    payload["messages"].append({"role": "system", "content": system_prompt})
                payload["messages"].append({"role": "user", "content": prompt})
                
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}
                    
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    raise httpx.HTTPStatusError(
                        f"{provider.upper()} API error {resp.status_code}: {resp.text[:300]}",
                        request=resp.request,
                        response=resp,
                    )
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                
                usage = data.get("usage", {})
                tokens_in = usage.get("prompt_tokens", len(prompt.split()) * 4 // 3)
                tokens_out = usage.get("completion_tokens", len(content.split()) * 4 // 3)
                
                return content, tokens_in, tokens_out, resp.status_code

        raise ValueError(f"Unknown LLM provider: {provider}")

    def _estimate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost based on model name pattern matching."""
        model_lower = model.lower()

        # Find best matching cost tier
        for key, (in_rate, out_rate) in COST_METRICS.items():
            if key == "default":
                continue
            if key in model_lower:
                return (tokens_in * in_rate + tokens_out * out_rate) / 1_000_000

        in_rate, out_rate = COST_METRICS["default"]
        return (tokens_in * in_rate + tokens_out * out_rate) / 1_000_000

    async def _log_execution_and_emit_debug(
        self,
        role: AgentRole,
        prompt: str,
        content: str,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        latency_ms: int,
    ):
        from config.settings import active_session_id_var, active_topic_var
        session_id = active_session_id_var.get()
        topic = active_topic_var.get() or "Autonomous Multi-Agent Systems"

        if session_id:
            # Emit WebSocket debug events
            try:
                from memory.session import get_session_memory
                session_mem = get_session_memory()
                await session_mem.push_event(session_id, {
                    "agent": role.value,
                    "type": "debug",
                    "data": {
                        "topic": topic,
                        "prompt": prompt,
                        "response": content,
                        "provider": provider,
                        "model": f"{provider}:{model}",
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "token_count": tokens_in + tokens_out,
                        "response_length": len(content),
                        "cost": cost,
                        "latency": latency_ms,
                    }
                })
                # Cache raw output
                await session_mem.set_state(session_id, {
                    "raw_llm_output": content,
                    "writer_prompt": prompt if role == AgentRole.WRITER else None,
                })
            except Exception as e:
                logger.warning("failed_pushing_debug_event", error=str(e))

            # Log execution details to PostgreSQL
            try:
                from memory.metadata import get_metadata_store
                metadata = get_metadata_store()
                await metadata.log_agent_execution(
                    session_id=session_id,
                    agent_name=role.value,
                    status="success",
                    input_data={"prompt": prompt},
                    output_data={"response": content},
                    tokens_used=tokens_in + tokens_out,
                    duration_ms=latency_ms,
                    error=None,
                    model_name=f"{provider}:{model}",
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost=cost,
                    latency=latency_ms,
                )
            except Exception as e:
                logger.warning("failed_logging_llm_execution", error=str(e))


# Singleton manager
_llm_manager = None


def get_llm_manager() -> LLMManager:
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager
