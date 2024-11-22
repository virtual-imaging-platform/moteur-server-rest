from routes import app
from config import get_env_variable
from jvm_utils import shutdown_jvm

def handle_shutdown(*args):
    print("Shutting down JVM...")
    shutdown_jvm()

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=get_env_variable("SERVER_PORT", "5000", required=False))
    finally:
        handle_shutdown()
