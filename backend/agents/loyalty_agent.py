"""
Loyalty Agent

This agent specializes in managing customer loyalty programs, calculating benefits,
applying discounts, tracking points, and providing tier progression guidance.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .state import ConversationState, LoyaltyStatus
from .utils import (
    log_agent_execution, format_currency, calculate_loyalty_discount
)
from ..llm.mistral_client import get_mistral_client
from ..tools.database_tools import (
    get_loyalty_profile, apply_loyalty_discount, earn_loyalty_points,
    get_available_coupons, calculate_cart_total
)

# Configure logging
logger = logging.getLogger(__name__)


class LoyaltyAgent:
    """
    Loyalty program specialist agent.
    
    This agent manages customer loyalty benefits, calculates discounts,
    tracks points earning/redemption, and provides tier progression guidance.
    """
    
    def __init__(self):
        self.mistral_client = None
    
    async def initialize(self):
        """Initialize the loyalty agent"""
        self.mistral_client = get_mistral_client()
    
    @log_agent_execution("LoyaltyAgent.process")
    async def process(self, state: ConversationState) -> Dict[str, Any]:
        """Main processing function for the loyalty agent"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting loyalty process for user: {state.user_id}")
            
            # Step 1: Determine loyalty action from user intent
            loyalty_action = await self._determine_loyalty_action(state)
            
            if loyalty_action == "check_status":
                result = await self._check_loyalty_status(state)
            elif loyalty_action == "apply_discount":
                result = await self._apply_loyalty_discounts(state)
            elif loyalty_action == "redeem_points":
                result = await self._redeem_points(state)
            elif loyalty_action == "tier_info":
                result = await self._provide_tier_information(state)
            elif loyalty_action == "earning_opportunities":
                result = await self._show_earning_opportunities(state)
            else:
                result = await self._provide_loyalty_assistance(state)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Loyalty process completed in {processing_time:.2f}s")
            
            return {
                "content": result["content"],
                "data": {
                    **result.get("data", {}),
                    "loyalty_action": loyalty_action
                },
                "confidence": result.get("confidence", 0.8),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error in loyalty process: {str(e)}")
            return {
                "content": "I'm having trouble accessing your loyalty information right now. Please try again or contact support.",
                "data": {"error": str(e)},
                "confidence": 0.1,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def _determine_loyalty_action(self, state: ConversationState) -> str:
        """Determine what loyalty action to perform based on user intent"""
        try:
            latest_message = None
            for msg in reversed(state.messages):
                if msg.role == "user":
                    latest_message = msg.content
                    break
            
            if not latest_message:
                return "check_status"
            
            message_lower = latest_message.lower()
            
            # Check status patterns
            status_patterns = [
                "loyalty status", "my points", "loyalty points", "tier status",
                "member status", "benefits", "what's my status"
            ]
            if any(pattern in message_lower for pattern in status_patterns):
                return "check_status"
            
            # Apply discount patterns
            discount_patterns = [
                "apply discount", "use loyalty", "member discount", "loyalty benefits",
                "discount", "coupon", "promo code"
            ]
            if any(pattern in message_lower for pattern in discount_patterns):
                return "apply_discount"
            
            # Redeem points patterns
            redeem_patterns = [
                "redeem", "use points", "cash out", "spend points", "exchange points"
            ]
            if any(pattern in message_lower for pattern in redeem_patterns):
                return "redeem_points"
            
            # Tier information patterns
            tier_patterns = [
                "tier", "next level", "upgrade", "progress", "how to upgrade",
                "gold", "silver", "platinum", "bronze"
            ]
            if any(pattern in message_lower for pattern in tier_patterns):
                return "tier_info"
            
            # Earning opportunities patterns
            earning_patterns = [
                "earn points", "get points", "accumulate", "how to earn",
                "more points", "level up"
            ]
            if any(pattern in message_lower for pattern in earning_patterns):
                return "earning_opportunities"
            
            # If user has loyalty tier mentioned specifically
            loyalty_terms = ["loyalty", "member", "points", "tier", "benefits"]
            if state.customer_context and any(term in message_lower for term in loyalty_terms):
                return "check_status"
            
            # Default to providing assistance
            return "provide_assistance"
            
        except Exception as e:
            logger.error(f"Error determining loyalty action: {str(e)}")
            return "check_status"
    
    async def _check_loyalty_status(self, state: ConversationState) -> Dict[str, Any]:
        """Check customer's current loyalty status"""
        try:
            # Get loyalty profile
            loyalty_profile = await get_loyalty_profile(state.user_id)
            
            if not loyalty_profile:
                return {
                    "content": "I couldn't find your loyalty profile. You might not be enrolled yet. Would you like to join our loyalty program? It's free and you can start earning points immediately!",
                    "data": {"profile_not_found": True},
                    "confidence": 0.8
                }
            
            # Get available coupons
            available_coupons = await get_available_coupons(state.user_id)
            
            # Use Mistral to analyze loyalty status and provide insights
            loyalty_status = await self.mistral_client.calculate_loyalty_benefits(
                state=state,
                order_total=state.get_cart_total()
            )
            
            # Format status response
            current_tier = loyalty_profile.get("current_tier", "bronze").title()
            points_balance = loyalty_profile.get("points_balance", 0)
            total_spent = loyalty_profile.get("total_spent", 0.0)
            
            # Calculate next tier requirements
            tier_requirements = self._get_tier_requirements()
            next_tier = self._get_next_tier(current_tier.lower())
            progress_to_next = self._calculate_tier_progress(current_tier.lower(), total_spent, tier_requirements)
            
            # Build response
            response = f"🏆 **Your Loyalty Status**\n\n"
            response += f"**Current Tier:** {current_tier}\n"
            response += f"**Points Balance:** {points_balance:,} points\n"
            response += f"**Total Spent:** {format_currency(total_spent)}\n"
            
            if next_tier:
                if progress_to_next["amount_needed"] > 0:
                    response += f"\n📈 **Progress to {next_tier.title()}:**\n"
                    response += f"• {progress_to_next['percentage']:.1f}% complete\n"
                    response += f"• {format_currency(progress_to_next['amount_needed'])} more to spend\n"
                    response += f"• {progress_to_next['points_needed']} more points to earn\n"
                else:
                    response += f"\n🎉 **Congratulations!** You're eligible for {next_tier.title()} tier upgrade!"
            
            # Show available benefits
            response += f"\n💎 **{current_tier} Member Benefits:**\n"
            tier_benefits = self._get_tier_benefits(current_tier.lower())
            for benefit in tier_benefits:
                response += f"• {benefit}\n"
            
            # Show available coupons
            if available_coupons:
                response += f"\n🎁 **Available Coupons:**\n"
                for coupon in available_coupons[:3]:  # Show top 3
                    response += f"• {coupon['code']}: {coupon['description']}\n"
            
            # Calculate potential earnings if they shop now
            cart_total = state.get_cart_total()
            if cart_total > 0:
                points_earned = int(cart_total)
                tier_multiplier = self._get_tier_multiplier(current_tier.lower())
                total_earned = int(points_earned * tier_multiplier)
                
                response += f"\n🛒 **If you complete your current order:**\n"
                response += f"• You'll earn {total_earned} points"
                if tier_multiplier > 1.0:
                    response += f" ({points_earned} base + {total_earned - points_earned} bonus)"
                response += f"\n• That's worth {format_currency(total_earned / 10)} in future discounts!\n"
            
            response += f"\nWould you like me to apply any available discounts or show you how to earn more points?"
            
            return {
                "content": response,
                "data": {
                    "loyalty_profile": loyalty_profile,
                    "loyalty_status": loyalty_status.dict(),
                    "available_coupons": available_coupons,
                    "tier_progress": progress_to_next,
                    "cart_total": cart_total
                },
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"Error checking loyalty status: {str(e)}")
            return {
                "content": "I had trouble retrieving your loyalty status. Please try again.",
                "data": {"error": str(e)},
                "confidence": 0.1
            }
    
    async def _apply_loyalty_discounts(self, state: ConversationState) -> Dict[str, Any]:
        """Apply loyalty discounts to current order/cart"""
        try:
            if not state.cart_items:
                return {
                    "content": "You need items in your cart to apply loyalty discounts. Would you like me to show you some products first?",
                    "data": {"empty_cart": True},
                    "confidence": 0.9
                }
            
            # Get loyalty profile and cart total
            loyalty_profile = await get_loyalty_profile(state.user_id)
            cart_total = state.get_cart_total()
            
            if not loyalty_profile:
                return {
                    "content": "You're not enrolled in our loyalty program yet. Joining is free and you can start earning points immediately! Would you like to join?",
                    "data": {"not_enrolled": True},
                    "confidence": 0.8
                }
            
            current_tier = loyalty_profile.get("current_tier", "bronze")
            points_balance = loyalty_profile.get("points_balance", 0)
            
            # Calculate applicable discounts
            loyalty_discount = calculate_loyalty_discount(cart_total, current_tier)
            discount_amount = loyalty_discount["discount_amount"]
            
            # Get available coupons
            available_coupons = await get_available_coupons(state.user_id)
            
            # Determine best discount strategy
            best_strategy = await self._determine_best_discount_strategy(
                cart_total, current_tier, points_balance, available_coupons
            )
            
            response = f"💎 **Loyalty Discount Analysis**\n\n"
            response += f"**Current Tier:** {current_tier.title()}\n"
            response += f"**Cart Total:** {format_currency(cart_total)}\n\n"
            
            if discount_amount > 0:
                response += f"✅ **Automatic Tier Discount:**\n"
                response += f"• {current_tier.title()} member discount: {loyalty_discount['discount_rate']*100:.0f}%\n"
                response += f"• Savings: {format_currency(discount_amount)}\n\n"
            
            # Show point redemption options
            if points_balance >= 100:  # Minimum redemption threshold
                max_redeemable = min(points_balance, int(cart_total * 10))  # Max 100% of cart value
                if max_redeemable >= 100:
                    redemption_amount = max_redeemable / 10  # Convert points to dollars
                    response += f"🎯 **Point Redemption Options:**\n"
                    response += f"• You have {points_balance:,} points available\n"
                    response += f"• Redeem up to {max_redeemable:,} points for {format_currency(redemption_amount)} off\n"
                    response += f"• That's {int(max_redeemable/10)} points = $1 off\n\n"
            
            # Show best strategy
            if best_strategy:
                response += f"💡 **Recommended Strategy:**\n"
                response += f"• {best_strategy['description']}\n"
                response += f"• Total savings: {format_currency(best_strategy['total_savings'])}\n\n"
            
            # Show available coupons
            if available_coupons:
                response += f"🎁 **Additional Coupons Available:**\n"
                for coupon in available_coupons[:2]:
                    response += f"• {coupon['code']}: {coupon['description']}\n"
                response += "\n"
            
            new_total = cart_total - discount_amount
            response += f"**New Total:** {format_currency(new_total)}\n\n"
            response += f"Would you like me to apply the recommended discounts?"
            
            return {
                "content": response,
                "data": {
                    "cart_total": cart_total,
                    "tier_discount": discount_amount,
                    "loyalty_profile": loyalty_profile,
                    "available_coupons": available_coupons,
                    "best_strategy": best_strategy,
                    "new_total": new_total
                },
                "confidence": 0.8
            }
            
        except Exception as e:
            logger.error(f"Error applying loyalty discounts: {str(e)}")
            return {
                "content": "I had trouble calculating your loyalty discounts. Please try again.",
                "data": {"error": str(e)},
                "confidence": 0.1
            }
    
    async def _redeem_points(self, state: ConversationState) -> Dict[str, Any]:
        """Handle points redemption requests"""
        try:
            loyalty_profile = await get_loyalty_profile(state.user_id)
            
            if not loyalty_profile:
                return {
                    "content": "You're not enrolled in our loyalty program yet. Would you like to join? It's free and you can start earning points immediately!",
                    "data": {"not_enrolled": True},
                    "confidence": 0.8
                }
            
            points_balance = loyalty_profile.get("points_balance", 0)
            current_tier = loyalty_profile.get("current_tier", "bronze")
            cart_total = state.get_cart_total()
            
            if points_balance < 100:
                return {
                    "content": f"You currently have {points_balance} points, but you need at least 100 points to redeem. Keep shopping to earn more points!",
                    "data": {
                        "current_points": points_balance,
                        "minimum_required": 100,
                        "shortage": 100 - points_balance
                    },
                    "confidence": 0.9
                }
            
            # Calculate redemption options
            max_redeemable = min(points_balance, int(cart_total * 10)) if cart_total > 0 else points_balance
            redemption_tiers = [
                {"points": 100, "discount": 5.00, "description": "Small redemption"},
                {"points": 250, "discount": 15.00, "description": "Medium redemption"},
                {"points": 500, "discount": 35.00, "description": "Large redemption"},
                {"points": max_redeemable, "discount": max_redeemable / 10, "description": "Maximum redemption"}
            ]
            
            # Filter applicable tiers
            applicable_tiers = [tier for tier in redemption_tiers if tier["points"] <= points_balance]
            
            if not applicable_tiers:
                return {
                    "content": f"You have {points_balance} points available for redemption, but no valid redemption tiers match your current balance.",
                    "data": {"points_balance": points_balance},
                    "confidence": 0.7
                }
            
            response = f"🎯 **Points Redemption**\n\n"
            response += f"**Your Balance:** {points_balance:,} points\n"
            if cart_total > 0:
                response += f"**Cart Total:** {format_currency(cart_total)}\n"
            response += f"**Current Tier:** {current_tier.title()}\n\n"
            
            response += f"**Choose Your Redemption:**\n\n"
            
            for i, tier in enumerate(applicable_tiers, 1):
                dollar_value = tier["discount"]
                response += f"{i}. **{tier['points']:,} points** → {format_currency(dollar_value)} off\n"
                response += f"   {tier['description']}\n\n"
            
            # Show benefits of keeping points for higher tiers
            if current_tier in ["bronze", "silver"]:
                next_tier = self._get_next_tier(current_tier)
                if next_tier:
                    response += f"💡 **Pro Tip:** Consider saving points to reach {next_tier.title()} tier for better discounts!\n\n"
            
            response += f"Which redemption amount would you like to use?"
            
            return {
                "content": response,
                "data": {
                    "points_balance": points_balance,
                    "redemption_tiers": applicable_tiers,
                    "cart_total": cart_total,
                    "current_tier": current_tier
                },
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"Error in points redemption: {str(e)}")
            return {
                "content": "I had trouble processing your points redemption. Please try again.",
                "data": {"error": str(e)},
                "confidence": 0.1
            }
    
    async def _provide_tier_information(self, state: ConversationState) -> Dict[str, Any]:
        """Provide information about loyalty tiers"""
        try:
            loyalty_profile = await get_loyalty_profile(state.user_id)
            current_tier = loyalty_profile.get("current_tier", "bronze") if loyalty_profile else "bronze"
            total_spent = loyalty_profile.get("total_spent", 0.0) if loyalty_profile else 0.0
            
            tier_requirements = self._get_tier_requirements()
            
            response = f"🏆 **Loyalty Tier Information**\n\n"
            
            for tier_name, requirements in tier_requirements.items():
                tier_title = tier_name.title()
                status_indicator = "✅ " if tier_name == current_tier else "⬜ "
                
                response += f"{status_indicator}**{tier_title} Tier:**\n"
                response += f"• Minimum spend: {format_currency(requirements['min_spent'])}\n"
                response += f"• Benefits: {', '.join(requirements['benefits'])}\n"
                
                # Show progress if this is current or next tier
                if tier_name == current_tier or tier_name == self._get_next_tier(current_tier):
                    if total_spent < requirements['min_spent']:
                        amount_needed = requirements['min_spent'] - total_spent
                        percentage = (total_spent / requirements['min_spent']) * 100
                        response += f"• Your progress: {percentage:.1f}% ({format_currency(amount_needed)} to go)\n"
                    else:
                        response += f"• You've reached this tier! 🎉\n"
                
                response += "\n"
            
            # Add earning information
            response += f"💰 **How to Earn Points:**\n"
            response += f"• 1 point per $1 spent (base rate)\n"
            response += f"• Silver: 1.25x points\n"
            response += f"• Gold: 1.5x points\n"
            response += f"• Platinum: 2x points\n\n"
            
            # Special promotions
            response += f"🎁 **Current Promotions:**\n"
            response += f"• Double points on select categories\n"
            response += f"• Birthday month bonus: 500 points\n"
            response += f"• Referral bonus: 200 points per friend\n\n"
            
            if current_tier != "platinum":
                next_tier = self._get_next_tier(current_tier)
                if next_tier:
                    response += f"Ready to level up? You're {format_currency(tier_requirements[next_tier]['min_spent'] - total_spent)} away from {next_tier.title()}!"
            
            return {
                "content": response,
                "data": {
                    "current_tier": current_tier,
                    "total_spent": total_spent,
                    "tier_requirements": tier_requirements
                },
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"Error providing tier information: {str(e)}")
            return {
                "content": "I had trouble retrieving tier information. Please try again.",
                "data": {"error": str(e)},
                "confidence": 0.1
            }
    
    async def _show_earning_opportunities(self, state: ConversationState) -> Dict[str, Any]:
        """Show ways to earn loyalty points"""
        try:
            loyalty_profile = await get_loyalty_profile(state.user_id)
            current_tier = loyalty_profile.get("current_tier", "bronze") if loyalty_profile else "bronze"
            
            response = f"💰 **Ways to Earn Loyalty Points**\n\n"
            
            # Shopping earn rates
            response += f"🛒 **Shopping:**\n"
            response += f"• Earn points on every purchase\n"
            response += f"• Bronze: 1 point per $1\n"
            response += f"• Silver: 1.25 points per $1\n"
            response += f"• Gold: 1.5 points per $1\n"
            response += f"• Platinum: 2 points per $1\n\n"
            
            # Bonus earning opportunities
            response += f"🎁 **Bonus Point Opportunities:**\n"
            response += f"• Write product reviews: 50 points per review\n"
            response += f"• Refer a friend: 200 points\n"
            response += f"• Follow us on social media: 100 points\n"
            response += f"• Complete your profile: 150 points\n"
            response += f"• Birthday bonus: 500 points (once per year)\n"
            response += f"• First purchase: 100 points bonus\n\n"
            
            # Seasonal promotions
            response += f"🌟 **Current Promotions:**\n"
            response += f"• Weekend warrior: Double points on weekends\n"
            response += f"• Category bonus: 2x points on electronics this month\n"
            response += f"• New customer special: 3x points on first order\n\n"
            
            # Ways to maximize earning
            response += f"💡 **Maximize Your Earnings:**\n"
            response += f"• Shop during double point promotions\n"
            response += f"• Complete your profile for bonus points\n"
            response += f"• Leave reviews for products you've purchased\n"
            response += f"• Refer friends and family\n"
            response += f"• Follow us for exclusive offers\n\n"
            
            # Calculate potential earnings from current cart
            if state.cart_items:
                cart_total = state.get_cart_total()
                multiplier = self._get_tier_multiplier(current_tier)
                potential_points = int(cart_total * multiplier)
                
                response += f"🛒 **Current Cart Potential:**\n"
                response += f"• You'll earn {potential_points} points from this order"
                if multiplier > 1.0:
                    response += f" ({int(cart_total)} base + {potential_points - int(cart_total)} bonus)"
                response += f"\n• That's worth {format_currency(potential_points / 10)} in future discounts!\n"
            
            response += f"\nStart earning today with your next purchase!"
            
            return {
                "content": response,
                "data": {
                    "current_tier": current_tier,
                    "cart_total": state.get_cart_total() if state.cart_items else 0
                },
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"Error showing earning opportunities: {str(e)}")
            return {
                "content": "I had trouble showing earning opportunities. Please try again.",
                "data": {"error": str(e)},
                "confidence": 0.1
            }
    
    async def _provide_loyalty_assistance(self, state: ConversationState) -> Dict[str, Any]:
        """Provide general loyalty program assistance"""
        try:
            loyalty_profile = await get_loyalty_profile(state.user_id)
            
            if not loyalty_profile:
                response = f"🎯 **Loyalty Program Overview**\n\n"
                response += f"Our loyalty program is free to join and helps you save money while shopping!\n\n"
                response += f"**Benefits include:**\n"
                response += f"• Earn points on every purchase\n"
                response += f"• Exclusive member discounts\n"
                response += f"• Early access to sales\n"
                response += f"• Birthday bonuses\n"
                response += f"• Free shipping on orders over $50\n\n"
                response += f"**How it works:**\n"
                response += f"1. Join for free (done!)\n"
                response += f"2. Shop and earn 1+ points per $1\n"
                response += f"3. Redeem points for discounts\n"
                response += f"4. Unlock better benefits as you spend more\n\n"
                response += f"Would you like me to help you check your current status or show you how to earn more points?"
                
                return {
                    "content": response,
                    "data": {"not_enrolled": True},
                    "confidence": 0.8
                }
            
            # Customer is enrolled, show summary
            current_tier = loyalty_profile.get("current_tier", "bronze").title()
            points_balance = loyalty_profile.get("points_balance", 0)
            
            response = f"👋 **Loyalty Program Help**\n\n"
            response += f"**Your Status:** {current_tier} Member ({points_balance:,} points)\n\n"
            response += f"I can help you with:\n\n"
            response += f"• 🏆 Check your loyalty status and progress\n"
            response += f"• 💰 Apply loyalty discounts to your cart\n"
            response += f"• 🎯 Redeem points for discounts\n"
            response += f"• 📈 Learn about tier upgrades\n"
            response += f"• 💡 Find ways to earn more points\n\n"
            response += f"What would you like to know about your loyalty benefits?"
            
            return {
                "content": response,
                "data": {
                    "loyalty_profile": loyalty_profile,
                    "assistance_provided": True
                },
                "confidence": 0.8
            }
            
        except Exception as e:
            logger.error(f"Error providing loyalty assistance: {str(e)}")
            return {
                "content": "I'm here to help with your loyalty benefits! What would you like to know?",
                "data": {"error": str(e)},
                "confidence": 0.5
            }
    
    async def _determine_best_discount_strategy(
        self, 
        cart_total: float, 
        current_tier: str, 
        points_balance: int, 
        available_coupons: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Determine the best discount strategy for the customer"""
        try:
            if cart_total <= 0:
                return None
            
            # Calculate tier discount
            tier_discount = calculate_loyalty_discount(cart_total, current_tier)
            tier_savings = tier_discount["discount_amount"]
            
            # Calculate point redemption value
            max_redeemable = min(points_balance, int(cart_total * 10))
            redemption_value = max_redeemable / 10 if max_redeemable >= 100 else 0
            
            # Find best coupon
            best_coupon = None
            if available_coupons:
                best_coupon = max(available_coupons, key=lambda c: c.get("discount", 0))
            
            coupon_value = best_coupon.get("discount", 0) if best_coupon else 0
            
            # Determine strategy
            strategies = []
            
            if tier_savings > 0:
                strategies.append({
                    "type": "tier_discount",
                    "description": f"{current_tier.title()} member discount",
                    "savings": tier_savings,
                    "apply_immediately": True
                })
            
            if redemption_value > 0:
                strategies.append({
                    "type": "point_redemption",
                    "description": f"Redeem {max_redeemable} points",
                    "savings": redemption_value,
                    "requires_confirmation": True
                })
            
            if coupon_value > 0:
                strategies.append({
                    "type": "coupon",
                    "description": f"Apply {best_coupon['code']}",
                    "savings": coupon_value,
                    "apply_immediately": True
                })
            
            if not strategies:
                return None
            
            # Find best combination (simplified - could be more sophisticated)
            best_strategy = max(strategies, key=lambda s: s["savings"])
            total_savings = sum(s["savings"] for s in strategies)
            
            return {
                "description": f"Apply {best_strategy['type'].replace('_', ' ')}",
                "total_savings": total_savings,
                "strategies": strategies,
                "new_total": cart_total - total_savings
            }
            
        except Exception as e:
            logger.error(f"Error determining discount strategy: {str(e)}")
            return None
    
    def _get_tier_requirements(self) -> Dict[str, Dict[str, Any]]:
        """Get loyalty tier requirements and benefits"""
        return {
            "bronze": {
                "min_spent": 0,
                "benefits": ["Basic point earning", "Member-only promotions"]
            },
            "silver": {
                "min_spent": 500,
                "benefits": ["1.25x point earning", "5% discount", "Free shipping over $50"]
            },
            "gold": {
                "min_spent": 1500,
                "benefits": ["1.5x point earning", "10% discount", "Priority customer service"]
            },
            "platinum": {
                "min_spent": 3000,
                "benefits": ["2x point earning", "15% discount", "VIP support", "Early access"]
            }
        }
    
    def _get_next_tier(self, current_tier: str) -> Optional[str]:
        """Get the next tier above current tier"""
        tier_order = ["bronze", "silver", "gold", "platinum"]
        try:
            current_index = tier_order.index(current_tier)
            if current_index < len(tier_order) - 1:
                return tier_order[current_index + 1]
        except ValueError:
            pass
        return None
    
    def _calculate_tier_progress(
        self, 
        current_tier: str, 
        total_spent: float, 
        tier_requirements: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate progress to next tier"""
        next_tier = self._get_next_tier(current_tier)
        
        if not next_tier:
            return {
                "percentage": 100.0,
                "amount_needed": 0.0,
                "points_needed": 0,
                "is_max_tier": True
            }
        
        next_tier_requirement = tier_requirements[next_tier]["min_spent"]
        amount_needed = max(0, next_tier_requirement - total_spent)
        percentage = min(100, (total_spent / next_tier_requirement) * 100) if next_tier_requirement > 0 else 100
        
        # Estimate points needed (rough calculation)
        estimated_points_needed = int(amount_needed)
        
        return {
            "percentage": percentage,
            "amount_needed": amount_needed,
            "points_needed": estimated_points_needed,
            "is_max_tier": False,
            "next_tier": next_tier
        }
    
    def _get_tier_multiplier(self, tier: str) -> float:
        """Get point earning multiplier for tier"""
        multipliers = {
            "bronze": 1.0,
            "silver": 1.25,
            "gold": 1.5,
            "platinum": 2.0
        }
        return multipliers.get(tier.lower(), 1.0)
    
    def _get_tier_benefits(self, tier: str) -> List[str]:
        """Get benefits for a specific tier"""
        all_benefits = {
            "bronze": [
                "Earn points on every purchase",
                "Member-only promotions",
                "Birthday bonus"
            ],
            "silver": [
                "1.25x points earning",
                "5% discount on orders",
                "Free shipping on orders over $50",
                "Priority email support"
            ],
            "gold": [
                "1.5x points earning",
                "10% discount on orders",
                "Free shipping on all orders",
                "Priority customer service",
                "Early access to sales"
            ],
            "platinum": [
                "2x points earning",
                "15% discount on orders",
                "Free expedited shipping",
                "VIP customer support",
                "Exclusive product access",
                "Personal shopping assistant"
            ]
        }
        return all_benefits.get(tier.lower(), all_benefits["bronze"])


# Global instance
_loyalty_agent: Optional[LoyaltyAgent] = None


async def get_loyalty_agent() -> LoyaltyAgent:
    """Get or create global loyalty agent instance"""
    global _loyalty_agent
    
    if _loyalty_agent is None:
        _loyalty_agent = LoyaltyAgent()
        await _loyalty_agent.initialize()
    
    return _loyalty_agent