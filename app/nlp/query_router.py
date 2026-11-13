"""
Query Router Module.
Integrates Intent Classification, Entity Extraction, Conversation Context,
Query Planning, RBAC Validation, and Grounded Response Generation.
"""

from typing import Dict, Any, Optional
from app.config.logging_config import logger
from app.security.access_control import UserContext, AccessDeniedError
from app.nlp.intent_classifier import IntentClassifier
from app.nlp.conversation_context import ConversationContext
from app.nlp.query_planner import QueryPlanner
from app.response.response_generator import ResponseGenerator


class QueryRouter:
    _contexts: Dict[str, ConversationContext] = {}

    @classmethod
    def get_context(cls, user_id: str) -> ConversationContext:
        if user_id not in cls._contexts:
            cls._contexts[user_id] = ConversationContext(session_id=user_id)
        return cls._contexts[user_id]

    @classmethod
    def reset_context(cls, user_id: str):
        if user_id in cls._contexts:
            del cls._contexts[user_id]

    @classmethod
    def process_query(cls, user_context: UserContext, query: str) -> Dict[str, Any]:
        """
        Process a natural language user query with full RBAC enforcement,
        context-aware entity resolution, and deterministic query planning.
        """
        clean_q = query.strip()
        if not clean_q:
            return {
                "intent": "help",
                "response": ResponseGenerator.format_insufficient_info("Please enter a question or command.")
            }

        # 1. Retrieve Conversation Context for this user session
        conv_ctx = cls.get_context(user_context.user_id)

        # 2. Structured Interpretation: Intent Classification & Entity Extraction
        sq = IntentClassifier.classify_to_structured_query(clean_q, default_faculty_id=user_context.faculty_id)

        # 3. Multi-turn Follow-up and Context Resolution
        sq = conv_ctx.resolve_follow_up(clean_q, sq)

        logger.info(
            f"Query mapped: intent={sq.intent.value}, granularity={sq.time_granularity.value}, "
            f"metric={sq.metric.value}, faculty={sq.faculty_id}, user={user_context.username}"
        )

        try:
            # 4. Plan and Execute via QueryPlanner
            result = QueryPlanner.execute_plan(sq, user_context)

            # Ensure structured query is attached for tracing and testing
            result["structured_query"] = sq.model_dump()
            
            # Map intent to string for backwards compatibility with legacy tests
            result["intent"] = IntentClassifier.LEGACY_INTENT_MAP.get(sq.intent, sq.intent.value.lower())

            # 5. Record Turn into Conversation Context
            conv_ctx.add_turn(clean_q, sq, result.get("response", ""))

            return result

        except AccessDeniedError as ade:
            return {
                "intent": sq.intent.value.lower(),
                "error": "ACCESS_DENIED",
                "response": ResponseGenerator.format_access_denied(ade.message),
                "structured_query": sq.model_dump()
            }
        except ValueError as ve:
            return {
                "intent": sq.intent.value.lower(),
                "error": "NOT_FOUND",
                "response": ResponseGenerator.format_insufficient_info(str(ve)),
                "structured_query": sq.model_dump()
            }
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}", exc_info=True)
            return {
                "intent": sq.intent.value.lower(),
                "error": "INTERNAL_ERROR",
                "response": ResponseGenerator.format_insufficient_info("An error occurred while retrieving information."),
                "structured_query": sq.model_dump()
            }
