# Smart Agriculture IoT Monitoring System

A comprehensive full-stack application for real-time agricultural monitoring with sensor data visualization, irrigation control, and weather integration.

## 🌱 Features

- **Real-time Sensor Monitoring**: Track soil moisture, temperature, pH, conductivity, and NPK levels
- **Weather Integration**: Current weather conditions and forecasts
- **Irrigation Control**: Manual irrigation system activation with status monitoring
- **Alert System**: Real-time notifications for abnormal sensor readings
- **Responsive Dashboard**: Modern web interface built with React and Tailwind CSS
- **RESTful API**: FastAPI backend with automatic documentation
- **Database Storage**: SQLite for data persistence
- **Docker Support**: Containerized deployment ready

## 🚀 Quick Start

### Using Docker Compose

1. **Start the application**:
   ```bash
   docker-compose up --build
   ```

2. **Access the application**:
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Manual Setup

#### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

#### Frontend Setup

The frontend is a single HTML file with embedded React. Simply serve the `frontend/public/index.html` file using any web server:

```bash
cd frontend/public
python -m http.server 3000
```

## 🌐 Deployment

### Render.com

1. **Backend**: Deploy as Web Service using `backend/` directory
2. **Frontend**: Deploy as Static Site using `frontend/` directory

See deployment-guide.md for detailed instructions.

## 📊 API Endpoints

- `GET /` - API information and health
- `GET /health` - Health check
- `GET /api/sensors/current` - Current sensor readings
- `GET /api/irrigation/status` - Irrigation system status
- `POST /api/irrigation/control` - Control irrigation system
- `GET /api/weather/current` - Current weather data
- `GET /api/alerts` - System alerts

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **Frontend**: React 18, Tailwind CSS
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Deployment**: Docker, Render.com

## 📄 License

This project is licensed under the MIT License.

Built with ❤️ for smart agriculture and sustainable farming.
