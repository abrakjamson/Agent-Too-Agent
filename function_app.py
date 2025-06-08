import azure.functions as func
import logging
import json
import asyncio  # Import asyncio
import debugpy
from samples.agents.semantickernel.agent import SemanticKernelTravelAgent
from samples.agents.semantickernel.agent_card import agent_card  # Import the existing AgentCard

debugpy.listen(("localhost", 5678))  # Start the debugger on port 5678
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
        message_obj = params.get("message", {})
        jsonrpc_id = req_body.get("id")

        if method == "message/send":
            # TODO error handling
            user_message = next(
                (part["text"] for part in message_obj.get("parts", []) if part.get("kind") == "text"),
                ""
            )

            session_id = params.get("sessionId")
            
            # Construct the Message object per the A2A Protocol:
            # - "role" is set to "user"
            # - "parts" contains a single TextPart carrying the user's text
            # - "messageId" is assigned (here we reuse the JSON-RPC id)
            # - "kind" is fixed as "message"
            message_obj = {
                "role": "user",
                "parts": [
                    {"kind": "text", "text": user_message}
                ],
                "messageId": jsonrpc_id,
                "kind": "message"
            }
            
            # Send the message using an updated travel_agent function.
            # It now returns a Task object or similar response per the new specification.
            result = await travel_agent.send_message(message_obj, session_id)
            response = {"jsonrpc": "2.0", "result": result, "id": jsonrpc_id}
            return func.HttpResponse(json.dumps(response), mimetype="application/json")

        elif method == "message/sendSubscribe":
            # For streaming requests, extract the user message and session ID
            session_id = params.get("sessionId")
            # TODO error handling
            user_message = next(
                (part["text"] for part in message_obj.get("parts", []) if part.get("kind") == "text"),
                ""
            )
            
            # Build the Message object as above
            message_obj = {
                "role": "user",
                "parts": [
                    {"kind": "text", "text": user_message}
                ],
                "messageId": jsonrpc_id,
                "kind": "message"
            }

            async def generate_events():
                # Stream updates from the updated travel_agent method.
                # Each update is expected to be a Task or a Task-status update, per the A2A spec.
                async for task_update in travel_agent.stream_message(message_obj, session_id):
                    event_data = {
                        "jsonrpc": "2.0",
                        "id": jsonrpc_id,
                        "result": {
                            "task": task_update,
                            "final": False
                        }
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                # Send a final event to indicate the end of streaming.
                final_event_data = {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_id,
                    "result": {
                        "final": True
                    }
                }
                yield f"data: {json.dumps(final_event_data)}\n\n"

            return func.HttpResponse(
                generate_events(),
                mimetype="text/event-stream",
            )
        else:
            # Method not found; reply with the standard JSON-RPC error structure.
            response = {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": "Method not found. This server is designed for Agent2Agent 0.2.1"},
                "id": jsonrpc_id
            }
            return func.HttpResponse(json.dumps(response), mimetype="application/json")
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": "Internal error", "data": str(e)},
            "id": req_body.get("id") if 'req_body' in locals() else None
        }
        return func.HttpResponse(json.dumps(error_response), status_code=500, mimetype="application/json")
