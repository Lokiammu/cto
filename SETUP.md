# Setup Instructions

## Prerequisites

Before running the application, ensure you have the following installed:

1. **Python 3.9 or higher**
   ```bash
   python --version
   ```

2. **MongoDB 4.4 or higher**
   ```bash
   # Install MongoDB (Ubuntu/Debian)
   sudo apt-get install mongodb
   
   # Or use Docker
   docker run -d -p 27017:27017 --name mongodb mongo:latest
   ```

3. **Redis (optional, for caching)**
   ```bash
   # Install Redis (Ubuntu/Debian)
   sudo apt-get install redis-server
   
   # Or use Docker
   docker run -d -p 6379:6379 --name redis redis:latest
   ```

## Installation Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd <repository-name>
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` file with your configuration:
- Set `MONGODB_URL` to your MongoDB connection string
- Set `JWT_SECRET_KEY` to a secure random string
- Set `OPENAI_API_KEY` if using LangChain/LangGraph features
- Update `CORS_ORIGINS` for your frontend URLs

### 5. Verify MongoDB Connection
```bash
# Start MongoDB if not running
sudo systemctl start mongodb

# Check MongoDB status
sudo systemctl status mongodb
```

### 6. Seed Database (Optional)
```bash
python scripts/seed_database.py
```

This will create:
- Sample users (john@example.com, jane@example.com - password: password123)
- Sample products (8 products across various categories)
- Sample coupons

## Running the Application

### Development Mode
```bash
# Option 1: Using the start script
./scripts/start_dev.sh

# Option 2: Using uvicorn directly
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Option 3: Using Python module
python backend/main.py
```

The server will start at `http://localhost:8000`

### Production Mode
```bash
# Using uvicorn with multiple workers
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or using gunicorn with uvicorn workers
gunicorn backend.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Accessing the Application

Once running, you can access:

- **API Root**: http://localhost:8000/
- **Swagger UI (Interactive API docs)**: http://localhost:8000/docs
- **ReDoc (Alternative API docs)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Testing

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=backend --cov-report=html
# Open htmlcov/index.html in browser
```

### Run Specific Tests
```bash
# Test auth endpoints
pytest backend/tests/test_auth.py

# Test products
pytest backend/tests/test_products.py

# Test with verbose output
pytest -v

# Test with print statements
pytest -s
```

## Quick API Test

### 1. Create a User (Signup)
```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "securepassword123",
    "full_name": "Test User"
  }'
```

### 2. Sign In
```bash
curl -X POST http://localhost:8000/api/auth/signin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepassword123"
  }'
```

Save the `access_token` from the response.

### 3. Get Current User Profile
```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. List Products
```bash
curl http://localhost:8000/api/products
```

### 5. Add to Cart
```bash
curl -X POST http://localhost:8000/api/cart/items \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "PRODUCT_ID_HERE",
    "quantity": 1
  }'
```

## WebSocket Testing

You can test the WebSocket chat using a WebSocket client:

### Using websocat (command line)
```bash
# Install websocat
# Ubuntu/Debian: cargo install websocat
# macOS: brew install websocat

# Connect to chat WebSocket
websocat "ws://localhost:8000/ws/chat/session123?token=YOUR_ACCESS_TOKEN"

# Send message (type and press Enter)
{"message": "Hello, I need help finding a laptop"}
```

### Using JavaScript (browser console)
```javascript
const token = "YOUR_ACCESS_TOKEN";
const ws = new WebSocket(`ws://localhost:8000/ws/chat/session123?token=${token}`);

ws.onopen = () => {
    console.log("Connected");
    ws.send(JSON.stringify({message: "Hello!"}));
};

ws.onmessage = (event) => {
    console.log("Received:", JSON.parse(event.data));
};
```

## Troubleshooting

### MongoDB Connection Error
```bash
# Check if MongoDB is running
sudo systemctl status mongodb

# Start MongoDB
sudo systemctl start mongodb

# Check MongoDB logs
sudo tail -f /var/log/mongodb/mongod.log
```

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Not Seeding
```bash
# Drop existing database and reseed
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017'); client.drop_database('ecommerce_db')"
python scripts/seed_database.py
```

## Development Tips

1. **Use the Swagger UI** at `/docs` for interactive API testing
2. **Enable debug mode** in `.env` by setting `DEBUG=true`
3. **Check logs** for detailed error messages
4. **Use MongoDB Compass** for visual database inspection
5. **Monitor background tasks** in application logs

## Environment Variables Reference

See `.env.example` for all available configuration options.

Key variables:
- `MONGODB_URL` - MongoDB connection string
- `JWT_SECRET_KEY` - Secret key for JWT token signing
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Access token expiration (default: 60)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token expiration (default: 7)
- `CORS_ORIGINS` - Comma-separated list of allowed origins
- `OPENAI_API_KEY` - OpenAI API key for LangChain/LangGraph
- `ENABLE_BACKGROUND_TASKS` - Enable/disable scheduled tasks

## Next Steps

1. **Integrate Frontend**: Connect your React/Vue/Angular frontend to the API
2. **Configure LangGraph**: Implement the sales agent logic in `backend/websocket/chat.py`
3. **Add More Products**: Use the seed script or admin API to add products
4. **Configure Payment Gateway**: Replace mock payment with real payment processor
5. **Set up Monitoring**: Configure Sentry for error tracking
6. **Deploy to Production**: Use Docker or deploy to cloud platforms

## Support

For issues and questions:
- Check the logs in the terminal
- Review API documentation at `/docs`
- Check MongoDB connection and data
- Ensure all environment variables are set correctly
