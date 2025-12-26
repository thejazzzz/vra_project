import os
import json
import logging
from typing import Optional, Dict, Any
from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None

class LLMGenerationError(Exception):
    """Raised when the LLM fails to generate a response."""
    pass

class LLMJSONParseError(Exception):
    """Raised when the LLM response cannot be parsed as JSON."""
    pass

def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        _client = OpenAI(api_key=api_key)
    return _client

def generate_response(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.7, system_prompt: str = "") -> str:
    """
    Generates a text response from the LLM.
    Raises:
        LLMGenerationError: If the API call fails.
    """
    try:
        client = get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            timeout=30.0
        )
        if not response.choices or not response.choices[0].message.content:
            logger.error("LLM returned empty response or no content")
            raise LLMGenerationError("LLM returned empty response")
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"LLM Generation Failed: {e}", exc_info=True)
        raise LLMGenerationError(f"Failed to generate LLM response: {e}") from e

def generate_json_response(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.5, system_prompt: str = "") -> Dict[str, Any]:
    """
    Generates a JSON response. Enforces JSON mode.
    Raises:
        LLMGenerationError: If the API call fails.
        LLMJSONParseError: If the response is not valid JSON.
    """
    content = ""
    try:
        client = get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
            timeout=30.0
        )
        
        if not response.choices or not response.choices[0].message.content:
            logger.error("LLM returned empty response or no content")
            raise LLMGenerationError("LLM returned empty response")

        content = response.choices[0].message.content
        return json.loads(content)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}. Content: {content}")
        raise LLMJSONParseError(f"Failed to parse JSON from LLM response: {e}") from e
    except Exception as e:
        # Re-raise already custom exceptions
        if isinstance(e, (LLMGenerationError, LLMJSONParseError)):
            raise e
        logger.error(f"LLM JSON Generation Failed: {e}", exc_info=True)
        raise LLMGenerationError(f"Failed to generate JSON response: {e}") from e
