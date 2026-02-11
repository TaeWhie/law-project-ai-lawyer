import os
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from dotenv import load_dotenv

load_dotenv()

class LLMFactory:
    _llm_cache = {}
    _embed_cache = {}

    @staticmethod
    def create_llm(model_type: str = "openai", model_name: str = None, temperature: float = 0):
        """
        Create an LLM instance based on the specified type and name.
        Instances are cached by (model_type, model_name, temperature).
        """
        # Default settings if not provided
        if not model_name:
            if model_type == "openai":
                model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-5-nano") # Default to cheaper model
            elif model_type == "ollama":
                model_name = os.getenv("OLLAMA_MODEL_NAME", "llama3")

        cache_key = (model_type, model_name, temperature)
        if cache_key in LLMFactory._llm_cache:
            return LLMFactory._llm_cache[cache_key]

        print(f"[LLMFactory] Initializing {model_type} model: {model_name} (temp={temperature})")

        if model_type == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is not set in environment variables.")
            
            # Apply cost/verbosity optimizations for GPT-5 Nano
            # Apply cost/verbosity optimizations for GPT-5 Nano
            kwargs = {}
            if "gpt-5-nano" in model_name:
                kwargs["verbosity"] = "low"
                # reasoning_effort is likely a model_kwarg or specialized param. 
                # If langchain implementation supports it as a top-level kwarg, we pass it here.
                # If the warning persists, it might need to be in model_kwargs depending on version.
                # However, the previous warning was "Parameters ... should be specified explicitly".
                kwargs["reasoning_effort"] = "low"

            llm = ChatOpenAI(
                model_name=model_name, 
                temperature=temperature, 
                openai_api_key=api_key,
                **kwargs
            )
            
        elif model_type == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            llm = ChatOllama(model=model_name, temperature=temperature, base_url=base_url)
            
        else:
            raise ValueError(f"Unsupported model_type: {model_type}")

        LLMFactory._llm_cache[cache_key] = llm
        return llm

    @staticmethod
    def create_embeddings(model_type: str = "openai", model_name: str = None):
        """
        Create an Embeddings instance. Instances are cached by (model_type, model_name).
        """
        cache_key = (model_type, model_name)
        if cache_key in LLMFactory._embed_cache:
            return LLMFactory._embed_cache[cache_key]

        print(f"[LLMFactory] Initializing {model_type} embeddings: {model_name or 'default'}")
        
        if model_type == "openai":
            from langchain_openai import OpenAIEmbeddings
            api_key = os.getenv("OPENAI_API_KEY")
            embed = OpenAIEmbeddings(openai_api_key=api_key)
            
        elif model_type == "ollama":
            from langchain_community.embeddings import OllamaEmbeddings
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            # Default to a good embedding model if not specified
            model_name = model_name or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
            embed = OllamaEmbeddings(model=model_name, base_url=base_url)
            
        else:
            raise ValueError(f"Unsupported embedding model_type: {model_type}")

        LLMFactory._embed_cache[cache_key] = embed
        return embed

# Example Usage:
# llm = LLMFactory.create_llm("openai", "gpt-4o-mini")
# llm_local = LLMFactory.create_llm("ollama", "llama3")
