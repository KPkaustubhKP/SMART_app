# Smart Agriculture IoT Monitoring System

A comprehensive full-stack web application for real-time agriculture monitoring with IoT sensors, irrigation control, and weather integration.

## Features

### Frontend Dashboard
- **Real-time Sensor Monitoring**: Live updates of soil moisture, temperature, pH, NPK levels, and more
- **Weather Integration**: Current weather data and severe weather alerts
- **Irrigation Control**: Manual irrigation system control with duration settings
- **Historical Data**: Interactive charts showing sensor trends over time
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Dark/Light Themes**: Toggle between modern dark and light themes
- **PWA Support**: Install as a native-like app on mobile and desktop
- **Real-time Updates**: WebSocket connection for live data updates

### Backend API
- **FastAPI Framework**: High-performance async API with automatic documentation
- **Real-time Data**: WebSocket endpoints for live sensor data streaming
- **Weather Service**: Integration with OpenWeatherMap API for weather data and alerts
- **Database Management**: SQLite for development, PostgreSQL-ready for production
- **Comprehensive Logging**: Detailed system logging and error handling
- **Health Monitoring**: System health checks and monitoring endpoints

### Sensor Data Simulation
- Realistic sensor value generation with natural variations
- Time-based patterns (day/night cycles, seasonal changes)
- Alert system for threshold violations
- Historical data storage and retrieval

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation and serialization
- **SQLite/PostgreSQL** - Database storage
- **aiohttp** - Async HTTP client for weather API
- **WebSockets** - Real-time communication

### Frontend
- **React 18** - Modern React with hooks
- **TailwindCSS** - Utility-first CSS framework
- **Chart.js** - Interactive data visualization
- **Lucide React** - Modern icon library
- **Axios** - HTTP client for API calls

### Deployment
- **Docker** - Containerized deployment
- **Render** - Cloud platform deployment
- **Nginx** - Production web server
- **PWA** - Progressive Web App capabilities

## Quick Start

### Prerequisites
- Node.js 18+ 
- Python 3.11+
- Docker (optional)

### Local Development

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your OpenWeatherMap API key
python -m app.main
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

### Docker Development
```bash
# Copy environment file
cp backend/.env.example backend/.env
# Edit backend/.env with your settings

# Start all services
docker-compose up --build
```

Access the application:
- Frontend: http://localhost:80
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Deployment

### Deploy to Render (Recommended)

1. **Prepare Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/agri-monitor-app.git
   git push -u origin main
   ```

2. **Deploy Backend**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the backend directory
   - Use the following settings:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python -m app.main`
     - **Environment Variables**:
       - `PORT`: `8000`
       - `OPENWEATHER_API_KEY`: Your API key
       - `FARM_LATITUDE`: Your farm latitude
       - `FARM_LONGITUDE`: Your farm longitude

3. **Deploy Frontend**
   - Click "New +" → "Static Site"
   - Connect the same repository
   - Select the frontend directory
   - Use the following settings:
     - **Build Command**: `npm install && npm run build`
     - **Publish Directory**: `build`
     - **Environment Variables**:
       - `REACT_APP_API_URL`: Your backend URL

4. **Optional: Use render.yaml**
   - Place `render.yaml` in your repository root
   - Render will automatically deploy both services

### Deploy with Docker

#### Production Docker Setup
```bash
# Build images
docker build -t agri-backend ./backend
docker build -t agri-frontend ./frontend

# Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

## Configuration

### Environment Variables

#### Backend (.env)
```env
# Server
PORT=8000
HOST=0.0.0.0

# Database
DATABASE_PATH=agriculture_monitor.db

# Weather API
OPENWEATHER_API_KEY=your_api_key_here
FARM_LATITUDE=40.7128
FARM_LONGITUDE=-74.0060

# Security
CORS_ORIGINS=http://localhost:3000,https://your-domain.com
SECRET_KEY=your-secret-key
```

#### Frontend
```env
REACT_APP_API_URL=http://localhost:8000
```

### OpenWeatherMap API Setup

1. Sign up at [OpenWeatherMap](https://openweathermap.org/)
2. Go to API Keys section
3. Generate a free API key
4. Add to your backend .env file

## API Documentation

Once the backend is running, visit:
- Interactive API docs: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`

### Key Endpoints

#### Sensor Data
- `GET /api/sensors/current` - Current sensor readings
- `GET /api/sensors/historical` - Historical sensor data
- `WebSocket /ws/sensors` - Real-time sensor data stream

#### Irrigation Control
- `GET /api/irrigation/status` - Current irrigation status
- `POST /api/irrigation/control` - Control irrigation system

#### Weather
- `GET /api/weather/current` - Current weather data
- `GET /api/weather/alerts` - Active weather alerts
- `GET /api/weather/forecast` - Weather forecast

#### System
- `GET /health` - System health check
- `GET /api/system/status` - Comprehensive system status

## Features in Detail

### Real-time Dashboard
- Live sensor data updates every 30 seconds
- Interactive charts showing trends
- Threshold-based alert system
- Weather conditions and warnings
- Irrigation system status and controls

### PWA Capabilities
- Install on mobile home screen
- Offline functionality for cached data
- Background sync when connection restored
- Native app-like experience

### Responsive Design
- Mobile-first design approach
- Touch-friendly controls
- Optimized for tablets and phones
- Consistent experience across devices

### Security Features
- CORS configuration
- Environment-based configuration
- Input validation and sanitization
- Rate limiting ready

## Monitoring and Maintenance

### Health Checks
- Backend health endpoint: `/health`
- Database connectivity monitoring
- Service status monitoring
- Automatic error recovery

### Logging
- Comprehensive application logging
- Error tracking and reporting
- Performance monitoring
- System event logging

### Data Management
- Automatic old data cleanup
- Database size monitoring
- Backup recommendations
- Data export capabilities

## Customization

### Adding New Sensors
1. Update `SensorType` enum in `models.py`
2. Modify sensor simulation in `sensors.py`
3. Add database schema updates
4. Update frontend dashboard components

### Custom Alerts
1. Define alert conditions in `sensors.py`
2. Update alert checking logic
3. Add frontend notification handling
4. Configure alert thresholds

### Theme Customization
1. Modify `tailwind.config.js`
2. Update CSS custom properties
3. Adjust component styling
4. Test both light/dark themes

## Troubleshooting

### Common Issues

1. **Backend not starting**
   - Check Python version (3.11+ required)
   - Verify all dependencies installed
   - Check environment variables
   - Review logs for specific errors

2. **Frontend build failures**
   - Ensure Node.js 18+ installed
   - Clear `node_modules` and `package-lock.json`
   - Run `npm install` again
   - Check for conflicting dependencies

3. **Database issues**
   - Ensure write permissions for database file
   - Check disk space availability
   - Verify database path in configuration
   - Review database logs

4. **API connection issues**
   - Verify backend is running and accessible
   - Check CORS configuration
   - Confirm API URL in frontend configuration
   - Test API endpoints directly

### Debug Mode

Enable debug logging:
```env
# Backend
LOG_LEVEL=DEBUG

# Frontend  
REACT_APP_DEBUG=true
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review common troubleshooting steps

---

Built with ❤️ for modern agriculture monitoring and IoT applications.
