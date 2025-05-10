import logging
import azure.functions as func
from samples.agents.semantickernel.agent import SemanticKernelTravelAgent

logger = logging.getLogger(__name__)

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Handle the /tasks/send function for sending tasks.

    Args:
        req (func.HttpRequest): The HTTP request object.

    Returns:
        func.HttpResponse: The HTTP response object.
    """
    try:
        # Extract user input and session ID from the request
        user_input = req.params.get('user_input')
        session_id = req.params.get('session_id')

        if not user_input or not session_id:
            return func.HttpResponse(
                "Missing user_input or session_id in the request.",
                status_code=400
            )

        # Initialize the Semantic Kernel Travel Agent
        travel_agent = SemanticKernelTravelAgent()

        # Invoke the agent to handle the task
        response = await travel_agent.invoke(user_input, session_id)

        # Return the response as JSON
        return func.HttpResponse(
            body=response,
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error processing /tasks/send request: {e}")
        return func.HttpResponse(
            "An error occurred while processing the request.",
            status_code=500
        )