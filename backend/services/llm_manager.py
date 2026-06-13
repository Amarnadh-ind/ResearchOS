"""
Multi-Provider LLM Manager
Handles automatic provider failover, token tracking, latency tracking, health checks, and diagnostics.
"""

import json
import time
import traceback
import httpx
import structlog
from typing import Any
from config.settings import get_settings
from config.models import AgentRole

logger = structlog.get_logger()

# Cost per 1M tokens: (input, output) in USD
COST_METRICS = {
    "manus": (2.00, 10.00),
    "gemma-4-31b": (0.10, 0.40),
    "gemma-4-26b": (0.075, 0.30),
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-2.5-flash-lite": (0.0375, 0.15),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    "grok-2": (2.00, 10.00),
    "grok-beta": (2.00, 10.00),
    "gpt-4o-mini": (0.150, 0.60),
    "gpt-4o": (2.50, 10.00),
    "openrouter-fallback": (0.50, 1.50)
}

# ── Valid OpenRouter model slugs (verified) ──────────────────
OPENROUTER_MODELS = {
    "fast": "openai/gpt-4o-mini",
    "standard": "openai/gpt-4o",
    "quality": "anthropic/claude-3.5-sonnet",
    "fallback": "meta-llama/llama-3.1-8b-instruct",
}


