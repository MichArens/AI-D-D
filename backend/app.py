from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import endpoints
from models import ActionRequest
from endpoints import (
    generate_character_options, 
    generate_character_icon, 
    start_game, 
    take_action, 
    check_music, 
    get_available_models, 
    start_new_chapter,
    generate_tts_endpoint,
    TTSRequest
)

app = FastAPI(title="D&D AI Game Backend")

# Add global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Configure CORS with more specific settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins like "http://localhost:3000"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Register endpoints with logger
@app.post("/api/generate-character-options")
async def wrapped_generate_character_options():
    logger.info("Received request for character options")
    try:
        result = await generate_character_options()
        logger.info(f"Returning character options: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in generate_character_options: {e}")
        logger.error(traceback.format_exc())
        raise

@app.post("/api/take-action")
async def wrapped_take_action(request: ActionRequest):
    logger.info("Received action request")
    try:
        # Log the request details for debugging
        if hasattr(request, 'customAction') and request.customAction:
            logger.info(f"Custom action: {request.customAction[:100]}...")
        else:
            logger.info(f"Action choice ID: {request.choiceId}")
        
        result = await take_action(request)
        
        # Log success
        logger.info(f"Action processed successfully, returned {len(result.get('choices', []))} choices")
        return result
    except Exception as e:
        logger.error(f"Error in take_action: {e}")
        logger.error(traceback.format_exc())
        raise

# Register other endpoints
app.post("/api/generate-character-icon")(generate_character_icon)
app.post("/api/start-game")(start_game)
app.post("/api/take-action")(take_action)
app.post("/api/start-new-chapter")(start_new_chapter)
app.get("/api/check-music")(check_music)
app.get("/api/models")(get_available_models)

# Register the new TTS endpoint
app.post("/api/generate-tts")(generate_tts_endpoint)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
