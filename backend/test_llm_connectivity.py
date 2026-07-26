"""
LLM Provider Connectivity Test
===============================
Sends "Hello" to every configured provider and reports:
- Which provider succeeded
- Which provider failed
- Exact exception trace
- Endpoint URL and payload format validation
- Model name validation

Usage:
    cd backend
    python test_llm_connectivity.py
"""

import asyncio
import json
import os
import sys
import time
import traceback

import httpx
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()

# ── Provider configurations ──────────────────────────────────
PROVIDERS = {
    "openrouter": {
        "env_key": "OPENROUTER_API_KEY",
        "env_base": "OPENROUTER_BASE_URL",
        "default_base": "https://openrouter.ai/api/v1",
        "endpoint": "/chat/completions",
        "models": ["openai/gpt-4o-mini", "openai/gpt-4o", "meta-llama/llama-3.1-8b-instruct"],
        "payload_builder": lambda model, base_url: {
            "url": f"{base_url}/chat/completions",
            "model": model,
        },
    },
    "gemini": {
        "env_key": "GEMINI_API_KEY",
        "models": ["gemini-2.5-flash", "gemini-2.5-flash-lite"],
    },
    "gemma": {
        "env_key": "GEMMA_API_KEY",
        "models": ["gemma-4-31b-it", "gemma-4-26b-a4b-it"],
    },
    "manus": {
        "env_key": "MANUS_API_KEY",
        "env_base": "MANUS_BASE_URL",
        "default_base": "https://api.manus.im/v1",
        "endpoint": "/chat/completions",
        "models": ["manus-v1"],
        "auth_header": "API_KEY",
    },
    "grok": {
        "env_key": "GROK_API_KEY",
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "models": ["grok-4.3", "grok-latest"],
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "models": ["gpt-4o-mini", "gpt-4o"],
    },
}


def _mask_key(key: str) -> str:
    if not key:
        return "NOT SET"
    if len(key) < 16:
        return key[:4] + "****"
    return key[:12] + "..." + key[-6:]


async def test_openai_compatible(
    provider: str, url: str, key: str, model: str, timeout: float = 15.0
) -> dict:
    """Test an OpenAI-compatible endpoint (OpenRouter, Grok, OpenAI)."""
    result = {
        "provider": provider,
        "model": model,
        "url": url,
        "api_key_loaded": bool(key),
        "status": "untested",
        "status_code": 0,
        "response": "",
        "latency_ms": 0,
        "error": "",
        "exception_trace": "",
    }

    if not key:
        result["status"] = "skipped_no_key"
        return result

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 30,
        "temperature": 0.1,
    }

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            auth_headers = {"Content-Type": "application/json"}
            if provider == "manus":
                auth_headers["API_KEY"] = key
            else:
                auth_headers["Authorization"] = f"Bearer {key}"
            resp = await client.post(
                url,
                headers=auth_headers,
                json=payload,
            )
            result["status_code"] = resp.status_code
            result["latency_ms"] = int((time.monotonic() - start) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                result["status"] = "success"
                result["response"] = content[:200]
            else:
                result["status"] = "failed"
                result["error"] = resp.text[:500]
    except Exception as e:
        result["latency_ms"] = int((time.monotonic() - start) * 1000)
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)}"
        result["exception_trace"] = traceback.format_exc()

    return result


async def test_gemini(key: str, model: str, timeout: float = 15.0) -> dict:
    """Test the Gemini API."""
    result = {
        "provider": "gemini",
        "model": model,
        "url": f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "api_key_loaded": bool(key),
        "status": "untested",
        "status_code": 0,
        "response": "",
        "latency_ms": 0,
        "error": "",
        "exception_trace": "",
    }

    if not key:
        result["status"] = "skipped_no_key"
        return result

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    )
    payload = {
        "contents": [{"parts": [{"text": "Hello"}]}],
        "generationConfig": {"maxOutputTokens": 30, "temperature": 0.1},
    }

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            result["status_code"] = resp.status_code
            result["latency_ms"] = int((time.monotonic() - start) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                result["status"] = "success"
                result["response"] = content[:200]
            else:
                result["status"] = "failed"
                result["error"] = resp.text[:500]
    except Exception as e:
        result["latency_ms"] = int((time.monotonic() - start) * 1000)
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)}"
        result["exception_trace"] = traceback.format_exc()

    return result


