"""
LangGraph + Mistral Sales Agent System

A sophisticated sales agent orchestration system built with LangGraph and Mistral LLM.
"""

__version__ = "1.0.0"
__author__ = "LangGraph Sales Agent Team"
__description__ = "Intelligent sales agent system for e-commerce conversations"

# Import main components for easy access
from .agents.state import ConversationState
from .agents.sales_agent import process_sales_conversation, get_sales_orchestrator
from .llm.mistral_client import get_mistral_client
from .tools.database_tools import initialize_database

__all__ = [
    "ConversationState",
    "process_sales_conversation", 
    "get_sales_orchestrator",
    "get_mistral_client",
    "initialize_database"
]