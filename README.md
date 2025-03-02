# D&D AI Adventure

An AI-powered Dungeons & Dragons adventure game with a React frontend and FastAPI backend.

## Prerequisites

- Node.js (v14 or higher)
- Python (v3.8 or higher)
- npm or yarn
- pip

## Installation

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd /Users/michaelarens/Documents/projects/dnd5/backend
   ```

2. Create a Python virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. Install dependencies:
   ```bash
   pip install fastapi uvicorn python-dotenv
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd /Users/michaelarens/Documents/projects/dnd5/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Running the Project

### Start the Backend

1. Run the FastAPI server:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```
   
   Alternatively, you can use uvicorn directly:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

3. The API will be available at http://localhost:8000

### Start the Frontend

1. Navigate to the frontend directory
2. Run the development server:
   ```bash
   cd frontend
   npm i
   npm start
   ```

3. The application will open in your browser at http://localhost:3000

## API Endpoints

- `/api/generate-character-options`: Generate character creation options
- `/api/generate-character-icon`: Generate character icon
- `/api/start-game`: Start a new game session
- `/api/take-action`: Submit player actions
- `/api/start-new-chapter`: Start a new game chapter
- `/api/check-music`: Check music status
- `/api/models`: Get available AI models

## Project Structure

```
/dnd5
├── backend/
│   ├── app.py           # Main FastAPI application
│   ├── endpoints.py       # API endpoint functions
├── frontend/
│   ├── public/          # Public assets
│   ├── src/             # React source code
│   ├── package.json     # Frontend dependencies
├── README.md            # This file
```
