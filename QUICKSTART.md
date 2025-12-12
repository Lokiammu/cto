# Quick Start Guide

Get the FastAPI backend running in 5 minutes!

## Prerequisites

- Python 3.9+
- MongoDB running locally (or Docker)

## 1. Start MongoDB (if not running)

### Using Docker (Recommended)
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### Using System MongoDB
```bash
# Check if MongoDB is running
sudo systemctl status mongodb

# If not running, start it
sudo systemctl start mongodb
```

## 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env if needed (default settings work for local MongoDB)
# Minimum required: No changes needed for local development!
```

## 4. Seed Database with Sample Data

```bash
python scripts/seed_database.py
```

This creates:
- 2 sample users (email: john@example.com, password: password123)
- 8 sample products
- 3 sample coupons

## 5. Start the Server

```bash
# Option 1: Using the start script
./scripts/start_dev.sh

# Option 2: Using Python directly
python backend/main.py

# Option 3: Using uvicorn
uvicorn backend.main:app --reload
```

## 6. Test the API

Open your browser to:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Quick API Test

### 1. Sign Up a New User

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "username": "demouser",
    "password": "password123"
  }'
```

### 2. Get Products

```bash
curl http://localhost:8000/api/products
```

### 3. Test WebSocket Chat

Open browser console and run:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/test123');
ws.onopen = () => ws.send(JSON.stringify({message: "Hello!"}));
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

## That's It! 🎉

Your FastAPI backend is now running with:
- ✅ REST API endpoints
- ✅ WebSocket chat
- ✅ User authentication
- ✅ Sample data
- ✅ Real-time features
- ✅ Background tasks

## Next Steps

1. **Explore API**: Visit http://localhost:8000/docs
2. **Run Tests**: `pytest`
3. **Read Documentation**: See README.md for full details
4. **Connect Frontend**: Use the API endpoints in your frontend

## Troubleshooting

### MongoDB Connection Error
```bash
# Make sure MongoDB is running
docker ps  # Check if Docker container is running
# OR
sudo systemctl status mongodb
```

### Port 8000 Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or change port in .env file
PORT=8001
```

### Module Not Found Error
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## Sample Credentials

After seeding the database:

**User 1:**
- Email: john@example.com
- Password: password123

**User 2:**
- Email: jane@example.com
- Password: password123

## API Endpoints Overview

- `POST /api/auth/signup` - Create account
- `POST /api/auth/signin` - Login
- `GET /api/auth/me` - Get profile
- `GET /api/products` - List products
- `GET /api/cart` - Get cart
- `POST /api/cart/items` - Add to cart
- `POST /api/orders` - Create order
- `GET /api/loyalty/profile` - Loyalty info
- `WS /ws/chat/{session_id}` - Chat WebSocket

See full documentation at http://localhost:8000/docs