class LLMManager:
    """Manages multi-provider LLM routing and failovers."""
    
    _diagnostics: dict[str, dict] = {
        "openrouter": {"connected": False, "latency": 0.0, "last_status": 0, "last_error": "", "last_model": ""},
        "gemini": {"connected": False, "latency": 0.0, "last_status": 0, "last_error": "", "last_model": ""},
        "grok": {"connected": False, "latency": 0.0, "last_status": 0, "last_error": "", "last_model": ""},
        "openai": {"connected": False, "latency": 0.0, "last_status": 0, "last_error": "", "last_model": ""},
    }

    _model_diagnostics: dict[str, dict] = {
        "manus": {"connected": False, "latency": 0, "last_status": 0, "last_error": "", "provider": "manus"},
        "gemini-2.5-flash": {"connected": False, "latency": 0, "last_status": 0, "last_error": "", "provider": "gemini"},
        "gemini-2.5-flash-lite": {"connected": False, "latency": 0, "last_status": 0, "last_error": "", "provider": "gemini"},
        "mock-fallback": {"connected": True, "latency": 10, "last_status": 200, "last_error": "", "provider": "mock"},
    }

    _discovered_gemma_models: list[str] = []
    _discovered_gemini_models: list[str] = []
    _discovered_status: dict[str, str] = {
        "manus": "untested",
        "gemma": "untested",
        "gemini": "untested"
    }

    _default_gemma_models: list[str] = ["gemma-4-31b-it", "gemma-4-26b-a4b-it"]
    _default_gemini_models: list[str] = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

    @classmethod
    async def discover_google_models(cls):
        """Discovers Google (Gemini and Gemma) models dynamically from ListModels endpoint."""
        settings = get_settings()
        key = settings.gemini_api_key or settings.gemma_api_key
        if not key:
            cls._discovered_status["gemini"] = "invalid API key"
            cls._discovered_status["gemma"] = "invalid API key"
            logger.info("skip_google_discovery_no_key")
            return

        cls._discovered_gemma_models = []
        cls._discovered_gemini_models = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                resp = await client.get(url)
                
                if resp.status_code == 200:
                    data = resp.json()
                    models_list = data.get("models", [])
                    
                    # Log the list
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

                    cls._discovered_status["gemini"] = "online" if cls._discovered_gemini_models else "unavailable model"
                    cls._discovered_status["gemma"] = "online" if cls._discovered_gemma_models else "unavailable model"
                    
                    # Synchronize _model_diagnostics
                    for k in list(cls._model_diagnostics.keys()):
                        if cls._model_diagnostics[k].get("provider") in ("gemini", "gemma"):
                            del cls._model_diagnostics[k]
                            
                    for m in cls._discovered_gemini_models:
                        cls._model_diagnostics[m] = {
                            "connected": False,
                            "latency": 0,
                            "last_status": 0,
                            "last_error": "",
                            "provider": "gemini"
                        }
                    for m in cls._discovered_gemma_models:
                        cls._model_diagnostics[m] = {
                            "connected": False,
                            "latency": 0,
                            "last_status": 0,
                            "last_error": "",
                            "provider": "gemma"
                        }
                        
                elif resp.status_code in (400, 403):
                    cls._discovered_status["gemini"] = "invalid API key"
                    cls._discovered_status["gemma"] = "invalid API key"
                    logger.error("google_discovery_failed_key", status=resp.status_code, error=resp.text)
                elif resp.status_code == 429:
                    cls._discovered_status["gemini"] = "quota exceeded"
                    cls._discovered_status["gemma"] = "quota exceeded"
                    logger.error("google_discovery_quota_exceeded")
                else:
                    cls._discovered_status["gemini"] = "connection failure"
                    cls._discovered_status["gemma"] = "connection failure"
                    logger.error("google_discovery_failed_status", status=resp.status_code, error=resp.text)
                    
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            cls._discovered_status["gemini"] = "connection failure"
            cls._discovered_status["gemma"] = "connection failure"
            logger.error("google_discovery_connection_error", error=str(e))
        except Exception as e:
            cls._discovered_status["gemini"] = "connection failure"
            cls._discovered_status["gemma"] = "connection failure"
            logger.error("google_discovery_unexpected_error", error=str(e))

    @classmethod
    def get_provider_diagnostics(cls) -> dict:
        """Return per-provider diagnostics with api_key_loaded and connection_status."""
        settings = get_settings()
        result = {}
        for prov in ["manus", "gemma", "gemini"]:
            key = getattr(settings, f"{prov}_api_key", "")
            
            # Find the first connected model for this provider
            connected = False
            latency = 0
            last_status = 200
            last_error = ""
            last_model = ""
            
            for model_name, diag in cls._model_diagnostics.items():
                if diag.get("provider") == prov:
                    last_model = model_name
                    if diag.get("connected"):
                        connected = True
                        latency = diag.get("latency", 0)
                        last_status = diag.get("last_status", 200)
                        last_error = ""
                        break
                    else:
                        latency = 0
                        last_status = diag.get("last_status", 500)
                        last_error = diag.get("last_error", "")
            
            if not key:
                conn_status = "no_key"
            elif cls._discovered_status.get(prov) == "unavailable model":
                conn_status = "untested"  # Do not mark provider as failed
                last_error = "unavailable model"
            elif cls._discovered_status.get(prov) in ("invalid API key", "quota exceeded", "connection failure"):
                conn_status = "failed"
                last_error = cls._discovered_status.get(prov)
            elif connected:
                conn_status = "connected"
            elif last_status > 0:
                conn_status = "failed"
            else:
                conn_status = "untested"
                
            result[prov] = {
                "provider": prov,
                "model": last_model,
                "api_key_loaded": bool(key),
                "connection_status": conn_status,
                "latency_ms": latency,
                "last_status_code": last_status,
                "last_error": last_error or (cls._discovered_status.get(prov) if cls._discovered_status.get(prov) != "online" else ""),
            }
        return result

    @classmethod
    async def verify_startup_health(cls):
        """Runs short connection test for all available provider keys at startup."""
        import os
        settings = get_settings()
        
        # ── Startup Diagnostics Banner ──
        print("\n" + "="*70)
        print("         ResearchOS LLM Provider Startup Diagnostics")
        print("="*70)
        print("Verifying Environment Variables:")
        for var in ["MANUS_API_KEY", "GEMMA_API_KEY", "GEMINI_API_KEY"]:
            val = os.getenv(var, "")
            present = "true" if val else "false"
            masked = val[:12] + "..." if val else ""
            print(f"  - {var}: present={present} {f'({masked})' if val else ''}")
            
        # Discover Google models dynamically
        await cls.discover_google_models()

        print("\nLoaded Providers:")
        providers_check = [
            ("MANUS", settings.manus_api_key, "manus"),
        ]
        
        gemma_list = cls._discovered_gemma_models if cls._discovered_status["gemma"] != "untested" else cls._default_gemma_models
        gemini_list = cls._discovered_gemini_models if cls._discovered_status["gemini"] != "untested" else cls._default_gemini_models

        for m in gemma_list:
            providers_check.append(("GEMMA", settings.gemma_api_key, m))
        for m in gemini_list:
            providers_check.append(("GEMINI", settings.gemini_api_key, m))

        for name, key, model in providers_check:
            print(f"  - {name}:")
            print(f"      API Key Present? {'true' if key else 'false'}")
            print(f"      Model Selected: {model}")
        print("="*70 + "\n", flush=True)

        logger.info("llm_manager_startup_verification")
        
        # Test Manus
        if settings.manus_api_key:
            await cls.test_model_health("manus", "manus")
        else:
            logger.info("startup_health_skip", provider="manus", reason="No API key")
            
        # Test Gemma
        if settings.gemma_api_key:
            for m in gemma_list:
                await cls.test_model_health("gemma", m)
        else:
            logger.info("startup_health_skip", provider="gemma", reason="No API key")

        # Test Gemini
        if settings.gemini_api_key:
            for m in gemini_list:
                await cls.test_model_health("gemini", m)
        else:
            logger.info("startup_health_skip", provider="gemini", reason="No API key")

    @classmethod
    async def test_model_health(cls, provider: str, model: str) -> bool:
        """Runs a health check for a specific model."""
        settings = get_settings()
        key = getattr(settings, f"{provider}_api_key", "")
        if not key:
            cls._model_diagnostics[model] = {
                "connected": False,
                "latency": 0,
                "last_status": 0,
                "last_error": "invalid API key",
                "provider": provider,
            }
            return False
            
        start_time = time.monotonic()
        connected = False
        status_code = 0
        error_msg = ""
        error_class = ""
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                if provider == "manus":
                    base_url = settings.manus_base_url.rstrip("/") if settings.manus_base_url else "https://api.manus.ai/v1"
                    url = f"{base_url}/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"
                    }
                    resp = await client.post(
                        url,
                        headers=headers,
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 5
                        }
                    )
                else:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                    resp = await client.post(
                        url,
                        json={
                            "contents": [{"parts": [{"text": "ping"}]}],
                            "generationConfig": {"maxOutputTokens": 5}
                        }
                    )
                status_code = resp.status_code
                if status_code != 200:
                    error_msg = resp.text[:500]
                    # Classify error based on status code
                    if status_code in (400, 403):
                        error_class = "invalid API key"
                    elif status_code == 429:
                        error_class = "quota exceeded"
                    else:
                        error_class = "connection failure"
                connected = (status_code == 200)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            status_code = 0
            error_class = "connection failure"
            
        latency = time.monotonic() - start_time
        latency_ms = int(latency * 1000) if connected else 0
        
        cls._model_diagnostics[model] = {
            "connected": connected,
            "latency": latency_ms,
            "last_status": status_code,
            "last_error": error_class if error_class else error_msg,
            "provider": provider,
        }
        return connected

    @classmethod
    async def test_provider_health(cls, provider: str) -> bool:
        if provider == "gemini":
            m = cls._discovered_gemini_models[0] if cls._discovered_gemini_models else "gemini-2.5-flash"
            return await cls.test_model_health("gemini", m)
        elif provider == "gemma":
            m = cls._discovered_gemma_models[0] if cls._discovered_gemma_models else "gemma-4-31b-it"
            return await cls.test_model_health("gemma", m)
        elif provider == "manus":
            return await cls.test_model_health("manus", "manus")
        return False

    def __init__(self):
        self.settings = get_settings()

    def _get_provider_chain(self, role: AgentRole, preferred_provider: str | None = None) -> list[tuple[str, str]]:
        """Returns ordered list of (provider, model) to try.
        
        Uses priority routing order:
        1. manus
        2. Gemma models (dynamic)
        3. Gemini models (dynamic)
        4. mock-fallback
        """
        settings = get_settings()
        prov = preferred_provider or settings.llm_provider or "auto"
        prov = prov.lower()

        all_candidates = [("manus", "manus")]
        
        gemma_list = self._discovered_gemma_models if self._discovered_status["gemma"] != "untested" else self._default_gemma_models
        gemini_list = self._discovered_gemini_models if self._discovered_status["gemini"] != "untested" else self._default_gemini_models

        # Sort Gemma models: prioritize 31b or similar over others
        gemma_sorted = sorted(
            gemma_list,
            key=lambda x: ("31b" in x.lower(), "26b" in x.lower(), x),
            reverse=True
        )
        for m in gemma_sorted:
            all_candidates.append(("gemma", m))
            
        # Sort Gemini models: prioritize 2.5-flash, then 2.5-flash-lite, etc.
        gemini_sorted = sorted(
            gemini_list,
            key=lambda x: ("lite" not in x.lower(), "2.5-flash" in x.lower(), x),
            reverse=True
        )
        for m in gemini_sorted:
            all_candidates.append(("gemini", m))

        candidates = []
        for p, m in all_candidates:
            # Check key
            key = getattr(settings, f"{p}_api_key", "")
            if not key:
                continue
            
            # Check provider routing filter
            if prov == "manus" and p != "manus":
                continue
            if prov == "gemma" and p != "gemma":
                continue
            if prov == "gemini" and p != "gemini":
                continue
            if prov == "mock":
                continue  # Skip all real LLMs if mock is forced
                
            candidates.append((p, m))

        # Always append mock fallback at the end
        if prov == "mock":
            candidates = [("mock", "mock-fallback")]
        else:
            candidates.append(("mock", "mock-fallback"))

        return candidates


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
        """Executes LLM request with automatic failover down the priority chain."""
        candidates = self._get_provider_chain(role, preferred_provider=provider)
        
        last_error = None
        provider_errors: list[dict] = []
        
        for idx, (prov, model) in enumerate(candidates):
            # ── Pre-call logging (strictly conforming to user specifications) ──
            print(f"provider_attempt={model}", flush=True)
            logger.info("llm_manager_attempt", provider=prov, model=model, role=role.value)
            
            # Handle mock fallback inside candidate chain
            if prov == "mock":
                from services.mock_llm import generate_mock_completion
                from config.settings import active_topic_var
                topic = active_topic_var.get() or prompt
                content = generate_mock_completion(role, system_prompt or "", prompt, topic)
                latency_ms = 10
                
                # Estimate cost
                cost = 0.0
                tokens_in = len(prompt.split()) * 4 // 3
                tokens_out = len(content.split()) * 4 // 3
                
                self._model_diagnostics["mock-fallback"] = {
                    "connected": True,
                    "latency": latency_ms,
                    "last_status": 200,
                    "last_error": "",
                    "provider": "mock",
                }
                
                # Success output format matching specs
                print("provider_success=true", flush=True)
                
                # Log debug outputs and metadata
                await self._log_execution_and_emit_debug(
                    role=role,
                    prompt=prompt,
                    content=content,
                    provider="mock",
                    model="mock-fallback",
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost=cost,
                    latency_ms=latency_ms
                )
                return content
                
            # If real LLM, try calling API
            key = getattr(self.settings, f"{prov}_api_key", "")
            start_time = time.monotonic()
            
            try:
                content, tokens_in, tokens_out, status = await self._call_provider_api(
                    provider=prov,
                    model=model,
                    key=key,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode
                )
                
                latency_ms = int((time.monotonic() - start_time) * 1000)
                
                # Update health check stats dynamically
                self._model_diagnostics[model] = {
                    "connected": True,
                    "latency": latency_ms,
                    "last_status": status,
                    "last_error": "",
                    "provider": prov,
                }
                
                # Estimate cost
                cost = self._estimate_cost(model, tokens_in, tokens_out)
                
                # Success log output matching specs
                print("provider_success=true", flush=True)
                
                # Log debug outputs and metadata
                await self._log_execution_and_emit_debug(
                    role=role,
                    prompt=prompt,
                    content=content,
                    provider=prov,
                    model=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost=cost,
                    latency_ms=latency_ms
                )
                
                return content
                
            except Exception as e:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                error_trace = traceback.format_exc()
                
                status_code = 500
                if hasattr(e, 'response') and e.response is not None:
                    status_code = getattr(e.response, 'status_code', 500)
                elif isinstance(e, httpx.HTTPStatusError):
                    status_code = e.response.status_code
                
                # Print and log failure using exact format requested
                print(f"provider_failed={status_code}", flush=True)
                
                # Log fallback attempt if there's a next candidate
                if idx + 1 < len(candidates):
                    next_model = candidates[idx + 1][1]
                    print(f"fallback_to={next_model}", flush=True)
                    logger.warning("provider_failed_falling_back", 
                                   provider_attempt=model, 
                                   provider_failed=status_code, 
                                   fallback_to=next_model)
                
                error_info = {
                    "provider": prov,
                    "model": model,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "exception_trace": error_trace,
                    "latency_ms": latency_ms,
                    "status_code": status_code,
                }
                provider_errors.append(error_info)
                
                self._model_diagnostics[model] = {
                    "connected": False,
                    "last_status": status_code,
                    "latency": 0,
                    "last_error": str(e)[:500],
                    "provider": prov,
                }
                last_error = e
                continue

        # If all candidates failed
        raise RuntimeError(
            f"All LLM providers failed for role '{role.value}'. Last error: {str(last_error)}"
        )

    def _build_error_report(self, provider_errors: list[dict], skipped: list[str], role: AgentRole) -> dict:
        """Build a structured report of which providers succeeded/failed."""
        succeeded = []
        failed = []
        
        for err in provider_errors:
            failed.append({
                "provider": err["provider"],
                "model": err["model"],
                "error": err["error"],
                "error_type": err["error_type"],
                "exception_trace": err["exception_trace"],
                "latency_ms": err["latency_ms"],
            })
        
        # Check which are actually connected from diagnostics
        for prov, diag in self._diagnostics.items():
            if diag.get("connected"):
                succeeded.append(prov)
        
        return {
            "role": role.value,
            "succeeded_providers": succeeded,
            "failed_providers": failed,
            "skipped_providers_no_key": skipped,
            "total_attempted": len(provider_errors),
            "total_skipped": len(skipped),
        }

    async def _emit_provider_failure_event(self, role: AgentRole, error_report: dict):
        """Emit a WebSocket event with the provider failure report for UI display."""
        from config.settings import active_session_id_var
        session_id = active_session_id_var.get()
        if session_id:
            try:
                from memory.session import get_session_memory
                session_mem = get_session_memory()
                await session_mem.push_event(session_id, {
                    "agent": role.value,
                    "type": "provider_failure",
                    "data": error_report,
                })
            except Exception as e:
                logger.warning("failed_emitting_provider_failure", error=str(e))

    async def _call_provider_api(
        self,
        provider: str,
        model: str,
        key: str,
        prompt: str,
        system_prompt: str | None,
        temperature: float | None,
        max_tokens: int | None,
        json_mode: bool
    ) -> tuple[str, int, int, int]:
        """Performs raw network requests to specific provider APIs."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            temp = temperature if temperature is not None else 0.2
            max_tok = max_tokens if max_tokens is not None else 2000
            
            if provider in ("gemini", "gemma"):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temp,
                        "maxOutputTokens": max_tok
                    }
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
                
            elif provider in ("openai", "openrouter", "grok", "manus"):
                if provider == "openai":
                    url = "https://api.openai.com/v1/chat/completions"
                elif provider == "grok":
                    url = "https://api.x.ai/v1/chat/completions"
                elif provider == "manus":
                    base_url = self.settings.manus_base_url.rstrip("/") if self.settings.manus_base_url else "https://api.manus.ai/v1"
                    url = f"{base_url}/chat/completions"
                else:
                    url = f"{self.settings.openrouter_base_url}/chat/completions"
                    
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
                
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temp,
                    "max_tokens": max_tok
                }
                
                # Grok sometimes rejects response_format, only use it for OpenAI/OpenRouter
                if json_mode and provider != "grok":
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
        # Strip provider prefix for cost lookup (e.g., "openai/gpt-4o-mini" → "gpt-4o-mini")
        model_short = model.split("/")[-1] if "/" in model else model
        in_rate, out_rate = COST_METRICS.get(model_short, COST_METRICS["openrouter-fallback"])
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
        latency_ms: int
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
                        "latency": latency_ms
                    }
                })
                # Cache raw output
                await session_mem.set_state(session_id, {
                    "raw_llm_output": content,
                    "writer_prompt": prompt if role == AgentRole.WRITER else None
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
                    latency=latency_ms
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
