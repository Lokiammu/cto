# FastAPI Backend with WebSocket Integration

A comprehensive FastAPI backend with WebSocket chat, REST endpoints, and real-time data synchronization.

## Features

### 🔐 Authentication
- JWT-based authentication (access & refresh tokens)
- User signup, signin, logout
- Token refresh mechanism
- Rate limiting on login attempts
- Secure password hashing with bcrypt

### 💬 WebSocket Chat
- Real-time chat with session management
- JWT authentication for WebSocket connections
- Connection pooling and heartbeat mechanism
- Message history persistence
- Sales agent integration (LangGraph ready)
- Streaming responses for thinking and tool calls

### 🛍️ E-commerce Features
- **Products**: List, search, filter by category/brand/price
- **Cart**: Add/remove/update items with stock validation
- **Orders**: Create orders, track shipments, initiate returns
- **Loyalty**: Tier-based rewards, coupons, point redemption
- **Inventory**: Real-time stock updates via MongoDB change streams

### 📦 Product Management
- Pagination and filtering
- Full-text search
- Stock status tracking
- Multi-warehouse inventory support

### 💳 Payment Processing
- Mock payment gateway (card, UPI, gift card)
- Payment authorization and capture simulation
- Refund processing
- Edge case testing support

### 🔄 Real-time Features
- Inventory updates broadcast to all clients
- MongoDB change streams integration
- WebSocket connection management
- Automatic reconnection support

### ⚙️ Background Tasks
- Daily cleanup of old sessions and tokens
- Periodic inventory synchronization
- Low stock alerts
- Scheduled maintenance tasks

### 🛡️ Error Handling
- Custom exception classes
- Global error handlers
- Structured logging (JSON format)
- Request ID tracking
- Sentry integration (optional)

## Tech Stack

- **Framework**: FastAPI 0.109+
- **Database**: MongoDB (Motor async driver)
- **Authentication**: JWT (python-jose)
- **WebSocket**: Native FastAPI WebSocket
- **Background Tasks**: APScheduler
- **Logging**: Structlog
- **Testing**: Pytest, pytest-asyncio
- **Rate Limiting**: SlowAPI
- **AI Integration**: LangChain, LangGraph (ready)

## Prerequisites

- Python 3.9+
- MongoDB 4.4+
- Redis (optional, for caching)

## Installation

1. Clone the repository
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Start MongoDB
```bash
# Make sure MongoDB is running on mongodb://localhost:27017
# Or update MONGODB_URL in .env
```

## Running the Application

### Development Mode
```bash
python backend/main.py
```

Or using uvicorn directly:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/signin` - Sign in user
- `POST /api/auth/logout` - Logout user
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user profile

### Products
- `GET /api/products` - List products with filters
- `GET /api/products/{id}` - Get product details
- `GET /api/products/search` - Search products
- `GET /api/products/inventory/{id}` - Check stock levels

### Cart
- `GET /api/cart` - Get user's cart
- `POST /api/cart/items` - Add item to cart
- `PUT /api/cart/items/{id}` - Update cart item
- `DELETE /api/cart/items/{id}` - Remove from cart
- `GET /api/cart/total` - Get cart total with discounts
- `POST /api/cart/checkout` - Proceed to checkout

### Orders
- `GET /api/orders` - List user's orders
- `GET /api/orders/{id}` - Get order details
- `POST /api/orders` - Create new order
- `GET /api/orders/{id}/tracking` - Track shipment
- `POST /api/orders/{id}/return` - Initiate return

### Loyalty
- `GET /api/loyalty/profile` - Get loyalty profile
- `GET /api/loyalty/coupons` - Get available coupons
- `POST /api/loyalty/apply-coupon` - Apply coupon
- `POST /api/loyalty/redeem-points` - Redeem points
- `GET /api/loyalty/tiers` - List tier definitions

### Users
- `GET /api/users/profile` - Get user profile
- `PUT /api/users/profile` - Update profile
- `GET /api/users/addresses` - List addresses
- `POST /api/users/addresses` - Add address
- `DELETE /api/users/addresses/{id}` - Delete address
- `GET /api/users/payment-methods` - List payment methods
- `POST /api/users/payment-methods` - Add payment method
- `DELETE /api/users/payment-methods/{id}` - Delete payment method

### WebSocket
- `WS /ws/chat/{session_id}` - Chat WebSocket endpoint
  - Query param: `token` (JWT for authentication)
  - Message format: `{"message": "user message"}`
  - Response types: `user`, `assistant`, `thinking`, `tool_call`, `error`, `system`

## Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=backend --cov-report=html
```

Run specific test file:
```bash
pytest backend/tests/test_auth.py
```

Run tests by marker:
```bash
pytest -m unit
pytest -m integration
```

## WebSocket Usage Example

```javascript
// JavaScript client example
const token = "your-jwt-token";
const sessionId = "unique-session-id";
const ws = new WebSocket(`ws://localhost:8000/ws/chat/${sessionId}?token=${token}`);

ws.onopen = () => {
    console.log("Connected");
    
    // Send message
    ws.send(JSON.stringify({
        message: "Hello, I'm looking for a laptop"
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Received:", data);
    
    if (data.type === "assistant") {
        console.log("Agent:", data.content);
    }
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};
```

## Architecture

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── database.py            # MongoDB connection
├── api/                   # REST API endpoints
│   ├── auth.py           # Authentication endpoints
│   ├── products.py       # Product endpoints
│   ├── cart.py           # Cart endpoints
│   ├── orders.py         # Order endpoints
│   ├── loyalty.py        # Loyalty endpoints
│   └── users.py          # User profile endpoints
├── websocket/            # WebSocket handlers
│   ├── manager.py        # Connection manager
│   └── chat.py           # Chat endpoint
├── models/               # Pydantic models
│   ├── user.py
│   ├── auth.py
│   ├── product.py
│   ├── cart.py
│   ├── order.py
│   ├── loyalty.py
│   └── message.py
├── services/             # Business logic
│   ├── auth_service.py   # JWT & password handling
│   └── payment.py        # Payment processing
├── middleware/           # Custom middleware
│   └── error_handlers.py # Exception handlers
├── realtime/             # Real-time features
│   └── inventory.py      # Inventory change listener
├── tasks/                # Background tasks
│   ├── cleanup.py        # Cleanup tasks
│   └── inventory_sync.py # Inventory sync
└── tests/                # Test suite
    ├── conftest.py
    ├── test_auth.py
    ├── test_products.py
    ├── test_cart.py
    ├── test_orders.py
    └── test_websocket.py
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `MONGODB_URL` - MongoDB connection string
- `JWT_SECRET_KEY` - Secret key for JWT signing
- `OPENAI_API_KEY` - OpenAI API key (for LangGraph)
- `CORS_ORIGINS` - Allowed CORS origins
- `SENTRY_DSN` - Sentry error tracking (optional)

## Performance Considerations

- Response time target: < 200ms for most endpoints
- WebSocket timeout: 30 minutes idle
- JWT expiration: 1 hour (access), 7 days (refresh)
- MongoDB connection pooling: 10 max, 1 min
- Background tasks: Configurable intervals

## Security

- Passwords hashed with bcrypt
- JWT tokens with secure signing
- Rate limiting on authentication endpoints
- Token revocation on logout
- CORS configuration
- Input validation with Pydantic
- MongoDB injection prevention

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Run tests: `pytest`
5. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.
