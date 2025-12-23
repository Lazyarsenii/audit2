# 🚀 Quick Start Guide

## Local Development

### 1. Start Everything
```bash
chmod +x start-all.sh
./start-all.sh
```

This will start:
- Backend on http://localhost:8000
- Frontend on http://localhost:3000
- API docs on http://localhost:8000/docs

**Note:** Local dev has authentication DISABLED by default.

### 2. Test Authentication (Optional)

Enable auth in `backend/.env`:
```bash
API_KEY_REQUIRED=true
API_KEYS=repoaudit
```

Then test:
```bash
chmod +x test-auth.sh
./test-auth.sh
```

## Deployment

### 1. Deploy Backend to Railway
```bash
chmod +x deploy-railway.sh
./deploy-railway.sh
```

Variables set automatically:
- `API_KEY_REQUIRED=true`
- `API_KEYS=repoaudit`

### 2. Deploy Frontend to Vercel
```bash
chmod +x deploy-vercel.sh
./deploy-vercel.sh
```

### 3. Connect Frontend to Backend

In Vercel dashboard, set:
```
NEXT_PUBLIC_API_URL=https://your-railway-app.railway.app
```

In Railway dashboard, update:
```
CORS_ORIGINS=["https://your-vercel-app.vercel.app","http://localhost:3000"]
```

## Using Authentication

### In the UI
1. Open http://localhost:3000
2. Go to Settings → Integrations
3. Enter API key: `repoaudit`
4. Save

### In API calls
```bash
curl -H "X-API-Key: repoaudit" http://localhost:8000/api/v1/analyses
```

## Available Scripts

| Script | Purpose |
|--------|---------|
| `start-all.sh` | Start both backend and frontend |
| `start-backend.sh` | Start only backend |
| `start-frontend.sh` | Start only frontend |
| `test-auth.sh` | Test API key authentication |
| `deploy-railway.sh` | Deploy backend to Railway |
| `deploy-vercel.sh` | Deploy frontend to Vercel |

## Stopping Services

```bash
pkill -f "uvicorn app.main:app"
pkill -f "next dev"
```

## Logs

```bash
# Backend logs
tail -f /tmp/backend.log

# Frontend logs
tail -f /tmp/frontend.log
```

## Authentication Setup

### Backend (.env)
```bash
API_KEY_REQUIRED=true
API_KEYS=repoaudit
```

### Frontend (Settings UI)
- Key stored in localStorage
- Auto-attached to all API requests
- Can be cleared in Settings

### Railway (.env.railway)
```bash
API_KEY_REQUIRED=true
API_KEYS=repoaudit
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=["https://your-vercel-app.vercel.app"]
```
