from samples.common.types import (
    AgentCard, 
    AgentCapabilities, 
    AgentSkill, 
    AgentInterface,
    AgentProvider
)

capabilities = AgentCapabilities(streaming=True)

skill_trip_planning = AgentSkill(
    id='trip_planning_sk',
    name='Semantic Kernel Trip Planning',
    description=(
        'Handles comprehensive trip planning, including currency exchanges, itinerary creation, sightseeing, '
        'dining recommendations, and event bookings using Frankfurter API for currency conversions.'
    ),
    tags=['trip', 'planning', 'travel', 'currency', 'semantic-kernel'],
    examples=[
        'Plan a budget-friendly day trip to Seoul including currency exchange.',
        "What's the exchange rate and recommended itinerary for visiting Tokyo?",
    ],
    input_modes=['text/plain'],
    output_modes=['text/plain'],
)

agent_card = AgentCard(
    protocol_version="1.0",
    name='SK Travel Agent',
    description=(
        'Semantic Kernel-based travel agent providing comprehensive trip planning services '
        'including currency exchange and personalized activity planning.'
    ),
    provider=AgentProvider(organization="Semantic Kernel", url="https://example.com"),
    version='1.0.0',
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain'],
    capabilities=capabilities,
    skills=[skill_trip_planning],
    supported_interfaces=[
        AgentInterface(protocol_binding="JSON-RPC", url="http://localhost:7071/api/v1")
    ],
    # For anonymous auth, security can be omitted or explicitly defined if needed.
    # Leaving it empty implies no specific security requirements at the agent level.
    security_schemes={},
    security=[],
)