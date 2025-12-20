# services/structured_llm.py
import os
import json
import logging
import threading
from typing import Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None
_client_lock = threading.Lock()

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError("OPENAI_API_KEY is missing")
                _client = OpenAI(api_key=api_key)
    return _client

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def generate_structured_json(prompt: str) -> Dict[str, Any]:
    """
    Generates a deterministic JSON response from the LLM.
    Enforces 'response_format={"type": "json_object"}'.
    """
    client = _get_client()
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0, # Deterministic
            response_format={"type": "json_object"}
        )
        
        if not response.choices:
            raise ValueError("No choices returned from LLM")
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")            
        return json.loads(content)
        
    except Exception as e:
        logger.error(f"Structured LLM Call Failed: {e}")
        # Can re-raise or return empty dict depending on policy.
        # Raising allows retry logic in agent.
        raise e
