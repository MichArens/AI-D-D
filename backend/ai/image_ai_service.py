import httpx

SD_BASE_URL = "http://localhost:7860/sdapi/v1"

async def generate_image(prompt: str):
    """Generate image using Stable Diffusion API"""
    try:
        negative_prompt = "poor quality, deformed, blurry, bad anatomy, bad proportions, extra limbs, out of frame, watermark, signature, text"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SD_BASE_URL}/txt2img",
                json={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": 512,
                    "height": 512,
                    "steps": 30,
                    "guidance_scale": 7.5  # Stronger adherence to prompt
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
            return data["images"][0]  # Base64 encoded image
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        return None
