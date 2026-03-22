# File: services/llm/orchestrator.py
import logging
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
    async def robust_generate_response(prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
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
                    provider=provider
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
