import httpx

SD_BASE_URL = "http://localhost:7860/sdapi/v1"

async def generate_image(prompt: str):
    """Generate image using Stable Diffusion API"""
    try:
        # Different handling based on type of chapter transition
        is_chapter_transition = "→" in prompt or "transition" in prompt.lower()
        is_fresh_start = "new adventure" in prompt.lower() or "establishing shot" in prompt.lower()
        
        # Enhance prompt with appropriate styling
        if is_fresh_start:
            # For fresh start chapters, emphasize new beginnings
            enhanced_prompt = f"fantasy art, dungeons and dragons style, establishing shot, new adventure beginning, fresh start, {prompt}"
            enhanced_prompt += ", vibrant colors, wide landscape view, new horizon, detailed environment, adventure awaits"
        elif is_chapter_transition:
            # For chapter continuations, emphasize the continuity 
            enhanced_prompt = f"fantasy art, dungeons and dragons style, detailed, story transition, narrative continuity, same characters in new situation, {prompt}"
            enhanced_prompt += ", detailed background, dramatic lighting, seamless storytelling, character consistency"
        else:
            # For regular scenes
            enhanced_prompt = f"fantasy art, dungeons and dragons style, detailed, dynamic scene, action shot, {prompt}"
            enhanced_prompt += ", vibrant lighting, dramatic composition, high quality, highly detailed"
        
        # Add negative prompt to avoid common issues
        negative_prompt = "poor quality, deformed, blurry, bad anatomy, bad proportions, extra limbs, out of frame, watermark, signature, text"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SD_BASE_URL}/txt2img",
                json={
                    "prompt": enhanced_prompt,
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
