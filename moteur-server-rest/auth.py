from flask_httpauth import HTTPBasicAuth
from config import get_env_variable

SERVER_PASSWORD = get_env_variable("SERVER_PASSWORD", required=True)
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(_, password):
    return password == SERVER_PASSWORD