import azure.functions as func
import logging
import json
import asyncio  # Import asyncio
from samples.agents.semantickernel.agent import SemanticKernelTravelAgent
from samples.agents.semantickernel.agent_card import agent_card  # Import the existing AgentCard

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Initialize the SemanticKernelTravelAgent
travel_agent = SemanticKernelTravelAgent()

@app.route(route=".well-known/agent.json")
def get_agent_card(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Serving the AgentCard JSON.')
    try:
        # Override the URL based on the request
        modified_card = agent_card.model_copy()
        base_url = str(req.url).rsplit('/.well-known/agent.json', 1)[0]
        modified_card.url = base_url + '/'
        
        agent_card_json = json.dumps(modified_card, default=lambda o: o.__dict__)
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

@app.route(route="jsonrpc", methods=["POST"])
async def jsonrpc_handler(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        method = req_body.get("method")
        params = req_body.get("params", {})
        request_id = req_body.get("id")

        if method == "send_task":
            user_input = params.get("user_input")
            session_id = params.get("session_id")
            result = await travel_agent.invoke(user_input, session_id)
            response = {"jsonrpc": "2.0", "result": result, "id": request_id}
            return func.HttpResponse(json.dumps(response), mimetype="application/json")

        elif method == "send_subscribe":
            user_input = params.get("user_input")
            session_id = params.get("session_id")
            
            async def generate_events():
                async for response_item in travel_agent.stream(user_input, session_id):
                    # Wrap each item in the stream as a TaskStatusUpdateEvent
                    event_data = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "id": request_id,
                            "status": {"state": "working", "message": {"role": "agent", "parts": [{"type": "text", "text": str(response_item)}]}},  # Adjust as needed
                            "final": False  # Set to True for the last event
                        }
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                # Send a final event to signal completion
                final_event_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "id": request_id,
                        "status": {"state": "completed", "message": {"role": "agent", "parts": [{"type": "text", "text": "Streaming complete."}]}},
                        "final": True
                    }
                }
                yield f"data: {json.dumps(final_event_data)}\n\n"

            return func.HttpResponse(
                generate_events(),
                mimetype="text/event-stream",
            )
        else:
            response = {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": "Method not found"},
                "id": request_id
            }
            return func.HttpResponse(json.dumps(response), mimetype="application/json")
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": "Internal error", "data": str(e)},
            "id": req_body.get("id") if 'req_body' in locals() else None
        }
        return func.HttpResponse(json.dumps(error_response), status_code=500, mimetype="application/json")