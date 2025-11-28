import azure.functions as func
import logging
import json
import asyncio
import uuid
from samples.agents.semantickernel.agent import SemanticKernelTravelAgent
from samples.common.types import Message, SendMessageRequest

# Initialize the SemanticKernelTravelAgent
travel_agent = SemanticKernelTravelAgent()

async def main(req: func.HttpRequest) -> func.HttpResponse: # Changed return type implicitly
    logging.info('Python HTTP trigger function processed a request.')

    try:
        req_body = req.get_json() # Revert to get_json()
        logging.info(f"Incoming request body: {json.dumps(req_body, indent=2)}")
        method = req_body.get("method")
        params = req_body.get("params", [{}])[0]
        logging.info(f"Incoming request params: {json.dumps(params, indent=2)}")
        jsonrpc_id = req_body.get("id")

        if method == "SendMessage":
            try:
                send_request = SendMessageRequest.model_validate(params)
                session_id = send_request.message.context_id or str(uuid.uuid4())
                
                result_task = await travel_agent.send_message(send_request.message, session_id)
                
                response_data = result_task.model_dump(by_alias=True, exclude_none=True)
                
                response = {"jsonrpc": "2.0", "result": {"task": response_data}, "id": jsonrpc_id}
                return func.HttpResponse(json.dumps(response), mimetype="application/json")
            except Exception as e:
                logging.error(f"Error processing SendMessage: {e}")
                return func.HttpResponse(json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Invalid params", "data": str(e)},
                    "id": jsonrpc_id
                }), status_code=400, mimetype="application/json")


        elif method == "SendStreamingMessage":
            try:
                send_request = SendMessageRequest.model_validate(params)
                session_id = send_request.message.context_id or str(uuid.uuid4())

                response_stream = travel_agent.stream(send_request.message, session_id)
                
                # Collect all events into a list and join them
                response_data = []
                async for response in response_stream:
                    formatted_event = f"data: {json.dumps(response)}\n\n"
                    response_data.append(formatted_event)

                return func.HttpResponse(
                    "".join(response_data),
                    mimetype="text/event-stream"
                )

            except Exception as e:
                logging.error(f"Error processing SendStreamingMessage: {e}")
                return func.HttpResponse(json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": "Internal server error", "data": str(e)},
                    "id": jsonrpc_id
                }), status_code=500, mimetype="application/json")
        
        else:
            return func.HttpResponse(json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": "Method not found"},
                "id": jsonrpc_id
            }), status_code=404, mimetype="application/json")

    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": "Internal error", "data": str(e)},
            "id": req_body.get("id") if 'req_body' in locals() else None
        }
        return func.HttpResponse(json.dumps(error_response), status_code=500, mimetype="application/json")
