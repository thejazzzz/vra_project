#File: services/llm_factory.py
import os
import logging
from typing import Optional, Dict, Any, Union
from openai import OpenAI, AzureOpenAI

logger = logging.getLogger(__name__)

class LLMProvider:
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    AZURE = "azure"
    LOCAL = "local"
    GOOGLE = "google"

class LLMFactory:
    """
    Factory class to create and manage LLM clients.
    Supports hot-swapping providers and models.
    """
    
    _instances: Dict[Any, Union[OpenAI, AzureOpenAI]] = {}

    @staticmethod
    def get_client(provider: str = LLMProvider.OPENAI, **kwargs) -> Union[OpenAI, AzureOpenAI]:
        """
        Get or create a client for the specified provider.
        """
        api_key = kwargs.get("api_key")
        base_url = kwargs.get("base_url")
        api_version = kwargs.get("api_version")
        azure_endpoint = kwargs.get("azure_endpoint")
        timeout = kwargs.get("timeout", 45.0)
        max_retries = kwargs.get("max_retries", 2)

        # 1. Resolve Provider Defaults if not explicitly passed
        if provider == LLMProvider.OPENROUTER:
            api_key = api_key or os.getenv("OPENROUTER_API_KEY")
            base_url = base_url or "https://openrouter.ai/api/v1"
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not set")
                
        elif provider == LLMProvider.OPENAI:
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")

        elif provider == LLMProvider.LOCAL:
            base_url = base_url or os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
            api_key = "ollama" # Dummy key for Ollama
            
        elif provider == LLMProvider.AZURE:
            api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
            azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
            api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
            if not api_key or not azure_endpoint:
                raise ValueError("AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT must be set")
                
        elif provider == LLMProvider.GOOGLE:
            api_key = api_key or os.getenv("GOOGLE_API_KEY")
            base_url = base_url or "https://generativelanguage.googleapis.com/v1beta/openai/"
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not set")

        # 2. Config-Aware Caching
        # Create a cache key based on the effective configuration
        # Normalizing None to empty string or default for consistent invalidation
        cache_key = (
            provider, 
            api_key if api_key else "", 
            base_url if base_url else "",
            azure_endpoint if azure_endpoint else "",
            api_version if api_version else "",
            float(timeout), 
            int(max_retries)
        )
        
        if cache_key in LLMFactory._instances:
            return LLMFactory._instances[cache_key]

        # 3. Create new instance
        logger.info(f"Initializing LLM Client for provider: {provider} (Config Key: {hash(cache_key)})")
        
        try:
            client = None
            if provider == LLMProvider.AZURE:
                client = AzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=azure_endpoint,
                    api_version=api_version,
                    timeout=timeout,
                    max_retries=max_retries
                )
            else:
                # Standard OpenAI compatible client
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    timeout=timeout,
                    max_retries=max_retries
                )
            
            LLMFactory._instances[cache_key] = client # Store with config key
            return client
        except Exception as e:
            logger.error(f"Failed to initialize {provider} client: {e}")
            raise

    @staticmethod
    def get_default_model(provider: str) -> str:
        # Safety check: if provider is missing its API Key, fallback to a safe one
        if provider == LLMProvider.GOOGLE and not os.getenv("GOOGLE_API_KEY"):
            logger.warning("GOOGLE_API_KEY not found. Falling back to OPENAI.")
            provider = LLMProvider.OPENAI
        elif provider == LLMProvider.OPENROUTER and not os.getenv("OPENROUTER_API_KEY"):
            logger.warning("OPENROUTER_API_KEY not found. Falling back to OPENAI.")
            provider = LLMProvider.OPENAI
        elif provider == LLMProvider.OPENAI and not os.getenv("OPENAI_API_KEY"):
            # If even OpenAI is missing, we have a bigger problem, but we'll try to resolve anyway
            logger.error("OPENAI_API_KEY not found either!")

        model = "gpt-3.5-turbo"
        if provider == LLMProvider.OPENROUTER:
            model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash:free")
        elif provider == LLMProvider.OPENAI:
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        elif provider == LLMProvider.LOCAL:
            model = os.getenv("LOCAL_MODEL", "llama3")
        elif provider == LLMProvider.AZURE:
            model = os.getenv("AZURE_DEPLOYMENT_NAME", "azure-gpt-4")
        elif provider == LLMProvider.GOOGLE:
            model = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
            
        print(f"LLM resolved -> provider={provider}, model={model}")
        return model
