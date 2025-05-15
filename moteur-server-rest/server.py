from routes import app
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from config import get_env_variable
import signal
import sys
import traceback


def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Ne pas enregistrer les interruptions clavier
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error(
        "Error not handled : %s", exc_value, exc_info=(exc_type, exc_value, exc_traceback)
    )

if __name__ == '__main__':
    log_file = "moteur-server.log"
    # Logging config
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        ]
    )

    logger = logging.getLogger("moteur-server")

    app.logger.setLevel(logging.INFO)
    app.logger.handlers = logging.getLogger().handlers

    sys.excepthook = log_uncaught_exceptions

    try:
        port = int(get_env_variable("SERVER_PORT", "5000", required=False))
        logger.info(f"Launching Flask server on port {port}...")
        app.run(debug=False, host='0.0.0.0', port=port)
    except ValueError as ve:
        logger.error("Error converting the port : %s", ve, exc_info=True)
    except Exception as e:
        logger.error("Unexpected error : %s", e, exc_info=True)
