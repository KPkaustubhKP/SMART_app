# Deployment Guide

## 🌐 Render.com Deployment

### Option 1: Manual Deployment (Recommended)

#### Backend Deployment:
1. Go to [render.com/dashboard](https://render.com/dashboard)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `smart-agriculture-backend`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Environment Variables**:
     - `PORT`: `8000`
     - `PYTHONPATH`: `/opt/render/project/src`

#### Frontend Deployment:
1. Click "New +" → "Static Site"
2. Connect same GitHub repository
3. Configure:
   - **Name**: `smart-agriculture-frontend`
   - **Root Directory**: `frontend`
   - **Build Command**: `echo "No build needed"`
   - **Publish Directory**: `public`

### Option 2: Blueprint Deployment

Use the provided `render.yaml` file:
1. Go to Render Dashboard
2. Click "New +" → "Blueprint"
3. Connect your repository
4. Render will deploy both services automatically

## 🐳 Local Development with Docker

```bash
docker-compose up --build
```

Access at:
- Frontend: http://localhost
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🔧 Environment Variables

### Backend:
- `PORT`: Application port (default: 8000)
- `DATABASE_PATH`: SQLite database path
- `PYTHONPATH`: Python import path

### Frontend:
- `REACT_APP_API_URL`: Backend API URL (auto-detected)

## 📋 Troubleshooting

1. **Backend fails to start**: Check Python version (3.11+) and dependencies
2. **Frontend can't connect**: Verify backend URL in browser console
3. **Database errors**: Ensure write permissions for data directory

## 🎯 Expected URLs

After deployment:
- Backend: `https://smart-agriculture-backend.onrender.com`
- Frontend: `https://smart-agriculture-frontend.onrender.com`
