import httpx
import os
import base64
from fastapi import HTTPException
from kokoro import KPipeline
import io
import numpy as np
from scipy.io import wavfile
import logging

# Configure logging
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434/api"
SD_BASE_URL = "http://localhost:7860/sdapi/v1"
SUNO_API_URL = "https://api.suno.ai/v1"
SUNO_API_KEY = os.environ.get("SUNO_API_KEY", "")  # Get from environment variables

# Initialize Kokoro TTS pipeline once at module level
logger.info("Initializing Kokoro TTS pipeline...")
try:
    KOKORO_PIPELINE = KPipeline(lang_code='b')  # 'b' for English
    logger.info("Kokoro TTS pipeline initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Kokoro TTS pipeline: {e}")
    KOKORO_PIPELINE = None

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
    

async def generate_tts(text: str, voice='bm_george'):
    """
    Generate text-to-speech audio using Kokoro
    Returns base64-encoded MP3 audio data
    """
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
        
    # Check if the pipeline was initialized successfully
    if KOKORO_PIPELINE is None:
        logger.error("Kokoro TTS pipeline is not available")
        raise HTTPException(status_code=500, detail="TTS service is not available")
    
    try:
        # Use the global pipeline instead of creating a new one
        pipeline = KOKORO_PIPELINE
        
        # Process the text in sentences for better quality
        audios = []
        sample_rate = 24000  # Kokoro default
        
        # Clean and split text into sentences for better processing
        sentences = split_into_sentences(text)
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Generate audio for this sentence
            generator = pipeline(
                sentence, 
                voice=voice,  # Voice option
                speed=1.0,    # Normal speed
                split_pattern=None  # Don't split further
            )
            
            # Collect audio from the generator
            for _, _, audio in generator:
                # Convert PyTorch tensor to numpy array
                audio_np = audio.numpy()
                audios.append(audio_np)
        
        # Concatenate all audio segments
        if audios:
            full_audio = np.concatenate(audios)
            
            # Convert to WAV format using scipy
            output_buffer = io.BytesIO()
            wavfile.write(output_buffer, sample_rate, full_audio)
            
            # Convert to base64 for transmission
            output_buffer.seek(0)
            audio_base64 = base64.b64encode(output_buffer.read()).decode('utf-8')
            
            return audio_base64
        else:
            raise HTTPException(status_code=500, detail="Failed to generate audio")
            
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

def split_into_sentences(text):
    """
    Split text into sentences for better TTS processing
    """
    import re
    # Split on sentence ending punctuation followed by spaces or end of string
    sentences = re.split(r'(?<=[.!?])\s+|(?<=[.!?])$', text)
    return [s for s in sentences if s.strip()]

