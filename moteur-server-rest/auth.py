from functools import wraps
from flask import request, jsonify
from config import get_env_variable

def require_password(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_password = request.headers.get('Authorization')
        correct_password = get_env_variable("SERVER_PASSWORD", required=True)
        
        if not provided_password or provided_password != correct_password:
            print("Unauthorized access")
            return jsonify({"error": "Unauthorized access"}), 401
        
        return f(*args, **kwargs)
    return decorated_function