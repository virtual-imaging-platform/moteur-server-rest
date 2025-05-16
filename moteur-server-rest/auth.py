from flask_httpauth import HTTPBasicAuth
from config import get_env_variable

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(_, password):
    return password == get_env_variable("SERVER_PASSWORD", required=True)