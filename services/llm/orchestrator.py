# File: services/llm/orchestrator.py
import logging
from typing import Optional
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import requests
import openai
from services.llm_service import generate_response, LLMGenerationError

logger = logging.getLogger(__name__)

# Phase 6: Centralized LLM Chain
MODEL_CHAIN = [
    ("openai", "gpt-4o-mini"),
    ("openrouter", "google/gemini-2.0-flash-exp:free"), 
    ("openrouter", "meta-llama/llama-3.1-8b-instruct"),
    ("openrouter", "mistralai/mistral-7b-instruct")
]

class LLMOrchestrator:
    """
    Centralized LLM Orchestrator that handles multi-model fallback chains and robust retries.
    """
    _global_llm_lock = None
    _last_llm_call_time = 0.0

    @classmethod
    def _get_lock(cls):
        import asyncio
        if cls._global_llm_lock is None:
            try:
                cls._global_llm_lock = asyncio.Lock()
            except RuntimeError:
                # If there's no event loop running yet
                pass
        return cls._global_llm_lock

    @classmethod
    async def _wait_for_rate_limit(cls):
        import asyncio
        import time
        import os
        
        lock = cls._get_lock()
        if not lock:
            return # fallback if lock creation failed (e.g. sync context)

        async with lock:
            current_time = time.time()
            # Default to 12 seconds for Google AI Studio Free Tier (5 RPM)
            min_delay = float(os.getenv("LLM_MIN_DELAY", "12.0"))
            
            elapsed = current_time - cls._last_llm_call_time
            if elapsed < min_delay:
                wait_time = min_delay - elapsed
                logger.info(f"LLMOrchestrator: Global rate limit active. Waiting {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)
            
            # Update the last call time *after* waiting, 
            # so the next call measures from when this call actually starts
            cls._last_llm_call_time = time.time()
    
    @staticmethod
    @retry(
        wait=wait_exponential(min=1, max=20), 
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((
            ConnectionError, 
            TimeoutError, 
            requests.exceptions.RequestException,
            openai.APIConnectionError, 
            openai.RateLimitError, 
            openai.InternalServerError, 
            openai.APITimeoutError,
            LLMGenerationError
        ))
    )
    async def robust_generate_response(prompt: str, system_prompt: str = "", temperature: float = 0.3, cache_id: Optional[str] = None) -> str:
        """
        Executes an LLM call using the multi-model fallback chain and exponential backoff.
        """
        import asyncio
        import random
        last_exception = None
        
        for provider, model in MODEL_CHAIN:
            try:
                logger.debug(f"LLMOrchestrator: Attempting with {provider}/{model}")
                
                # Apply global rate limit wait before generating
                await LLMOrchestrator._wait_for_rate_limit()

                return await asyncio.to_thread(
                    generate_response,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                    temperature=temperature,
                    provider=provider,
                    cache_id=cache_id
                )
            except Exception as e:
                logger.warning(f"LLMOrchestrator: Fallback triggered. {provider}/{model} failed: {e}")
                last_exception = e
                
                # Check explicitly for known rate limit exceptions
                import httpx
                is_rate_limit = False
                if isinstance(e, openai.RateLimitError):
                    is_rate_limit = True
                elif isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
                    is_rate_limit = True
                    
                if is_rate_limit:
                    backoff = random.uniform(5.0, 15.0)
                    logger.info(f"LLMOrchestrator: Rate limited. Sleeping for {backoff:.2f}s before fallback.")
                    await asyncio.sleep(backoff)
                
        # If we exit the loop, ALL models failed. 
        # Raising an exception here triggers Tenacity to sleep and retry the whole chain.
        logger.error("LLMOrchestrator: All models in the chain failed. Triggering tenacity retry.")
        if last_exception:
            raise last_exception
        raise LLMGenerationError("All fallback models exhausted")

    @staticmethod
    def create_context_cache(state: dict) -> str:
        """
        Extracts static research context and pushes it to Google GenAI Caching.
        """
        import os
        import datetime
        from services.reporting.context_builder import ContextBuilder

        provider = os.getenv("PRIMARY_PROVIDER", "openai").lower()
        if provider != "google":
            logger.info("Context caching skipped: Provider is not 'google'.")
            return ""

        try:
            import google.generativeai as genai
            from google.generativeai import caching
            
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            
            # Use specific caching model version based on primary model or default 1.5 pro
            model_name = os.getenv("PRIMARY_MODEL", "models/gemini-1.5-pro-001")
            if not model_name.startswith("models/"):
                model_name = f"models/{model_name}"

            static_content = ContextBuilder.build_static_context_for_cache(state)
            
            if not static_content.strip():
                return ""

            cache = caching.CachedContent.create(
                model=model_name,
                display_name=f"VRA_Cache_{state.get('session_id', 'unknown')}",
                system_instruction="You are an expert research analyst compiling a comprehensive report.",
                contents=[static_content],
                ttl=datetime.timedelta(minutes=60),
            )
            logger.info(f"Successfully created Gemini Context Cache: {cache.name}")
            return cache.name
        except Exception as e:
            logger.error(f"Failed to create Google Context Cache: {e}")
            return ""

    @staticmethod
    def is_cache_valid(cache_id: str) -> bool:
        """
        Checks if the Gemini cache is still alive (e.g. hasn't expired its 60 min TTL).
        """
        if not cache_id:
            return False
            
        try:
            import os
            import google.generativeai as genai
            from google.generativeai import caching
            
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            caching.CachedContent.get(cache_id)
            return True
        except Exception as e:
            logger.warning(f"Cache {cache_id} validity check failed (likely expired): {e}")
            return False

    @staticmethod
    def delete_context_cache(cache_id: str):
        """
        Deletes the Gemini Context Cache.
        """
        if not cache_id:
            return
            
        try:
            import google.generativeai as genai
            from google.generativeai import caching
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            caching.CachedContent.get(cache_id).delete()
            logger.info(f"Successfully deleted Gemini Context Cache: {cache_id}")
        except Exception as e:
            logger.error(f"Failed to delete Google Context Cache {cache_id}: {e}")

