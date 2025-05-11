import logging

import click

from samples.agents.semantickernel.task_manager import TaskManager
from samples.common.server import A2AServer
from samples.common.utils.push_notification_auth import PushNotificationSenderAuth
from samples.agents.semantickernel.agent_card import agent_card  # Import the AgentCard from the new module
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


@click.command()
@click.option('--host', default='localhost')
@click.option('--port', default=10020)
def main(host, port):
    """Starts the Semantic Kernel Agent server using A2A."""

    # Prepare push notification system
    notification_sender_auth = PushNotificationSenderAuth()
    notification_sender_auth.generate_jwk()

    # Create the server
    task_manager = TaskManager(
        notification_sender_auth=notification_sender_auth
    )
    server = A2AServer(
        agent_card=agent_card,  # Use the imported AgentCard
        task_manager=task_manager,
        host=host,
        port=port
    )
    server.app.add_route(
        '/.well-known/jwks.json',
        notification_sender_auth.handle_jwks_endpoint,
        methods=['GET'],
    )

    logger.info(f'Starting the Semantic Kernel agent server on {host}:{port}')
    server.start()


if __name__ == '__main__':
    main()
