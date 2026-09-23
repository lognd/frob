import logging

logger = logging.getLogger(__name__)


def handle(request):
    logger.info(f"login attempt for user {request.form['username']}")
