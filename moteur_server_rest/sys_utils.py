import logging
import subprocess
from moteur_server_rest.config import get_env_variable, get_ram_per_workflow
from moteur_server_rest.workflow_manager import get_number_running_workflows

logger = logging.getLogger(__name__)

def get_max_ram() -> int:
    grep = subprocess.run(
        ["grep", "MemTotal", "/proc/meminfo"],
        capture_output=True,
        check=True,
    )
    output = grep.stdout.decode().strip()
    value = int(output.split()[1])
    # convert result into mB
    return int(value / 1000)

def get_allowed_ram() -> int:
    total_ram = get_max_ram()
    allowed_percentage = int(get_env_variable("RAM_ALLOWED_PERCENTAGE", "80", required=False))

    return total_ram * (allowed_percentage / 100)

def is_enough_ram() -> bool:
    ram_per_worflow = get_ram_per_workflow()

    running = get_number_running_workflows()
    used = running * ram_per_worflow
    allowed = get_allowed_ram()
    result = used + ram_per_worflow < allowed

    if not result:
        logger.warning(f"RAM limit reached: {used}/{allowed}mb ({running} workflows)")
    return result
