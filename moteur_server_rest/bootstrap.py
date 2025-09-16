from dotenv import load_dotenv
import shutil
import signal
import sys
import logging
from logging.handlers import RotatingFileHandler
from moteur_server_rest.workflow_manager import set_docker_available


def init_runtime():
    if len(sys.argv) > 1:
        logging.info("Loading config file %s", sys.argv[1])
        config_file = sys.argv[1]
    else:
        logging.info("Loading default config file %s", ".env")
        config_file = None
    load_dotenv(config_file)
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    set_docker_available(shutil.which("docker") is not None)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler("moteur-server.log", maxBytes=10 * 1024 * 1024, backupCount=5)
        ]
    )

    logger = logging.getLogger("moteur-server")

    def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error(
            "Error not handled : %s", exc_value, exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = log_uncaught_exceptions


def bind_flask_logging(app):
    app.logger.setLevel(logging.INFO)
    app.logger.handlers = logging.getLogger().handlers


