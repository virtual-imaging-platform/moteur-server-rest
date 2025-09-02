from dotenv import load_dotenv
import shutil
from workflow_manager import set_docker_available

load_dotenv()
set_docker_available(shutil.which("docker") is not None)

from routes import app