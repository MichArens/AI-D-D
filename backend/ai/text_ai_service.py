import logging

from fastapi import HTTPException
import httpx
from utilities.prompt_constants import PromptConstants

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434/api"

async def generate_text(prompt: str, model: str = "llama3")-> str:
    """Generate text using Ollama API"""
    try:
        # Add formatting reminders to help with parsing
        if PromptConstants.ACTIONS in prompt or "action choices" in prompt:
            prompt += f"\n\nIMPORTANT FORMATTING INSTRUCTIONS:\n" \
                     f"- Always start your response with '{PromptConstants.STORY}'\n" \
                     f"- Then add '{PromptConstants.ACTIONS}' on a new line before listing the actions\n" \
                     "- Number each action with a digit followed by a period (1., 2., etc.)"
                     
        # Add a formatting reminder for chapter titles
        if PromptConstants.NEXT_CHAPTER in prompt:
            prompt += "\n\nNote: The NEXT CHAPTER title should be brief (3-7 words) and on its own line."
        
        logger.info(f"Sending prompt to model {model} (first 100 chars): {prompt[:100]}...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()["response"]
            logger.info(f"Response received (length: {len(result)})")
            return result
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Text generation failed: {str(e)}")
