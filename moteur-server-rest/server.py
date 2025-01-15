from routes import app
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from jvm_utils import shutdown_jvm
from config import get_env_variable
import signal
import sys
import traceback

# Configurer le logging
log_file = "moteur-server.log"
logging.basicConfig(
    level=logging.DEBUG,  # Inclut debug et niveaux supérieurs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Affichage console
        RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)  # Fichier rotatif
    ]
)

logger = logging.getLogger("moteur-server")

# Intégration des logs Flask avec Python logging
app.logger.setLevel(logging.INFO)
app.logger.handlers = logging.getLogger().handlers

# Gestion des signaux pour arrêter proprement la JVM
def handle_shutdown(*args):
    logger.info("Signal reçu, arrêt de la JVM...")
    try:
        shutdown_jvm()
        logger.info("JVM arrêtée avec succès.")
    except Exception as e:
        logger.critical("Erreur lors de l'arrêt de la JVM : %s", e, exc_info=True)
    finally:
        sys.exit(0)

# Associer les signaux UNIX (SIGINT, SIGTERM) à la fonction de shutdown
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# Exemple de route
@app.route("/")
def index():
    app.logger.debug("Appel du point d'accès racine")
    return "Hello, World!"

# Capture globale des exceptions non gérées
def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Ne pas enregistrer les interruptions clavier
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error(
        "Exception non gérée capturée : %s", exc_value, exc_info=(exc_type, exc_value, exc_traceback)
    )

sys.excepthook = log_uncaught_exceptions

# Point d'entrée principal
if __name__ == '__main__':
    try:
        port = int(get_env_variable("SERVER_PORT", "5000", required=False))
        logger.info(f"Lancement du serveur Flask sur le port {port}...")
        app.run(debug=False, host='0.0.0.0', port=port)
    except ValueError as ve:
        logger.error("Erreur de conversion du port : %s", ve, exc_info=True)
    except Exception as e:
        logger.error("Une erreur inattendue est survenue : %s", e, exc_info=True)
    finally:
        handle_shutdown()
