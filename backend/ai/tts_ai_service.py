# Configure logging
import base64
import io
import logging
from typing import Optional
from fastapi import HTTPException
from kokoro import KPipeline
import numpy as np
from scipy.io import wavfile

logger = logging.getLogger(__name__)

# Initialize Kokoro TTS pipeline once at module level
logger.info("Initializing Kokoro TTS pipeline...")
try:
    KOKORO_PIPELINE = KPipeline(lang_code='b')  # 'b' for English
    logger.info("Kokoro TTS pipeline initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Kokoro TTS pipeline: {e}")
    KOKORO_PIPELINE = None

async def generate_tts(text: str, voice='bm_george')-> Optional[str]:
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
        sentences = _split_into_sentences(text)
        
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

def _split_into_sentences(text):
    """
    Split text into sentences for better TTS processing
    """
    import re
    # Split on sentence ending punctuation followed by spaces or end of string
    sentences = re.split(r'(?<=[.!?])\s+|(?<=[.!?])$', text)
    return [s for s in sentences if s.strip()]