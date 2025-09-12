from moteur_server_rest.routes import app
import logging
from moteur_server_rest.config import get_env_variable
from moteur_server_rest.bootstrap import init_runtime, bind_flask_logging

if __name__ == '__main__':
    init_runtime()
    
    logger = logging.getLogger("moteur-server")

    bind_flask_logging(app)

    try:
        port = int(get_env_variable("SERVER_PORT", "5000", required=False))
        logger.info(f"Launching Flask server on port {port}...")
        app.run(debug=False, host='0.0.0.0', port=port)
    except ValueError as ve:
        logger.error("Error converting the port : %s", ve, exc_info=True)
    except Exception as e:
        logger.error("Unexpected error : %s", e, exc_info=True)
