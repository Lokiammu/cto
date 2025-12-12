# AI Sales Chatbot Backend

This is the backend implementation for the AI Sales Chatbot, using FastAPI and MongoDB.

## Setup

1. **Install Dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   Copy `.env.example` to `.env` and update values if needed.
   ```bash
   cp .env.example .env
   ```

3. **Database Setup**
   Ensure MongoDB is running. If you have Docker:
   ```bash
   docker run -d -p 27017:27017 --name mongodb mongo:latest
   ```

4. **Initialize Schema**
   Run the schema setup script to create collections and indexes.
   ```bash
   export PYTHONPATH=$PYTHONPATH:.
   python backend/db/schema.py
   ```

5. **Seed Data**
   Populate the database with realistic test data.
   ```bash
   python backend/db/seed.py
   ```

## Running the Application

Start the FastAPI server:
```bash
uvicorn backend.main:app --reload
```

## Running Tests

Run the unit and integration tests:
```bash
pytest tests/
```

## Project Structure

- `backend/auth`: Authentication system (Signup, Signin, JWT)
- `backend/db`: Database scripts (Schema, Seed, Verify)
- `tests`: Unit and Integration tests

## Database Verification

To check collections and indexes:
```bash
python backend/db/verify.py
```
