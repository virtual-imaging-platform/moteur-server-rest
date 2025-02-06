import os
from dotenv import load_dotenv

load_dotenv()

def get_env_variable(var_name, default=None, required=True):
    """Helper function to get environment variables with optional default and required flag."""
    value = os.getenv(var_name, default)
    if required and value is None:
        raise EnvironmentError(f"{var_name} is not defined and is required.")
    return value

def get_workflow_filename():
    """Helper function to get workflow file name"""
    return os.getenv("WORKFLOW_FILE_NAME", "workflow.json")
