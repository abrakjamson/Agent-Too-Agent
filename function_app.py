import azure.functions as func
import logging
from samples.agents.semantickernel.agent import SemanticKernelTravelAgent

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="test_http")
def test_http(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
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
        logging.error(f"Error processing /tasks/send request: {e}")
        return func.HttpResponse(
            "An error occurred while processing the request.",
            status_code=500
        )