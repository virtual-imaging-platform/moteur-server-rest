import os

def get_env_variable(var_name, default=None, required=True):
    """Helper function to get environment variables with optional default and required flag."""
    value = os.getenv(var_name, default)
    if required and value is None:
        raise EnvironmentError(f"{var_name} is not defined and is required.")
    return value
