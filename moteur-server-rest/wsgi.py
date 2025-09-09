from dotenv import load_dotenv
import shutil
import signal
import sys
import logging
from logging.handlers import RotatingFileHandler
from workflow_manager import set_docker_available

"""Load environment variables, ignore SIGCHLD, set Docker availability and configure logging.
Same as server.py but without the Flask app. Adapted for WSGI."""

# Load environment variables
load_dotenv()
signal.signal(signal.SIGCHLD, signal.SIG_IGN)
set_docker_available(shutil.which("docker") is not None)

# Configure logging (cf. server.py)
log_file = "moteur-server.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
    ]
)

logger = logging.getLogger("moteur-server")

# Manage uncaught exceptions
def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Do not log KeyboardInterrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error(
        "Error not handled : %s", exc_value, exc_info=(exc_type, exc_value, exc_traceback)
    )

sys.excepthook = log_uncaught_exceptions

from routes import app

# Configure Flask logger
app.logger.setLevel(logging.INFO)
app.logger.handlers = logging.getLogger().handlers