import httpx
import os
from fastapi import HTTPException

OLLAMA_BASE_URL = "http://localhost:11434/api"
SD_BASE_URL = "http://localhost:7860/sdapi/v1"
SUNO_API_URL = "https://api.suno.ai/v1"
SUNO_API_KEY = os.environ.get("SUNO_API_KEY", "")  # Get from environment variables

async def generate_text(prompt: str, model: str = "llama3"):
    """Generate text using Ollama API"""
    try:
        # Add a formatting reminder for chapter titles
        if "NEXT CHAPTER:" in prompt:
            prompt += "\n\nNote: The NEXT CHAPTER title should be brief (3-7 words) and on its own line."
            
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
            return response.json()["response"]
    except Exception as e:
        print(f"Error generating text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Text generation failed: {str(e)}")

async def generate_image(prompt: str):
    """Generate image using Stable Diffusion API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SD_BASE_URL}/txt2img",
                json={
                    "prompt": f"fantasy art, dungeons and dragons style, detailed, {prompt}",
                    "negative_prompt": "nsfw, poor quality, deformed",
                    "width": 512,
                    "height": 512,
                    "steps": 30
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
            return data["images"][0]  # Base64 encoded image
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        return None

async def generate_music(prompt: str):
    """Generate background music using Suno AI API"""
    if not SUNO_API_KEY:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {SUNO_API_KEY}",
                "Content-Type": "application/json"
            }
            response = await client.post(
                f"{SUNO_API_URL}/generate",
                headers=headers,
                json={
                    "prompt": f"Fantasy adventure music for a D&D game: {prompt}",
                    "duration": 120  # 2 minutes
                },
                timeout=180.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("url")
    except Exception as e:
        print(f"Error generating music: {str(e)}")
        return None
