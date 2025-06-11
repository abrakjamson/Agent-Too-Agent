import logging
import os
import uuid
import datetime
from datetime import timezone
import json

from collections.abc import AsyncIterable
from typing import TYPE_CHECKING, Annotated, Any, Literal

import httpx

from dotenv import load_dotenv
from pydantic import BaseModel
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.contents import (
    FunctionCallContent,
    FunctionResultContent,
    StreamingChatMessageContent,
    StreamingTextContent,
)
from semantic_kernel.functions import kernel_function
from semantic_kernel.functions.kernel_arguments import KernelArguments


if TYPE_CHECKING:
    from semantic_kernel.contents import ChatMessageContent

logger = logging.getLogger(__name__)

load_dotenv()

# region Plugin


class CurrencyPlugin:
    """A simple currency plugin that leverages Frankfurter for exchange rates.

    The Plugin is used by the `currency_exchange_agent`.
    """

    @kernel_function(
        description='Retrieves exchange rate between currency_from and currency_to using Frankfurter API'
    )
    def get_exchange_rate(
        self,
        currency_from: Annotated[
            str, 'Currency code to convert from, e.g. USD'
        ],
        currency_to: Annotated[
            str, 'Currency code to convert to, e.g. EUR or INR'
        ],
        date: Annotated[str, "Date or 'latest'"] = 'latest',
    ) -> str:
        try:
            response = httpx.get(
                f'https://api.frankfurter.app/{date}',
                params={'from': currency_from, 'to': currency_to},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            if 'rates' not in data or currency_to not in data['rates']:
                return f'Could not retrieve rate for {currency_from} to {currency_to}'
            rate = data['rates'][currency_to]
            return f'1 {currency_from} = {rate} {currency_to}'
        except Exception as e:
            return f'Currency API call failed: {e!s}'


# endregion

# region Response Format


class ResponseFormat(BaseModel):
    """A Response Format model to direct how the model should respond."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


# endregion

# region Semantic Kernel Agent


class SemanticKernelTravelAgent:
    """Wraps Semantic Kernel-based agents to handle Travel related tasks."""

    agent: ChatCompletionAgent
    thread: ChatHistoryAgentThread = None
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY', None)
        if not api_key:
            raise ValueError('OPENAI_API_KEY environment variable not set.')

        model_id = os.getenv('OPENAI_CHAT_MODEL_ID', 'gpt-4.1')

        # Define a CurrencyExchangeAgent to handle currency-related tasks
        currency_exchange_agent = ChatCompletionAgent(
            service=OpenAIChatCompletion(
                api_key=api_key,
                ai_model_id=model_id,
            ),
            name='CurrencyExchangeAgent',
            instructions=(
                'You specialize in handling currency-related requests from travelers. '
                'This includes providing current exchange rates, converting amounts between different currencies, '
                'explaining fees or charges related to currency exchange, and giving advice on the best practices for exchanging currency. '
                'Your goal is to assist travelers promptly and accurately with all currency-related questions.'
            ),
            plugins=[CurrencyPlugin()],
        )

        # Define an ActivityPlannerAgent to handle activity-related tasks
        activity_planner_agent = ChatCompletionAgent(
            service=OpenAIChatCompletion(
                api_key=api_key,
                ai_model_id=model_id,
            ),
            name='ActivityPlannerAgent',
            instructions=(
                'You specialize in planning and recommending activities for travelers. '
                'This includes suggesting sightseeing options, local events, dining recommendations, '
                'booking tickets for attractions, advising on travel itineraries, and ensuring activities '
                'align with traveler preferences and schedule. '
                'Your goal is to create enjoyable and personalized experiences for travelers.'
            ),
        )

        # Define the main TravelManagerAgent to delegate tasks to the appropriate agents
        self.agent = ChatCompletionAgent(
            service=OpenAIChatCompletion(
                api_key=api_key,
                ai_model_id=model_id,
            ),
            name='TravelManagerAgent',
            instructions=(
                "Your role is to carefully analyze the traveler's request and forward it to the appropriate agent based on the "
                'specific details of the query. '
                'Forward any requests involving monetary amounts, currency exchange rates, currency conversions, fees related '
                'to currency exchange, financial transactions, or payment methods to the CurrencyExchangeAgent. '
                'Forward requests related to planning activities, sightseeing recommendations, dining suggestions, event '
                'booking, itinerary creation, or any experiential aspects of travel that do not explicitly involve monetary '
                'transactions to the ActivityPlannerAgent. '
                'Your primary goal is precise and efficient delegation to ensure travelers receive accurate and specialized '
                'assistance promptly.'
            ),
            plugins=[currency_exchange_agent, activity_planner_agent],
            arguments=KernelArguments(
                settings=OpenAIChatPromptExecutionSettings(
                    response_format=ResponseFormat,
                )
            ),
        )

    async def send_message(self, message: dict, session_id: str) -> dict[str, Any]:
        """
        Handle synchronous messages (akin to message/send).

        Args:
            message (dict): A structured Message object following the A2A specification.
                            Expected to include a "role", a list of "parts" (e.g., a text part),
                            a unique message ID in "messageId", and a fixed "kind" ("message").
            session_id (str): Unique identifier for the session.

        Returns:
            dict: A Task object (or equivalent result) that encapsulates
                the agent's response, including content, status, and any task-related metadata.
        """
        # Ensure the session/thread is established.
        # await self._ensure_thread_exists(session_id)
        
        # Extract the text content from the message parts.
        # (This example assumes the first 'text' part is the user input.)
        user_text = ""
        for part in message.get("parts", []):
            if part.get("kind") == "text":
                user_text = part.get("text", "")
                break

        # Use the existing underlying mechanism to get a response.
        response = await self.agent.get_response(
            messages=user_text,
            thread=self.thread,
        )
        
        # Convert the raw response content into a Message structure in line with the A2A spec.
        return self._get_agent_response(response.content)

    def _get_agent_response(self, content: 'ChatMessageContent') -> dict[str, Any]:
        """
        Converts the agent's response content into a structured A2A Message format.

        Args:
            content (ChatMessageContent): The content returned by the agent.

        Returns:
            dict: A structured Message object.
        """
        innerContent = content.content if hasattr(content, 'content') else content
        content_object = json.loads(innerContent) if isinstance(innerContent, str) else innerContent
        if isinstance(content_object, dict) and 'message' in content_object:
            agent_response = content_object['message']
        return {
            "role": "agent",
            "parts": [
                {
                    "kind": "text",
                    "text": agent_response
                }
            ],
            "messageId": str(uuid.uuid4()),
            "kind": "message"
        }

    async def stream(self, message_obj: dict, session_id: str) -> AsyncIterable[dict[str, any]]:
        """
        Streams incremental updates for messages/sendSubscribe.
        Yields structured task updates that follow the A2A protocol in a combined function.
        
        Args:
        message_obj (dict): Structured message object from the request.
        session_id (str): Unique session ID.
        
        Yields:
        dict: A structured A2A task update (incremental or final).
        """
        chunks: list[StreamingChatMessageContent] = []

        # Extract the user text from the message parts.
        user_input = next(
            (part.get("text", "") for part in message_obj.get("parts", []) if part.get("kind") == "text"),
            ""
        )

        tool_call_in_progress = False
        message_in_progress = False

        # Stream incremental response chunks from the agent.
        async for response_chunk in self.agent.invoke_stream(
            messages=user_input,
            thread=self.thread,
        ):
            if any(
                isinstance(item, (FunctionCallContent, FunctionResultContent))
                for item in response_chunk.items
            ):
                if not tool_call_in_progress:
                    yield {
                        "task": {
                            "id": message_obj.get("messageId"),
                            "contextId": session_id,
                            "status": "working",
                            "message": {
                                "role": "agent",
                                "parts": [{
                                    "kind": "text", 
                                    "text": "Processing the trip plan (with plugins)..."
                                }],
                                "messageId": str(uuid.uuid4()),
                                "kind": "message"
                            }
                        }
                    }
                    tool_call_in_progress = True

            elif any(
                isinstance(item, StreamingTextContent)
                for item in response_chunk.items
            ):
                if not message_in_progress:
                    yield {
                        "task": {
                            "id": message_obj.get("messageId"),
                            "contextId": session_id,
                            "status": "working",
                            "message": {
                                "role": "agent",
                                "parts": [{
                                    "kind": "text", 
                                    "text": "Building the trip plan..."
                                }],
                                "messageId": str(uuid.uuid4()),
                                "kind": "message"
                            }
                        }
                    }
                    message_in_progress = True

                chunks.append(response_chunk.message)

        # Aggregate the chunks to form the complete message.
        if chunks:
            full_message = sum(chunks[1:], chunks[0])
        else:
            full_message = ""

        # Inline: transform final message into a structured task update.
        # Attempt to validate and parse the agent's final message.
        try:
            if hasattr(full_message, "content"):
                structured_response = ResponseFormat.model_validate_json(full_message.content)
            else:
                structured_response = ResponseFormat.model_validate_json(str(full_message))
        except Exception:
            structured_response = None

        # Generate a timestamp in ISO 8601 format.
        timestamp = datetime.datetime.now(timezone.utc).isoformat()

        if structured_response and isinstance(structured_response, ResponseFormat):
            final_text = structured_response.message
            # Use the response status, mapping "completed" as expected.
            final_state = "completed" if structured_response.status == "completed" else structured_response.status
        else:
            final_text = "We are unable to process your request at the moment. Please try again."
            final_state = "error"

        # Yield final update in structured task format.
        yield {
            "task": {
                "id": message_obj.get("messageId"),
                "contextId": session_id,
                "status": final_state,
                "timestamp": timestamp,
                "message": {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": final_text}],
                    "messageId": str(uuid.uuid4()),
                    "kind": "message"
                }
            }
        }
# endregion
