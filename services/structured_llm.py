# services/structured_llm.py
import os
import json
import logging
import threading
from typing import Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel
from openai import OpenAI

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class SchemaModel(BaseModel):
    """Base class for structured output models."""
    pass

class StructuredLLMService:
    def __init__(self):
        self._lock = threading.Lock()
        self._client: Optional[OpenAI] = None
        self._ensure_client()

    def _ensure_client(self):
        with self._lock:
            if not self._client:
                api_key = os.getenv("OPENAI_API_KEY")
                # Fallback or strict error? 
                # For now, we allow it to be None and fail at call time if needed, 
                # or use a dummy for local dev if key is missing.
                if api_key:
                    self._client = OpenAI(api_key=api_key)
                else:
                    logger.warning("OPENAI_API_KEY not found. StructuredLLMService will fail if used with Cloud.")

    @property
    def client(self) -> OpenAI:
        if not self._client:
            self._ensure_client()
            if not self._client:
                raise RuntimeError("OpenAI Client not initialized. missing key?")
        return self._client

    def generate(self, prompt: str, schema: Type[T], model_name: str = None) -> T:
        """
        Generates a structured response complying with the given Pydantic schema.
        """
        target_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        try:
            # 1. Construct System Prompt with Schema
            schema_json = json.dumps(schema.model_json_schema(), indent=2)
            system_prompt = f"""
            You are a precise data generation assistant.
            You MUST return a valid JSON object that strictly adheres to the schema below.
            Do not output markdown blocks (```json). Just the raw JSON.
            
            SCHEMA:
            {schema_json}
            """

            # 2. Call LLM
            response = self.client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1, # Low temp for structure
                response_format={"type": "json_object"}
            )
            
            # 3. Parse & Validate
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")
                
            data = json.loads(content)
            return schema.model_validate(data)

        except Exception as e:
            logger.error(f"Structured Generation Failed: {e}")
            raise e

# Legacy function support if needed elsewhere
def generate_structured_json(prompt: str) -> Dict[str, Any]:
    svc = StructuredLLMService()
    # This is a bit loose since we don't have a schema, but it matches old behavior
    class GenericDict(BaseModel):
        data: Dict[str, Any]
    
    # We simply ask for JSON object
    try:
        response = svc.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        if not response.choices:
            raise ValueError("No choices returned from LLM")
        
        choice = response.choices[0]
        if not choice.message or not choice.message.content:
            raise ValueError("Empty response content from LLM")
            
        return json.loads(choice.message.content)
    except Exception as e:
        logger.error(f"Legacy call failed: {e}")
        raise e