async def run_all_tests() -> dict:
    """Run connectivity tests for all configured providers."""
    results = []
    summary = {"succeeded": [], "failed": [], "skipped": []}

    print("=" * 70)
    print("  ResearchOS LLM Provider Connectivity Test")
    print("=" * 70)
    print()

    # ── 1. Environment check ──
    print("── Environment Variables ──")
    for prov_name, config in PROVIDERS.items():
        key = os.getenv(config["env_key"], "")
        print(f"  {config['env_key']}: {_mask_key(key)}")
    print()

    # ── 2. Test OpenRouter ──
    print("── Testing OpenRouter ──")
    or_key = os.getenv("OPENROUTER_API_KEY", "")
    or_base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    print(f"  Base URL: {or_base}")

    for model in PROVIDERS["openrouter"]["models"]:
        url = f"{or_base}/chat/completions"
        print(f"  Testing model: {model} ... ", end="", flush=True)
        r = await test_openai_compatible("openrouter", url, or_key, model)
        results.append(r)
        _print_result(r)
        if r["status"] == "success":
            summary["succeeded"].append(f"openrouter:{model}")
        elif r["status"] == "skipped_no_key":
            summary["skipped"].append(f"openrouter:{model}")
        else:
            summary["failed"].append(f"openrouter:{model}")
    print()

    # ── 3. Test Gemini ──
    print("── Testing Gemini ──")
    gem_key = os.getenv("GEMINI_API_KEY", "")
    for model in PROVIDERS["gemini"]["models"]:
        print(f"  Testing model: {model} ... ", end="", flush=True)
        r = await test_gemini(gem_key, model)
        results.append(r)
        _print_result(r)
        if r["status"] == "success":
            summary["succeeded"].append(f"gemini:{model}")
        elif r["status"] == "skipped_no_key":
            summary["skipped"].append(f"gemini:{model}")
        else:
            summary["failed"].append(f"gemini:{model}")
    print()

    # ── Test Gemma ──
    print("── Testing Gemma ──")
    gemma_key = os.getenv("GEMMA_API_KEY", "")
    for model in PROVIDERS["gemma"]["models"]:
        print(f"  Testing model: {model} ... ", end="", flush=True)
        r = await test_gemini(gemma_key, model)
        r["provider"] = "gemma"
        results.append(r)
        _print_result(r)
        if r["status"] == "success":
            summary["succeeded"].append(f"gemma:{model}")
        elif r["status"] == "skipped_no_key":
            summary["skipped"].append(f"gemma:{model}")
        else:
            summary["failed"].append(f"gemma:{model}")
    print()

    # ── Test Manus ──
    print("── Testing Manus ──")
    manus_key = os.getenv("MANUS_API_KEY", "")
    manus_base = os.getenv("MANUS_BASE_URL", "https://api.manus.ai/v1")
    print(f"  Base URL: {manus_base}")
    for model in PROVIDERS["manus"]["models"]:
        url = f"{manus_base.rstrip('/')}/chat/completions"
        print(f"  Testing model: {model} ... ", end="", flush=True)
        r = await test_openai_compatible("manus", url, manus_key, model)
        results.append(r)
        _print_result(r)
        if r["status"] == "success":
            summary["succeeded"].append(f"manus:{model}")
        elif r["status"] == "skipped_no_key":
            summary["skipped"].append(f"manus:{model}")
        else:
            summary["failed"].append(f"manus:{model}")
    print()

    # ── 4. Test Grok ──
    print("── Testing Grok ──")
    grok_key = os.getenv("GROK_API_KEY", "")
    for model in PROVIDERS["grok"]["models"]:
        url = PROVIDERS["grok"]["endpoint"]
        print(f"  Testing model: {model} ... ", end="", flush=True)
        r = await test_openai_compatible("grok", url, grok_key, model)
        results.append(r)
        _print_result(r)
        if r["status"] == "success":
            summary["succeeded"].append(f"grok:{model}")
        elif r["status"] == "skipped_no_key":
            summary["skipped"].append(f"grok:{model}")
        else:
            summary["failed"].append(f"grok:{model}")
    print()

    # ── 5. Test OpenAI ──
    print("── Testing OpenAI ──")
    oai_key = os.getenv("OPENAI_API_KEY", "")
    for model in PROVIDERS["openai"]["models"]:
        url = PROVIDERS["openai"]["endpoint"]
        print(f"  Testing model: {model} ... ", end="", flush=True)
        r = await test_openai_compatible("openai", url, oai_key, model)
        results.append(r)
        _print_result(r)
        if r["status"] == "success":
            summary["succeeded"].append(f"openai:{model}")
        elif r["status"] == "skipped_no_key":
            summary["skipped"].append(f"openai:{model}")
        else:
            summary["failed"].append(f"openai:{model}")
    print()

    # ── 6. Summary Report ──
    print("=" * 70)
    print("  CONNECTIVITY REPORT")
    print("=" * 70)
    print()

    if summary["succeeded"]:
        print("  ✅ SUCCEEDED:")
        for s in summary["succeeded"]:
            print(f"     • {s}")
    else:
        print("  ✅ SUCCEEDED: None")

    if summary["failed"]:
        print()
        print("  ❌ FAILED:")
        for f in summary["failed"]:
            print(f"     • {f}")
            # Print error details
            for r in results:
                if f"{r['provider']}:{r['model']}" == f:
                    print(f"       Status: {r['status_code']}")
                    if r["error"]:
                        print(f"       Error: {r['error'][:200]}")
    else:
        print("  ❌ FAILED: None")

    if summary["skipped"]:
        print()
        print("  ⏭️  SKIPPED (no API key):")
        for s in summary["skipped"]:
            print(f"     • {s}")

    print()

    # ── 7. Recommendation ──
    if not summary["succeeded"] and not summary["skipped"]:
        print("  ⚠️  ALL PROVIDERS FAILED!")
        print("     Check your API keys and network connectivity.")
        print("     The Planner WILL NOT be able to generate responses.")
    elif not summary["succeeded"] and summary["skipped"]:
        print("  ⚠️  No providers succeeded (some skipped due to missing keys).")
        print("     Add at least one valid API key to .env")
    elif summary["succeeded"]:
        first = summary["succeeded"][0]
        print(f"  🎯 Primary working provider: {first}")
        print("     The pipeline should work with this provider.")

    print()
    print("=" * 70)

    return {
        "results": results,
        "summary": summary,
    }


def _print_result(r: dict):
    if r["status"] == "success":
        print(f"✅ OK ({r['latency_ms']}ms) → {r['response'][:60]}")
    elif r["status"] == "skipped_no_key":
        print("⏭️  SKIPPED (no API key)")
    elif r["status"] == "failed":
        print(f"❌ FAILED (HTTP {r['status_code']}, {r['latency_ms']}ms)")
    else:
        print(f"❌ ERROR ({r['latency_ms']}ms): {r['error'][:80]}")


if __name__ == "__main__":
    report = asyncio.run(run_all_tests())

    # Save report to JSON for programmatic use
    report_path = os.path.join(os.path.dirname(__file__), "llm_connectivity_report.json")
    serializable = {
        "summary": report["summary"],
        "results": [
            {k: v for k, v in r.items() if k != "exception_trace"} for r in report["results"]
        ],
    }
    with open(report_path, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"  Report saved to: {report_path}")

    # Exit with error code if no providers succeeded
    if not report["summary"]["succeeded"]:
        sys.exit(1)
