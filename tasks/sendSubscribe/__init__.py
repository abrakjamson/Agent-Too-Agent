import azure.functions as func
import logging
import json
from samples.agents.semantickernel.agent import SemanticKernelTravelAgent

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Initialize the SemanticKernelTravelAgent
travel_agent = SemanticKernelTravelAgent()

@app.route(route="tasks/sendSubscribe")
async def send_subscribe(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing sendSubscribe request.')

    try:
        # Parse the request body
        req_body = req.get_json()
        user_input = req_body.get('user_input')
        session_id = req_body.get('session_id')

        if not user_input or not session_id:
            logging.error("Missing user_input or session_id in request.")
            return func.HttpResponse(
                "Missing user_input or session_id in request.",
                status_code=400
            )

        # Stream the response using the SemanticKernelTravelAgent
        response_stream = travel_agent.stream(user_input, session_id)

        # Collect and yield responses
        response_data = []
        async for response in response_stream:
            response_data.append(response)

        # Return the collected responses as JSON
        return func.HttpResponse(
            json.dumps(response_data),
            mimetype='application/json'
        )

    except Exception as e:
        logging.error(f"Error processing sendSubscribe request: {e}")
        return func.HttpResponse(
            "Error processing request.",
            status_code=500
        )