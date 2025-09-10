from moteur_server_rest.routes import app
import logging
from logging.handlers import RotatingFileHandler
from moteur_server_rest.config import get_env_variable
import signal
import sys
from dotenv import load_dotenv
import shutil
from moteur_server_rest.workflow_manager import set_docker_available

signal.signal(signal.SIGCHLD, signal.SIG_IGN)

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
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        ]
    )
    
    # On récupère le fichier de configuration
    if len(sys.argv) > 1:
        logging.info("Loading config file %s", sys.argv[1])
        config_file = sys.argv[1]
    else:
        logging.info("Loading default config file %s", ".env")
        config_file = None
    load_dotenv(config_file)

    logger = logging.getLogger("moteur-server")

    app.logger.setLevel(logging.INFO)
    app.logger.handlers = logging.getLogger().handlers

    sys.excepthook = log_uncaught_exceptions

    # Détection de Docker
    set_docker_available(shutil.which("docker") is not None)

    try:
        port = int(get_env_variable("SERVER_PORT", "5000", required=False))
        logger.info(f"Launching Flask server on port {port}...")
        app.run(debug=False, host='0.0.0.0', port=port)
    except ValueError as ve:
        logger.error("Error converting the port : %s", ve, exc_info=True)
    except Exception as e:
        logger.error("Unexpected error : %s", e, exc_info=True)
