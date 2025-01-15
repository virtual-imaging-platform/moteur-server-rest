from routes import app
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from jvm_utils import shutdown_jvm
from config import get_env_variable
import signal
import sys

# Configurer le logging
log_file = "moteur-server.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Affichage console
        RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)  # Fichier rotatif
    ]
)

logger = logging.getLogger("moteur-server")

#Créer une application Flask
#app = Flask(__name__)
app.logger.setLevel(logging.INFO)
log_file = "moteur-server.log"
app.logger.handlers = logging.getLogger().handlers

# Gestion des signaux pour arrêter proprement la JVM
def handle_shutdown(*args):
    logger.info("Shutting down JVM...")
    shutdown_jvm()
    logger.info("JVM shut down successfully.")
    sys.exit(0)

# Associer les signaux UNIX (SIGINT, SIGTERM) à la fonction de shutdown
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# Exemple de route
@app.route("/")
def index():
    app.logger.info("Root endpoint accessed")
    return "Hello, World!"

# Point d'entrée principal
if __name__ == '__main__':
    try:
        port = int(get_env_variable("SERVER_PORT", "5000", required=False))
        logger.info(f"Starting Flask server on port {port}...")
        app.run(debug=False, host='0.0.0.0', port=port)
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)
    finally:
        handle_shutdown()

