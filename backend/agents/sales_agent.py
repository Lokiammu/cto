"""
Sales Orchestrator LangGraph

This is the main LangGraph that orchestrates the entire sales conversation flow.
It manages the conversation state and routes to appropriate worker agents based on user intent.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import ConversationState, IntentAnalysis
from .utils import (
    log_agent_execution, validate_input, 
    add_message_reducer, update_intent_reducer, 
    add_agent_response_reducer, add_error_reducer
)
from ..llm.mistral_client import get_mistral_client
from ..tools.database_tools import (
    fetch_customer_profile, save_conversation_log, 
    update_channel_session, fetch_conversation_history
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SalesOrchestrator:
    """
    Main orchestrator for the sales agent system.
    
    This LangGraph manages the conversation flow and routes to appropriate
    worker agents based on detected user intent.
    """
    
    def __init__(self):
        self.graph = None
        self.mistral_client = None
    
    async def initialize(self):
        """Initialize the orchestrator with dependencies"""
        self.mistral_client = get_mistral_client()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph with nodes and edges"""
        
        # Create state graph
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("retrieve_context", self.retrieve_context_node)
        workflow.add_node("analyze_intent", self.analyze_intent_node)
        workflow.add_node("route_decision", self.route_decision_node)
        workflow.add_node("execute_agent", self.execute_agent_node)
        workflow.add_node("aggregate_response", self.aggregate_response_node)
        workflow.add_node("save_to_db", self.save_to_db_node)
        
        # Add edges
        workflow.set_entry_point("retrieve_context")
        
        # Main flow
        workflow.add_edge("retrieve_context", "analyze_intent")
        workflow.add_edge("analyze_intent", "route_decision")
        workflow.add_edge("route_decision", "execute_agent")
        workflow.add_edge("execute_agent", "aggregate_response")
        workflow.add_edge("aggregate_response", "save_to_db")
        workflow.add_edge("save_to_db", END)
        
        # Error handling edges
        workflow.add_edge("retrieve_context", "aggregate_response")  # Skip intent if context fails
        workflow.add_edge("analyze_intent", "aggregate_response")    # Skip routing if intent fails
        
        # Add memory for state persistence
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    @log_agent_execution("SalesOrchestrator.retrieve_context")
    async def retrieve_context_node(self, state: ConversationState) -> ConversationState:
        """Retrieve customer context and session information"""
        try:
            # Fetch customer profile
            customer_profile = await fetch_customer_profile(state.user_id)
            
            if customer_profile:
                # Update state with customer context
                customer_context = {
                    "user_id": customer_profile.get("user_id"),
                    "name": customer_profile.get("name", "Customer"),
                    "email": customer_profile.get("email"),
                    "loyalty_tier": customer_profile.get("loyalty_tier", "bronze"),
                    "loyalty_points": customer_profile.get("loyalty_points", 0),
                    "preferences": customer_profile.get("preferences", {}),
                    "past_purchases": customer_profile.get("past_purchases", []),
                    "browsing_history": customer_profile.get("browsing_history", []),
                    "location": customer_profile.get("location"),
                    "communication_preferences": customer_profile.get("communication_preferences", {})
                }
                state.update_customer_context(**customer_context)
                logger.info(f"Retrieved context for customer: {customer_profile.get('name')}")
            else:
                logger.info(f"No existing profile found for user: {state.user_id}")
            
            # Add system message about context retrieval
            state.add_message(
                role="system",
                content="Customer context retrieved successfully" if customer_profile else "No existing customer profile found",
                agent_name="sales_orchestrator"
            )
            
            state.workflow_step = "context_retrieved"
            
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            state.add_error("Context retrieval failed", "sales_orchestrator")
            state.add_message(
                role="system",
                content="Unable to retrieve customer context",
                agent_name="sales_orchestrator"
            )
        
        return state
    
    @log_agent_execution("SalesOrchestrator.analyze_intent")
    async def analyze_intent_node(self, state: ConversationState) -> ConversationState:
        """Analyze user intent using Mistral LLM"""
        try:
            if not state.messages:
                # Set default greeting intent if no messages
                state.current_intent = "greeting"
                state.workflow_step = "intent_analyzed"
                return state
            
            # Get the latest user message
            latest_message = None
            for msg in reversed(state.messages):
                if msg.role == "user":
                    latest_message = msg.content
                    break
            
            if not latest_message:
                state.current_intent = "general_chat"
                state.workflow_step = "intent_analyzed"
                return state
            
            # Analyze intent using Mistral
            intent_analysis = await self.mistral_client.analyze_intent(latest_message, state)
            
            # Update state with intent analysis
            state.current_intent = intent_analysis.intent
            
            # Add intent analysis as system message
            state.add_message(
                role="system",
                content=f"Intent detected: {intent_analysis.intent} (confidence: {intent_analysis.confidence:.2f})",
                agent_name="sales_orchestrator",
                metadata={
                    "intent_analysis": intent_analysis.dict(),
                    "reasoning": intent_analysis.reasoning
                }
            )
            
            logger.info(f"Intent analyzed: {intent_analysis.intent} (confidence: {intent_analysis.confidence:.2f})")
            
            state.workflow_step = "intent_analyzed"
            
        except Exception as e:
            logger.error(f"Error analyzing intent: {str(e)}")
            state.current_intent = "general_chat"  # Fallback intent
            state.add_error(f"Intent analysis failed: {str(e)}", "sales_orchestrator")
        
        return state
    
    @log_agent_execution("SalesOrchestrator.route_decision")
    async def route_decision_node(self, state: ConversationState) -> ConversationState:
        """Determine which agent to route to based on intent"""
        try:
            intent = state.current_intent
            
            # Route mapping based on intent
            route_mapping = {
                "greeting": "sales_orchestrator",  # Handle directly
                "browse": "recommendation_agent",
                "search": "recommendation_agent",
                "recommend": "recommendation_agent",
                "add_to_cart": "cart_agent",
                "checkout": "cart_agent",
                "inventory_check": "inventory_agent",
                "loyalty": "loyalty_agent",
                "support": "sales_orchestrator",  # Handle directly
                "general_chat": "sales_orchestrator"  # Handle directly
            }
            
            target_agent = route_mapping.get(intent, "sales_orchestrator")
            
            # Add routing decision to state
            state.add_message(
                role="system",
                content=f"Routing to {target_agent} for intent: {intent}",
                agent_name="sales_orchestrator",
                metadata={
                    "routing_decision": {
                        "intent": intent,
                        "target_agent": target_agent,
                        "routing_time": datetime.now().isoformat()
                    }
                }
            )
            
            # Store routing decision in state for next node
            state.metadata["routing_decision"] = {
                "intent": intent,
                "target_agent": target_agent
            }
            
            logger.info(f"Routing decision: {intent} -> {target_agent}")
            
            state.workflow_step = "routing_decided"
            
        except Exception as e:
            logger.error(f"Error in routing decision: {str(e)}")
            # Default to sales orchestrator for any routing errors
            state.metadata["routing_decision"] = {
                "intent": state.current_intent,
                "target_agent": "sales_orchestrator"
            }
            state.add_error(f"Routing decision failed: {str(e)}", "sales_orchestrator")
        
        return state
    
    @log_agent_execution("SalesOrchestrator.execute_agent")
    async def execute_agent_node(self, state: ConversationState) -> ConversationState:
        """Execute the appropriate worker agent"""
        try:
            routing_decision = state.metadata.get("routing_decision", {})
            target_agent = routing_decision.get("target_agent", "sales_orchestrator")
            
            if target_agent == "sales_orchestrator":
                # Handle directly in orchestrator
                response = await self._handle_direct_response(state)
            else:
                # Route to appropriate worker agent
                response = await self._route_to_agent(target_agent, state)
            
            # Add the response to state
            state.add_agent_response(
                agent_name=target_agent,
                content=response["content"],
                data=response.get("data", {}),
                confidence=response.get("confidence", 1.0),
                processing_time=response.get("processing_time", 0.0)
            )
            
            # Add the response as an assistant message
            state.add_message(
                role="assistant",
                content=response["content"],
                agent_name=target_agent
            )
            
            logger.info(f"Agent {target_agent} executed successfully")
            
            state.workflow_step = "agent_executed"
            
        except Exception as e:
            logger.error(f"Error executing agent: {str(e)}")
            error_response = {
                "content": "I apologize, but I'm having trouble processing your request right now. Please try again or rephrase your question.",
                "confidence": 0.1,
                "processing_time": 0.0
            }
            
            state.add_agent_response(
                agent_name="error_handler",
                content=error_response["content"],
                data={"error": str(e)},
                confidence=error_response["confidence"]
            )
            
            state.add_error(f"Agent execution failed: {str(e)}", "sales_orchestrator")
            state.workflow_step = "agent_executed"
        
        return state
    
    async def _handle_direct_response(self, state: ConversationState) -> Dict[str, Any]:
        """Handle responses directly in the orchestrator"""
        intent = state.current_intent
        
        if intent == "greeting":
            customer_name = state.customer_context.name if state.customer_context else "Customer"
            return {
                "content": f"Hello {customer_name}! 👋 I'm here to help you with your shopping needs. What can I assist you with today?",
                "confidence": 1.0,
                "processing_time": 0.1
            }
        
        elif intent == "support":
            return {
                "content": "I'm here to help! Please let me know what specific assistance you need - whether it's about products, your account, orders, or anything else. I'll do my best to help resolve your issue.",
                "confidence": 1.0,
                "processing_time": 0.1
            }
        
        else:  # general_chat
            return await self.mistral_client.generate_sales_response(state)
    
    async def _route_to_agent(self, agent_name: str, state: ConversationState) -> Dict[str, Any]:
        """Route to specific worker agent"""
        
        # Import agents dynamically to avoid circular imports
        from .recommendation_agent import RecommendationAgent
        from .inventory_agent import InventoryAgent
        from .cart_agent import CartAgent
        from .loyalty_agent import LoyaltyAgent
        
        agents = {
            "recommendation_agent": RecommendationAgent(),
            "inventory_agent": InventoryAgent(),
            "cart_agent": CartAgent(),
            "loyalty_agent": LoyaltyAgent()
        }
        
        if agent_name not in agents:
            # Fallback to orchestrator response
            return await self._handle_direct_response(state)
        
        try:
            agent = agents[agent_name]
            return await agent.process(state)
        except Exception as e:
            logger.error(f"Error routing to {agent_name}: {str(e)}")
            return {
                "content": f"I apologize, but I'm having trouble with the {agent_name.replace('_', ' ')} right now. Let me help you directly.",
                "confidence": 0.3,
                "processing_time": 0.0
            }
    
    @log_agent_execution("SalesOrchestrator.aggregate_response")
    async def aggregate_response_node(self, state: ConversationState) -> ConversationState:
        """Aggregate responses from all agents and prepare final response"""
        try:
            if not state.agent_responses:
                # No agent responses, create default response
                final_response = await self._create_default_response(state)
            else:
                # Aggregate the most recent agent response
                latest_response = state.agent_responses[-1]
                final_response = latest_response.content
            
            # Store final response in state
            state.metadata["final_response"] = final_response
            state.workflow_step = "response_aggregated"
            
            logger.info("Response aggregation completed")
            
        except Exception as e:
            logger.error(f"Error aggregating response: {str(e)}")
            state.add_error(f"Response aggregation failed: {str(e)}", "sales_orchestrator")
        
        return state
    
    async def _create_default_response(self, state: ConversationState) -> str:
        """Create a default response when no agent responses are available"""
        return f"Thank you for your message. I'm here to help you with your shopping needs. Current cart: {state.get_cart_items_count()} items."
    
    @log_agent_execution("SalesOrchestrator.save_to_db")
    async def save_to_db_node(self, state: ConversationState) -> ConversationState:
        """Save conversation state to database"""
        try:
            # Convert messages to serializable format
            messages_data = []
            for message in state.messages:
                messages_data.append({
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat() if isinstance(message.timestamp, datetime) else message.timestamp,
                    "agent_name": message.agent_name,
                    "metadata": message.metadata
                })
            
            # Save conversation log
            await save_conversation_log(
                session_id=state.session_id,
                user_id=state.user_id,
                messages=messages_data,
                metadata={
                    "current_intent": state.current_intent,
                    "last_agent": state.last_agent,
                    "cart_items_count": len(state.cart_items),
                    "workflow_step": state.workflow_step,
                    "error_count": state.error_count,
                    "channel": state.channel
                }
            )
            
            # Update channel session
            await update_channel_session(
                session_id=state.session_id,
                state_data={
                    "user_id": state.user_id,
                    "current_intent": state.current_intent,
                    "last_agent": state.last_agent,
                    "workflow_step": state.workflow_step,
                    "is_active": state.is_active,
                    "updated_at": datetime.now().isoformat()
                }
            )
            
            state.workflow_step = "conversation_saved"
            logger.info(f"Conversation saved for session: {state.session_id}")
            
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            state.add_error(f"Database save failed: {str(e)}", "sales_orchestrator")
        
        return state
    
    async def process_message(self, state: ConversationState) -> ConversationState:
        """Main entry point for processing a message through the graph"""
        try:
            # Validate input state
            if not state.session_id:
                state.session_id = state.session_id or f"session_{datetime.now().timestamp()}"
            
            if not state.user_id:
                raise ValueError("user_id is required")
            
            if not state.channel:
                raise ValueError("channel is required")
            
            # Execute the graph
            final_state = await self.graph.ainvoke(state)
            
            return final_state
            
        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}")
            state.add_error(f"Process message failed: {str(e)}", "sales_orchestrator")
            return state
    
    async def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for a user"""
        try:
            return await fetch_conversation_history(user_id, limit)
        except Exception as e:
            logger.error(f"Error fetching conversation history: {str(e)}")
            return []


# Global instance
_sales_orchestrator: Optional[SalesOrchestrator] = None


async def get_sales_orchestrator() -> SalesOrchestrator:
    """Get or create global sales orchestrator instance"""
    global _sales_orchestrator
    
    if _sales_orchestrator is None:
        _sales_orchestrator = SalesOrchestrator()
        await _sales_orchestrator.initialize()
    
    return _sales_orchestrator


async def create_initial_state(
    user_id: str,
    channel: str,
    session_id: str = None,
    initial_message: str = None
) -> ConversationState:
    """Create initial conversation state"""
    state = ConversationState(
        user_id=user_id,
        channel=channel,
        session_id=session_id
    )
    
    if initial_message:
        state.add_message(
            role="user",
            content=initial_message,
            agent_name=None
        )
    
    return state


async def process_sales_conversation(
    user_id: str,
    channel: str,
    message: str,
    session_id: str = None,
    additional_context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """High-level function to process a complete sales conversation"""
    
    # Get orchestrator
    orchestrator = await get_sales_orchestrator()
    
    # Create or get existing state
    state = await create_initial_state(
        user_id=user_id,
        channel=channel,
        session_id=session_id,
        initial_message=message
    )
    
    # Add additional context if provided
    if additional_context:
        for key, value in additional_context.items():
            state.metadata[key] = value
    
    # Process through the graph
    final_state = await orchestrator.process_message(state)
    
    # Return structured response
    return {
        "session_id": final_state.session_id,
        "user_id": final_state.user_id,
        "response": final_state.metadata.get("final_response", ""),
        "current_intent": final_state.current_intent,
        "last_agent": final_state.last_agent,
        "cart_items_count": len(final_state.cart_items),
        "workflow_step": final_state.workflow_step,
        "has_errors": final_state.error_count > 0,
        "conversation_complete": True
    }