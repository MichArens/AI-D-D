import os

import httpx


SUNO_API_URL = "https://api.suno.ai/v1"
SUNO_API_KEY = os.environ.get("SUNO_API_KEY", "")  # Get from environment variables

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
    
