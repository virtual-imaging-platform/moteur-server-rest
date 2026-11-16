import json
import logging
import os
import shutil
import subprocess
import shlex
import threading
from moteur_server_rest.jvm_utils import load_classpath
from moteur_server_rest.config import get_env_variable, get_ram_per_workflow
from moteur_server_rest.config import get_workflow_filename

logger = logging.getLogger(__name__)

DOCKER_AVAILABLE = False

def set_docker_available(status: bool):
    global DOCKER_AVAILABLE
    DOCKER_AVAILABLE = status
    logger.info(f"Docker available: {DOCKER_AVAILABLE}")

def get_number_running_workflows() -> int:
    user = get_env_variable('USER', required=True)
    moteur_process_class = get_env_variable('MOTEUR_MAIN_CLASS', required=True)
    result = subprocess.run(
        ["pgrep", "-u", user, "-f", f"{moteur_process_class}.*"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False
    )
    output = result.stdout.decode().strip()
    return len(output.splitlines()) if output else 0

def find_process_pids(workflow_id):
    user = get_env_variable('USER', required=True)
    moteur_process_class = get_env_variable('MOTEUR_MAIN_CLASS', required=True)
    result = subprocess.run(
        ["pgrep", "-u", user, "-f", f"{moteur_process_class}.*{workflow_id}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False
    )
    output = result.stdout.decode().strip()
    return output.splitlines() if output else []

def launch_workflow(base_path: str, proxy_file: str = None) -> int:
    """
    Lance un workflow Java dans un nouveau session (start_new_session),
    persiste son PID dans base_path/workflow.pid, et crée les logs.
    Retourne le PID du processus Java.
    """
    workflow_id = os.path.basename(base_path)
    os.environ['CLASSPATH'] = load_classpath()

    # Récupération des variables d'env
    java_cmd_tpl    = get_env_variable('JAVA_COMMAND',    required=True)
    java_home       = get_env_variable('JAVA_HOME',       required=True)
    moteur_home     = get_env_variable('MOTEUR_HOME',     required=True)
    conf_location   = get_env_variable('CONF_LOCATION',   required=True)
    moteur_main_cls = get_env_variable('MOTEUR_MAIN_CLASS', required=True)
    ram = get_ram_per_workflow()

    wf_file   = os.path.join(base_path, get_workflow_filename())
    input_file  = os.path.join(base_path, 'inputs.json')
    proxy_arg = f'-DX509_USER_PROXY={proxy_file}' if proxy_file else ''

    # Construction de la commande
    cmd = shlex.split(java_cmd_tpl.format(
        JAVA_HOME=java_home,
        RAM_WORKFLOW=ram,
        CONF_LOCATION=conf_location,
        PROXY_FILE=proxy_arg,
        MOTEUR_HOME=moteur_home,
        MOTEUR_MAIN_CLASS=moteur_main_cls,
        workflow_id=workflow_id,
        workflow_file_path=wf_file,
        inputs_file_path=input_file
    ))

    out_path = os.path.join(base_path, 'process.out')
    err_path = os.path.join(base_path, 'process.err')

    with open(out_path, 'w') as stdout_f, open(err_path, 'w') as stderr_f:
        process = subprocess.Popen(
            cmd,
            stdout=stdout_f,
            stderr=stderr_f,
            cwd=base_path,
            start_new_session=True
        )

    # Persistance du PID
    pid_file = os.path.join(base_path, 'workflow.pid')
    with open(pid_file, 'w') as f:
        f.write(str(process.pid))
    return process.pid

def _kill_workflow(workflow_id, hard_kill):
    """Kill a specific workflow and update its status in the database."""
    
    signal = 9 if hard_kill else 15
    try:
        pids = find_process_pids(workflow_id)

        if not pids:
            if not hard_kill:
                logger.warning("No matching process found.")
            return

        if len(pids) > 1:
            logger.error(f"Multiple processes found for workflow_id: {workflow_id}.")
            raise RuntimeError(f"Multiple processes found for workflow_id: {workflow_id}.")

        pid = int(pids[0])
        try:
            pgid = os.getpgid(pid)
        except ProcessLookupError:
            logger.warning(f"Process {pid} already gone.")
            return

        os.killpg(pgid, signal)
        logger.info(f"Process group {pgid} killed with signal {signal}.")

        if DOCKER_AVAILABLE:
            result = subprocess.run(
                ["docker", "ps", "-q", "--filter", f"name={workflow_id}*"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            if result.stdout.decode().strip():
                container_ids = result.stdout.decode().strip().split('\n')
                for container_id in container_ids:
                    if container_id.strip():
                        os.system(f"docker kill {container_id.strip()}")
                        logger.info(f"Container {container_id.strip()} killed.")
    
    except subprocess.CalledProcessError as e:
        logger.warning(f"Error finding or killing process: {e}")

def kill_workflow(workflow_id):
    """Trigger the `kill_workflow(workflow_id)` method after a specific delay."""
    delay = get_env_variable("KILL_DELAY", 120, False)

    try:
        _kill_workflow(workflow_id, False)
        threading.Timer(delay, _kill_workflow, args=[workflow_id, True]).start()

        return True
    except RuntimeError:
        return False

def _process_executor_settings(config: dict, conf_dir: str, executor_config: str, conf_location: str, default_conf: str):
    """Helper function to process settings for any executor resource."""
    executor_config_path = os.path.join(conf_location, executor_config)
    if not os.path.isdir(executor_config_path):
        raise FileNotFoundError(f"Executor configuration folder: {executor_config_path}")

    settings_source = os.path.join(executor_config_path, "settings.conf")
    if not os.path.isfile(settings_source):
        raise FileNotFoundError(f"Executor configuration file: {settings_source}")

    os.makedirs(conf_dir, exist_ok=True)
    settings_path = os.path.join(conf_dir, "settings.conf")
    with open(settings_path, 'w') as settings_file:
        settings_file.write(default_conf + "\n")
        settings_file.write(convert_dict_to_string(config))

    for file in os.listdir(executor_config_path):
        source = os.path.join(executor_config_path, file)
        destination = os.path.join(conf_dir, file)
        if file == "settings.conf":
            with open(source, 'r') as src_file, open(settings_path, 'a') as dst_file:
                dst_file.write("\n" + src_file.read())
                logger.info(f"Appended {file} to {settings_path}")
        elif os.path.isfile(source):
            shutil.copy2(source, destination)
            logger.info(f"Copied {source} to {destination}")

    remove_duplicates_config(settings_path)

def process_settings(config, conf_dir, executor_config):
    """Process and write configuration settings for the primary executor and the fallback resources."""
    conf_location = get_env_variable('CONF_LOCATION')
    config_dict = json.loads(config.decode("utf-8"))
    default_conf_path = os.path.join(conf_location, "default.conf")
    with open(default_conf_path, "r") as f:
        default_conf = f.read()

    _process_executor_settings(config_dict, conf_dir, executor_config.decode("utf-8"), conf_location, default_conf)
    _process_fallback_resources(config_dict, conf_dir, conf_location, default_conf)

def convert_dict_to_string(config: dict) -> str:
    return "\n".join(f"{key}={value}" for key, value in config.items())

def remove_duplicates_config(config_path: str):
    config = {}

    with open(config_path, "r") as file:
        for line in file.readlines():
            if len(line.strip()) == 0:
                continue
            split = line.split("=", 1)
            if not line.lstrip().startswith("#") and len(split) == 2:
                config[split[0].strip()] = split[1].strip()
            else:
                config[line.strip()] = None

    with open(config_path, "w+") as file:
        for k, v in config.items():
            if v is None:
                file.write(f"{k}\n")
            else:
                file.write(f"{k} = {v}\n")

def _validate_fallback_resource(resource):
    if not isinstance(resource, dict) or len(resource) != 1:
        raise ValueError(f"Invalid fallback resource format: {resource}")

    executor_type, config_path = next(iter(resource.items()))
    if not isinstance(executor_type, str) or not executor_type:
        raise ValueError(f"Invalid executor type: {executor_type}")

    if not isinstance(config_path, str) or not config_path:
        raise ValueError(f"Invalid executor configuration path: {config_path}")

    return executor_type, config_path

def _process_fallback_resources(config: dict, conf_dir: str, conf_location: str, default_conf: str):
    """Process and create conf folders for all fallback resources."""
    fallback_resources = json.loads(config.get("fallback.resources", "[]"))
    if not isinstance(fallback_resources, list):
        raise ValueError("fallback.resources must contain a JSON list")

    for resource in fallback_resources:
        try:
            executor_type, resource_config_path = _validate_fallback_resource(resource)
            # Create local conf folder for this resource at workflow root
            local_conf_dir = os.path.join(os.path.dirname(conf_dir), f"conf-{resource_config_path.lower()}")
            # Update config with this fallback executor type
            fallback_config = config.copy()
            fallback_config['default.executor'] = executor_type
            _process_executor_settings(fallback_config, local_conf_dir, resource_config_path, conf_location, default_conf)
        except (OSError, ValueError) as e:
            logger.exception(f"Failed to process fallback resource {resource}: {e}")