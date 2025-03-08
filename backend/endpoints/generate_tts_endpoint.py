import logging
import traceback
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from ai.tts_ai_service import generate_tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GenerateTTSRequest(BaseModel):
    text: str
    voice: str = "bm_george"  # Default voice

class GenerateTTSResponse(BaseModel):
    audioData: Optional[str] = None  # Base64 encoded audio
    
async def generate_tts_endpoint(request: GenerateTTSRequest):
    """Generate text-to-speech audio"""
    try:
        logger.info(f"Generating TTS for text of length: {len(request.text)}")
        audio_data = await generate_tts(request.text, "bm_george")
        return GenerateTTSResponse(audioData=audio_data)
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate TTS: {str(e)}")