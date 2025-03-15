from typing import List
from pydantic import BaseModel
from ai.text_ai_service import OLLAMA_BASE_URL

class GetAvailableModelsResponse(BaseModel):
    models: List[str]
    
async def get_available_models():
    """Get available models from Ollama"""

    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/tags", timeout=10.0)
            response.raise_for_status()
            models = response.json().get("models", [])
            return GetAvailableModelsResponse(models=[model["name"] for model in models])
    except Exception as e:
        # Return a default list if Ollama isn't available
        return GetAvailableModelsResponse(models=["llama3", "mistral", "wizard-mega"])