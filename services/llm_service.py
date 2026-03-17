#File: services/llm_service.py

import os
import json
import logging
from typing import Optional, Dict, Any, Union
from openai import OpenAI

from dotenv import load_dotenv
from services.llm_factory import LLMFactory, LLMProvider

load_dotenv()

logger = logging.getLogger(__name__)

# Legacy support: Default to OpenAI for existing agents
DEFAULT_PROVIDER = LLMProvider.OPENAI

class LLMGenerationError(Exception):
    """Raised when the LLM fails to generate a response."""
    pass

class LLMJSONParseError(Exception):
    """Raised when the LLM response cannot be parsed as JSON."""
    pass

def get_client(provider: str = DEFAULT_PROVIDER) -> OpenAI:
    """Delegate to Factory."""
    return LLMFactory.get_client(provider=provider)

def generate_response(
    prompt: str, 
    model: Optional[str] = None, 
    temperature: float = 0.7, 
    system_prompt: str = "",
    provider: str = DEFAULT_PROVIDER
) -> str:
    """
    Generates a text response from the LLM.
    """
    import time
    from openai import RateLimitError, APIError

    client = get_client(provider)
    
    # Resolve model if not provided
    if not model:
        model = LLMFactory.get_default_model(provider)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    max_retries_429 = 3
    base_delay = 15 # Start with 15s delay

    for attempt in range(max_retries_429 + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                timeout=60.0
            )
            if not response.choices or not response.choices[0].message.content:
                logger.error("LLM returned empty response or no content")
                raise LLMGenerationError("LLM returned empty response")
            return response.choices[0].message.content
            
        except RateLimitError as e:
            if attempt < max_retries_429:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit (429) for {provider}/{model}. Retrying in {delay}s... (Attempt {attempt+1}/{max_retries_429})")
                time.sleep(delay)
            else:
                logger.error(f"LLM Generation Failed after retries ({provider}/{model}): {e}", exc_info=True)
                raise LLMGenerationError(f"Failed to generate LLM response (Rate Limit): {e}") from e
                
        except Exception as e:
            # For non-429 errors, fail immediately or handle appropriately
            logger.error(f"LLM Generation Failed ({provider}/{model}): {e}", exc_info=True)
            raise LLMGenerationError(f"Failed to generate LLM response: {e}") from e

def generate_json_response(
    prompt: str, 
    model: Optional[str] = None, 
    temperature: float = 0.5, 
    system_prompt: str = "",
    provider: str = DEFAULT_PROVIDER
) -> Dict[str, Any]:
    """
    Generates a JSON response. Enforces JSON mode.
    """
    content = ""
    try:
        client = get_client(provider)
        if not model:
            model = LLMFactory.get_default_model(provider)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        import time
        from openai import RateLimitError, APIError

        max_retries_429 = 3
        base_delay = 15 # Start with 15s delay

        for attempt in range(max_retries_429 + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    timeout=60.0
                )
                
                if not response.choices or not response.choices[0].message.content:
                    logger.error("LLM returned empty response or no content")
                    raise LLMGenerationError("LLM returned empty response")

                content = response.choices[0].message.content
                return json.loads(content)

            except RateLimitError as e:
                if attempt < max_retries_429:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"JSON Rate limit hit (429) for {provider}/{model}. Retrying in {delay}s... (Attempt {attempt+1}/{max_retries_429})")
                    time.sleep(delay)
                else:
                    logger.error(f"LLM JSON Generation Failed after retries ({provider}/{model}): {e}", exc_info=True)
                    raise LLMGenerationError(f"Failed to generate JSON response (Rate Limit): {e}") from e
                    
            except Exception as e:
                # Let outer catch block handle parse errors or total failures
                raise e

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}. Content: {content}")
        raise LLMJSONParseError(f"Failed to parse JSON from LLM response: {e}") from e
    except Exception as e:
        if isinstance(e, (LLMGenerationError, LLMJSONParseError)):
            raise e
        logger.error(f"LLM JSON Generation Failed: {e}", exc_info=True)
        raise LLMGenerationError(f"Failed to generate JSON response: {e}") from e
