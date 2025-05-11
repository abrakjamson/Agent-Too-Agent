# filepath: c:\Users\abram\Documents\a2a\Agent-Too-Agent\samples\agents\semantickernel\agent_card.py
from samples.common.types import AgentCapabilities, AgentCard, AgentSkill

capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
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
)

agent_card = AgentCard(
    name='SK Travel Agent',
    description=(
        'Semantic Kernel-based travel agent providing comprehensive trip planning services '
        'including currency exchange and personalized activity planning.'
    ),
    url='http://localhost:10020/',  # Update this URL as needed
    version='1.0.0',
    defaultInputModes=['text'],
    defaultOutputModes=['text'],
    capabilities=capabilities,
    skills=[skill_trip_planning],
)