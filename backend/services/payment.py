import random
import uuid
from typing import Dict, Any
from datetime import datetime
import asyncio


class PaymentGateway:
    """Mock payment gateway for demo purposes"""
    
    @staticmethod
    async def process_payment(
        amount: float,
        payment_method: str,
        payment_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process payment (mock implementation)
        Simulates authorization, capture, and occasional decline
        """
        # Simulate processing delay
        await asyncio.sleep(0.5)
        
        # Simulate occasional failures (10% failure rate)
        success = random.random() > 0.1
        
        transaction_id = str(uuid.uuid4())
        payment_id = f"PAY_{uuid.uuid4().hex[:12].upper()}"
        
        if success:
            status = "success"
            message = "Payment processed successfully"
        else:
            status = "failed"
            message = random.choice([
                "Insufficient funds",
                "Card declined",
                "Payment gateway timeout",
                "Invalid payment details"
            ])
        
        return {
            "payment_id": payment_id,
            "transaction_id": transaction_id,
            "status": status,
            "message": message,
            "amount": amount,
            "payment_method": payment_method,
            "processed_at": datetime.utcnow().isoformat(),
        }
    
    @staticmethod
    async def process_card_payment(
        amount: float,
        card_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process card payment"""
        return await PaymentGateway.process_payment(
            amount=amount,
            payment_method="card",
            payment_details=card_details
        )
    
    @staticmethod
    async def process_upi_payment(
        amount: float,
        upi_id: str
    ) -> Dict[str, Any]:
        """Process UPI payment"""
        return await PaymentGateway.process_payment(
            amount=amount,
            payment_method="upi",
            payment_details={"upi_id": upi_id}
        )
    
    @staticmethod
    async def process_gift_card_payment(
        amount: float,
        gift_card_code: str
    ) -> Dict[str, Any]:
        """Process gift card payment"""
        return await PaymentGateway.process_payment(
            amount=amount,
            payment_method="gift_card",
            payment_details={"gift_card_code": gift_card_code}
        )
    
    @staticmethod
    async def refund_payment(
        payment_id: str,
        amount: float
    ) -> Dict[str, Any]:
        """Process refund (mock)"""
        await asyncio.sleep(0.3)
        
        refund_id = f"REF_{uuid.uuid4().hex[:12].upper()}"
        
        return {
            "refund_id": refund_id,
            "payment_id": payment_id,
            "status": "success",
            "amount": amount,
            "processed_at": datetime.utcnow().isoformat(),
        }
