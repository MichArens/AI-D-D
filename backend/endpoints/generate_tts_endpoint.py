import logging
import traceback

from fastapi import HTTPException
from ai.tts_ai_service import generate_tts
from models import TTSRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_tts_endpoint(request: TTSRequest):
    """Generate text-to-speech audio"""
    try:
        logger.info(f"Generating TTS for text of length: {len(request.text)}")
        audio_data = await generate_tts(request.text, "bm_george")
        return {"audioData": audio_data}
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate TTS: {str(e)}")