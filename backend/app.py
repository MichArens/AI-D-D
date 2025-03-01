from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from endpoints import generate_character_options, generate_character_icon, start_game, take_action, check_music, get_available_models

app = FastAPI(title="D&D AI Game Backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints
app.post("/api/generate-character-options")(generate_character_options)
app.post("/api/generate-character-icon")(generate_character_icon)
app.post("/api/start-game")(start_game)
app.post("/api/take-action")(take_action)
app.get("/api/check-music")(check_music)
app.get("/api/models")(get_available_models)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
