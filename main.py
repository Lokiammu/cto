"""
Main Application Entry Point

This module serves as the main entry point for the LangGraph Sales Agent system.
It can be run directly or imported as a module.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from api_server import app
from backend.tools.database_tools import initialize_database, close_database
from backend.llm.mistral_client import initialize_mistral_client, get_mistral_client
from backend.agents.sales_agent import get_sales_orchestrator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('sales_agent.log')
    ]
)
logger = logging.getLogger(__name__)


async def setup_application():
    """Set up the application with all necessary components"""
    try:
        logger.info("Setting up LangGraph Sales Agent System...")
        
        # Check environment variables
        required_env_vars = ["MISTRAL_API_KEY"]
        missing_vars = []
        
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            logger.error("Please set these variables in your .env file")
            return False
        
        # Initialize database connection
        logger.info("Initializing database connection...")
        await initialize_database()
        
        # Initialize Mistral client
        logger.info("Initializing Mistral client...")
        await initialize_mistral_client()
        
        # Initialize sales orchestrator
        logger.info("Initializing sales orchestrator...")
        await get_sales_orchestrator()
        
        logger.info("Application setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Application setup failed: {str(e)}")
        return False


async def cleanup_application():
    """Clean up application resources"""
    try:
        logger.info("Cleaning up application resources...")
        
        # Close database connection
        await close_database()
        
        logger.info("Application cleanup completed")
        
    except Exception as e:
        logger.error(f"Application cleanup failed: {str(e)}")


async def main():
    """Main application entry point"""
    try:
        # Set up the application
        setup_success = await setup_application()
        
        if not setup_success:
            logger.error("Failed to set up application. Exiting.")
            sys.exit(1)
        
        # Import uvicorn here to avoid import issues
        import uvicorn
        
        logger.info("Starting LangGraph Sales Agent API server...")
        
        # Run the API server
        uvicorn.run(
            app,
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            workers=int(os.getenv("API_WORKERS", "4")),
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)
    finally:
        await cleanup_application()


def run_interactive_demo():
    """Run an interactive demo of the sales agent"""
    import asyncio
    from backend.agents.sales_agent import process_sales_conversation
    
    async def demo():
        print("🤖 LangGraph Sales Agent Demo")
        print("=" * 50)
        print("Type 'quit' to exit the demo")
        print()
        
        user_id = "demo_user"
        channel = "console"
        session_id = None
        
        while True:
            try:
                user_input = input("👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                print("🤖 Agent: Thinking...")
                
                # Process the message
                result = await process_sales_conversation(
                    user_id=user_id,
                    channel=channel,
                    message=user_input,
                    session_id=session_id
                )
                
                session_id = result["session_id"]
                
                print(f"🤖 Agent: {result['response']}")
                print(f"   Intent: {result.get('current_intent', 'Unknown')}")
                print(f"   Agent: {result.get('last_agent', 'Unknown')}")
                print(f"   Cart: {result.get('cart_items_count', 0)} items")
                print()
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                print()
    
    # Run the demo
    asyncio.run(demo())


def run_tests():
    """Run the test suite"""
    import subprocess
    
    try:
        logger.info("Running test suite...")
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "backend/tests/", 
            "-v", 
            "--tb=short"
        ], cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            logger.info("All tests passed! ✅")
        else:
            logger.error("Some tests failed! ❌")
            
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"Failed to run tests: {str(e)}")
        return False


def create_sample_data():
    """Create sample data for testing"""
    import asyncio
    from backend.tools.database_tools import db
    
    async def create_data():
        try:
            logger.info("Creating sample data...")
            
            # Sample products
            products = [
                {
                    "product_id": "LAPTOP001",
                    "name": "Professional Laptop 15-inch",
                    "description": "High-performance laptop for professionals",
                    "price": 1299.99,
                    "category": "electronics",
                    "status": "active",
                    "is_featured": True
                },
                {
                    "product_id": "PHONE001", 
                    "name": "Smartphone Pro Max",
                    "description": "Latest smartphone with advanced features",
                    "price": 999.99,
                    "category": "electronics",
                    "status": "active",
                    "is_featured": True
                },
                {
                    "product_id": "HEAD001",
                    "name": "Wireless Headphones",
                    "description": "Premium noise-canceling headphones",
                    "price": 299.99,
                    "category": "electronics",
                    "status": "active"
                }
            ]
            
            # Insert products
            await db.products.insert_many(products)
            logger.info(f"Inserted {len(products)} products")
            
            # Sample customers
            customers = [
                {
                    "user_id": "demo_user",
                    "name": "Demo Customer",
                    "email": "demo@example.com",
                    "loyalty_tier": "gold",
                    "loyalty_points": 1500,
                    "total_spent": 2500.00,
                    "preferences": {"category": "electronics"},
                    "past_purchases": [{"product_id": "LAPTOP001", "total": 1299.99}],
                    "location": {"lat": 37.7749, "lng": -122.4194}
                },
                {
                    "user_id": "new_user",
                    "name": "New Customer",
                    "email": "new@example.com",
                    "loyalty_tier": "bronze",
                    "loyalty_points": 50,
                    "total_spent": 75.00
                }
            ]
            
            # Insert customers
            await db.customers.insert_many(customers)
            logger.info(f"Inserted {len(customers)} customers")
            
            # Sample inventory
            inventory = [
                {
                    "product_id": "LAPTOP001",
                    "warehouse_stock": 25,
                    "store_stock": 5,
                    "updated_at": asyncio.get_event_loop().time()
                },
                {
                    "product_id": "PHONE001",
                    "warehouse_stock": 50,
                    "store_stock": 10,
                    "updated_at": asyncio.get_event_loop().time()
                },
                {
                    "product_id": "HEAD001",
                    "warehouse_stock": 100,
                    "store_stock": 20,
                    "updated_at": asyncio.get_event_loop().time()
                }
            ]
            
            # Insert inventory
            await db.inventory.insert_many(inventory)
            logger.info(f"Inserted {len(inventory)} inventory records")
            
            # Sample stores
            stores = [
                {
                    "store_id": "STORE001",
                    "name": "Downtown Store",
                    "address": "123 Main St, San Francisco, CA 94102",
                    "location": {"type": "Point", "coordinates": [-122.4194, 37.7749]}
                },
                {
                    "store_id": "STORE002", 
                    "name": "Mall Store",
                    "address": "456 Mall Ave, San Francisco, CA 94102",
                    "location": {"type": "Point", "coordinates": [-122.4094, 37.7849]}
                }
            ]
            
            # Insert stores
            await db.stores.insert_many(stores)
            logger.info(f"Inserted {len(stores)} stores")
            
            logger.info("Sample data created successfully! ✅")
            
        except Exception as e:
            logger.error(f"Failed to create sample data: {str(e)}")
    
    asyncio.run(create_data())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="LangGraph Sales Agent System")
    parser.add_argument(
        "command",
        choices=["server", "demo", "test", "setup-data", "help"],
        help="Command to run"
    )
    
    args = parser.parse_args()
    
    if args.command == "server":
        # Run the API server
        asyncio.run(main())
    elif args.command == "demo":
        # Run interactive demo
        run_interactive_demo()
    elif args.command == "test":
        # Run tests
        success = run_tests()
        sys.exit(0 if success else 1)
    elif args.command == "setup-data":
        # Create sample data
        create_sample_data()
    elif args.command == "help":
        print(__doc__)
        print("\nAvailable commands:")
        print("  server     - Run the API server")
        print("  demo       - Run interactive demo")
        print("  test       - Run test suite")
        print("  setup-data - Create sample data")
        print("\nEnvironment variables required:")
        print("  MISTRAL_API_KEY - Your Mistral AI API key")
        print("  MONGODB_URI - MongoDB connection string")
    else:
        parser.print_help()