import azure.functions as func
import logging
import json
from samples.agents.semantickernel.agent import SemanticKernelTravelAgent
from samples.agents.semantickernel.agent_card import agent_card  # Import the existing AgentCard

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route=".well-known/agent.json")
def get_agent_card(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Serving the AgentCard JSON.')
    try:
        # Use the existing agent_card from agent_card.py
        agent_card_json = json.dumps(agent_card, default=lambda o: o.__dict__)
        return func.HttpResponse(agent_card_json, mimetype='application/json')
    except Exception as e:
        logging.error(f"Error generating AgentCard JSON: {e}")
        return func.HttpResponse(
            "Error generating AgentCard JSON.",
            status_code=500
        )

@app.route(route="test_http")
def test_http(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
            logging.info(f"Request Body: {req_body}")
        except ValueError:
            logging.error("Invalid JSON in request body.")
            return func.HttpResponse(
                "Invalid JSON in request body.",
                status_code=400
            )
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}!")
    else:
        return func.HttpResponse(
            "Please pass a name on the query string or in the request body",
            status_code=400
        )

@app.route(route="tasks/send", methods=["POST"])
async def send_task(req: func.HttpRequest) -> func.HttpResponse:
    """Handle the /tasks/send function for sending tasks."""
    logging.info('Processing /tasks/send request.')

    try:
        # Log request headers
        logging.info(f"Request Headers: {req.headers}")

        # Log request body
        try:
            req_body = req.get_json()  # Remove 'await' as get_json() is synchronous
            logging.info(f"Request Body: {req_body}")
        except ValueError:
            logging.error("Invalid JSON in request body.")
            return func.HttpResponse(
                "Invalid JSON in request body.",
                status_code=400
            )

        # Extract user input and session ID from the request
        user_input = req_body.get('user_input')
        session_id = req_body.get('session_id')

        if not user_input or not session_id:
            logging.warning(f"Missing parameters: user_input={user_input}, session_id={session_id}")
            return func.HttpResponse(
                f"{user_input} {session_id} did not find user_input or session_id in the request.",
                status_code=400
            )

        # Initialize the Semantic Kernel Travel Agent
        travel_agent = SemanticKernelTravelAgent()

        # Invoke the agent to handle the task
        response = await travel_agent.invoke(user_input, session_id)
        
        # Convert the response to JSON string
        if isinstance(response, dict):
            response_json = json.dumps(response)
        else:
            response_json = json.dumps({"message": str(response)})

        # Log the response for debugging
        logging.info(f"Agent response: {response_json}")

        # Return the response as JSON
        return func.HttpResponse(
            body=response_json,
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"(function_app) An error occurred: {e}")
        error_response = json.dumps({
            "error": "An internal error occurred",
            "details": str(e)
        })
        return func.HttpResponse(
            body=error_response,
            status_code=500,
            mimetype="application/json"
        )