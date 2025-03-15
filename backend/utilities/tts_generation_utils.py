import logging
from ai.tts_ai_service import generate_tts


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def maybe_generate_tts(text: str, enable_tts=False):
    """Generate TTS for text if enabled"""
    if not enable_tts or not text:
        return None
    
    try:
        logger.info(f"Pre-generating TTS for text of length {len(text)}")
        audio_data = await generate_tts(text, "bm_george")
        return audio_data
    except Exception as e:
        logger.error(f"Failed to generate TTS: {e}")
        return None