import azure.functions as func
import logging
import json
from samples.agents.semantickernel.agent_card import agent_card

async def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Serving the AgentCard JSON.')
    try:
        modified_card = agent_card.model_copy(deep=True)
        base_url = req.url.rsplit('/.well-known/agent-card.json', 1)[0]
        
        if not modified_card.supported_interfaces:
            modified_card.supported_interfaces = []
        
        modified_card.supported_interfaces = [{
            "protocolBinding": "JSON-RPC",
            "url": f"{base_url}/v1"
        }]

        modified_card.url = f"{base_url}/v1"

        agent_card_json = modified_card.model_dump_json(by_alias=True, exclude_none=True)
        return func.HttpResponse(agent_card_json, mimetype='application/json')
    except Exception as e:
        logging.error(f"Error generating AgentCard JSON: {e}")
        return func.HttpResponse("Error generating AgentCard JSON.", status_code=500)
