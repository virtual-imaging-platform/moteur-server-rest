from moteur_server_rest.bootstrap import init_runtime, bind_flask_logging

init_runtime()

from moteur_server_rest.routes import app

bind_flask_logging(app)