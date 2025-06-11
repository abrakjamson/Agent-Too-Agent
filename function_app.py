import azure.functions as func
import logging
import json
import asyncio
import debugpy
from starlette.responses import StreamingResponse  # (Unused, but you can remove if not needed)
from samples.agents.semantickernel.agent import SemanticKernelTravelAgent
from samples.agents.semantickernel.agent_card import agent_card  # Existing AgentCard

# Start the debugger on port 5678
debugpy.listen(("localhost", 5678))  
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Initialize the SemanticKernelTravelAgent
travel_agent = SemanticKernelTravelAgent()

def sync_generator(async_gen):
    loop = asyncio.new_event_loop()
    while True:
        try:
            chunk = loop.run_until_complete(async_gen.__anext__())
            yield chunk.encode("utf-8")  # Convert each chunk to bytes
        except StopAsyncIteration:
            break
    loop.close()

async def generate_sse_events(response_stream):
    """
    Async generator that reads responses from the travel agent's stream,
    formats each one as an SSE event (with the 'data:' prefix and two newlines),
    and yields the event as a UTF-8 encoded byte string.
    """
    async for response in response_stream:
        formatted_event = f"data: {json.dumps(response)}\n\n"  # Ensure SSE format
        yield formatted_event.encode("utf-8")  # Send chunks as bytes
        await asyncio.sleep(0.1)  # Small delay to allow flushing

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
            # TODO: Add error handling as needed
            user_message = next(
                (part["text"] for part in message_obj.get("parts", []) if part.get("kind") == "text"),
                ""
            )

            session_id = params.get("sessionId")
            
            # Construct the Message object per the A2A protocol
            message_obj = {
                "role": "user",
                "parts": [
                    {"kind": "text", "text": user_message}
                ],
                "messageId": jsonrpc_id,
                "kind": "message"
            }
            
            # Send the message using the travel_agent's send_message method.
            result = await travel_agent.send_message(message_obj, session_id)
            response = {"jsonrpc": "2.0", "result": result, "id": jsonrpc_id}
            return func.HttpResponse(json.dumps(response), mimetype="application/json")

        elif method == "message/sendSubscribe":
            try:
                req_body = req.get_json()
                params = req_body.get("params", {})
                session_id = params.get("sessionId")
                message_obj = params.get("message", {})

                if not message_obj or not session_id:
                    logging.error("Missing message or sessionId in request.")
                    return func.HttpResponse(
                        "(function_app) Missing message or sessionId in request.",
                        status_code=400
                    )

                # Obtain the response stream from the travel agent
                response_stream = travel_agent.stream(message_obj, session_id)

                # Collect async generator results into a list instead of awaiting it directly
                response_data = []
                async for response in response_stream:
                    response_data.append(f"data: {json.dumps(response)}\n\n")

                # This actually joins all the intermediate and final response into a single string
                # it isn't a proper implementation of SSE
                return func.HttpResponse("".join(response_data), mimetype="text/event-stream")

            except Exception as e:
                logging.error(f"Error processing sendSubscribe: {str(e)}")
                return func.HttpResponse(
                    json.dumps({"error": "Internal server error", "details": str(e)}),
                    status_code=500,
                    mimetype="application/json"
                )
        
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": "Internal error", "data": str(e)},
            "id": req_body.get("id") if 'req_body' in locals() else None
        }
        return func.HttpResponse(json.dumps(error_response), status_code=500, mimetype="application/json")