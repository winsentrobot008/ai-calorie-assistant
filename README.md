# AI Calorie Assistant 🥗

AI-powered food recognition and calorie tracking web application. Snap a photo or describe your meal — the AI estimates nutrition and tracks your daily intake.

## Features

- **AI Food Recognition** — Upload a food photo, AI identifies the dish and estimates calories
- **Text Input** — Describe what you ate, AI parses and calculates nutrition
- **Meal Type Classification** — Tag meals as Breakfast / Lunch / Dinner / Snack
- **Daily Dashboard** — Calorie ring chart with protein/fat/carbs breakdown
- **Trend Analysis** — Weekly and monthly calorie trend charts
- **AI Dietary Suggestions** — Get personalized nutrition advice based on your goals
- **User Profile** — Set daily calorie and macro targets

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite |
| Backend | FastAPI (Async, Python 3.12) |
| Database | SQLite + SQLAlchemy (Async) |
| AI API | Universal AI Proxy (Grok Vision) |

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env .env.local   # Edit .env.local with your API key
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd webapp
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

Open http://localhost:5173 in your browser.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/meals/analyze-image` | Analyze food from image |
| POST | `/api/v1/meals/analyze-text` | Analyze food from text |
| GET | `/api/v1/meals` | List meal records |
| DELETE | `/api/v1/meals/{id}` | Delete meal record |
| GET | `/api/v1/stats/daily` | Daily nutrition summary |
| GET | `/api/v1/stats/weekly` | 7-day calorie trend |
| GET | `/api/v1/stats/monthly` | 30-day calorie trend |
| GET | `/api/v1/stats/suggestions` | AI dietary suggestions |
| POST | `/api/v1/user/register` | Register user |
| GET | `/api/v1/user/profile` | Get user profile |
| PUT | `/api/v1/user/profile` | Update user profile |
| GET | `/health` | Health check |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_API_BASE_URL` | `https://api.lk888.ai/api` | Universal AI API base URL |
| `AI_API_KEY` | - | Universal AI API key (required) |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL for frontend |

## Deployment Guide

### Prerequisites
- Python 3.12+
- Node.js 20+
- FFmpeg (for image processing)

### Option A: Manual Deployment

1. **Start Backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start Frontend**
   ```bash
   cd webapp
   npm install
   npm run dev
   ```

3. **Environment Variable**
   ```bash
   # Frontend (set before starting dev server)
   VITE_API_URL=http://localhost:8000
   ```

### Option B: Docker Deployment

1. **Build the image**
   ```bash
   docker build -t ai-calorie-assistant .
   ```

2. **Run the container**
   ```bash
   docker run -d \
     --name calorie-assistant \
     -p 8000:8000 \
     -e AI_API_KEY=your-key-here \
     ai-calorie-assistant
   ```

3. **Access the app**
   - Backend API: http://localhost:8000
   - Health check: http://localhost:8000/health

### Option C: Docker Compose (Recommended)

Create a `docker-compose.yml`:

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AI_API_KEY=${AI_API_KEY}
      - AI_API_BASE_URL=https://api.lk888.ai/api
      - VITE_API_URL=http://localhost:8000
    volumes:
      - ./storage:/app/storage
```

Then run:
```bash
AI_API_KEY=your-key-here docker compose up -d
```

### Notes
- The SQLite database is stored at `storage/calories.db` — mount this volume for persistence
- Uploaded images are stored in `storage/uploads/`
- For production, replace SQLite with PostgreSQL and add authentication
