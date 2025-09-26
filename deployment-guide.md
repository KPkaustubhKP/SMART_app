# Smart Agriculture Monitoring System - Quick Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying your Smart Agriculture IoT Monitoring System to Render, the recommended cloud platform.

## Prerequisites
- GitHub account
- Render account (free tier available)
- OpenWeatherMap API key (free)

## Step 1: Get OpenWeatherMap API Key

1. Visit [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up for a free account
3. Go to "API Keys" section
4. Generate and copy your API key
5. Keep this key for Step 4

## Step 2: Prepare Your Repository

1. Extract the `smart-agriculture-monitoring-app.zip` file
2. Initialize a Git repository:
   ```bash
   cd agri-monitor-app
   git init
   git add .
   git commit -m "Initial commit: Smart Agriculture Monitoring System"
   ```

3. Create a GitHub repository:
   - Go to GitHub and create a new repository
   - Name it `smart-agriculture-monitor` or similar
   - Don't initialize with README (we already have one)

4. Push your code:
   ```bash
   git remote add origin https://github.com/yourusername/smart-agriculture-monitor.git
   git branch -M main
   git push -u origin main
   ```

## Step 3: Deploy Backend to Render

1. **Login to Render**
   - Go to [render.com](https://render.com)
   - Sign up or login with GitHub

2. **Create Web Service**
   - Click "New +" → "Web Service"
   - Select "Build and deploy from a Git repository"
   - Connect your GitHub repository
   - Click "Connect" next to your repository

3. **Configure Backend Service**
   - **Name**: `agri-monitor-backend`
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m app.main`

4. **Add Environment Variables**
   Click "Advanced" and add these environment variables:
   ```
   PORT = 8000
   HOST = 0.0.0.0
   DATABASE_PATH = ./agriculture_monitor.db
   OPENWEATHER_API_KEY = your_api_key_here
   FARM_LATITUDE = 40.7128
   FARM_LONGITUDE = -74.0060
   CORS_ORIGINS = *
   LOG_LEVEL = INFO
   ```

5. **Deploy**
   - Select "Free" plan
   - Click "Create Web Service"
   - Wait for deployment to complete (5-10 minutes)
   - Note your backend URL (e.g., `https://agri-monitor-backend.onrender.com`)

## Step 4: Deploy Frontend to Render

1. **Create Static Site**
   - Click "New +" → "Static Site"
   - Connect the same GitHub repository
   - Click "Connect"

2. **Configure Frontend Service**
   - **Name**: `agri-monitor-frontend`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `build`

3. **Add Environment Variables**
   ```
   REACT_APP_API_URL = https://your-backend-url.onrender.com
   ```
   Replace with your actual backend URL from Step 3

4. **Deploy**
   - Click "Create Static Site"
   - Wait for build and deployment (5-10 minutes)

## Step 5: Test Your Application

1. **Access Your App**
   - Visit your frontend URL (e.g., `https://agri-monitor-frontend.onrender.com`)
   - You should see the dashboard loading

2. **Verify Features**
   - Check real-time sensor data updates
   - Test theme toggle (dark/light mode)
   - Try manual irrigation control
   - View weather data and alerts
   - Test mobile responsiveness

3. **API Documentation**
   - Visit `https://your-backend-url.onrender.com/docs`
   - Explore the interactive API documentation

## Step 6: Optional Enhancements

### Custom Domain
1. Go to your Render service settings
2. Add custom domain
3. Configure DNS records as instructed

### Database Upgrade
For production use, consider upgrading to PostgreSQL:
1. Add PostgreSQL database in Render
2. Update environment variables
3. Modify database connection in code

### Monitoring
- Enable Render monitoring in service settings
- Set up health check endpoints
- Configure log aggregation

## Troubleshooting

### Backend Issues
- Check deployment logs in Render dashboard
- Verify environment variables are set correctly
- Ensure API key is valid and has usage quota

### Frontend Issues
- Check build logs for errors
- Verify REACT_APP_API_URL points to correct backend
- Test API endpoints directly

### API Connection Issues
- Check CORS configuration
- Verify backend is deployed and running
- Test API health endpoint: `/health`

### Performance Issues
- Render free tier has limitations
- Consider upgrading to paid plan for production
- Optimize database queries if needed

## Support and Resources

- **Render Documentation**: [render.com/docs](https://render.com/docs)
- **FastAPI Documentation**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **React Documentation**: [react.dev](https://react.dev)
- **TailwindCSS**: [tailwindcss.com](https://tailwindcss.com)

## Security Considerations

For production deployment:
1. Use environment-specific CORS origins (not `*`)
2. Implement proper authentication
3. Use HTTPS for all communications
4. Set up proper error handling
5. Configure rate limiting
6. Regular security updates

---

🎉 **Congratulations!** Your Smart Agriculture Monitoring System is now deployed and ready to use!

The system provides:
- Real-time IoT sensor monitoring
- Manual irrigation controls
- Weather integration with alerts
- Historical data visualization
- Mobile-responsive PWA
- Professional dashboard interface

Perfect for modern agriculture, greenhouses, and IoT monitoring applications!