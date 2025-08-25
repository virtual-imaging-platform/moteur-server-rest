import json
import logging
import os
import shutil
import subprocess
import shlex
import threading
from jvm_utils import load_classpath
from config import get_env_variable
from config import get_workflow_filename

logger = logging.getLogger(__name__)

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

    wf_file   = os.path.join(base_path, get_workflow_filename())
    input_file  = os.path.join(base_path, 'inputs.xml')
    proxy_arg = f'-DX509_USER_PROXY={proxy_file}' if proxy_file else ''

    # Construction de la commande
    cmd = shlex.split(java_cmd_tpl.format(
        JAVA_HOME=java_home,
        CONF_LOCATION=conf_location,
        PROXY_FILE=proxy_arg,
        MOTEUR_HOME=moteur_home,
        MOTEUR_MAIN_CLASS=moteur_main_cls,
        workflow_id=workflow_id,
        workflow_file_path=wf_file,
        inputs_file_path=input_file,
    ))

    out_path = os.path.join(base_path, 'workflow.out')
    err_path = os.path.join(base_path, 'workflow.err')

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



def process_settings(config, conf_dir, executor_config):
    """Process and write configuration settings."""
    conf_location = get_env_variable('CONF_LOCATION')
    default_conf_path = os.path.join(conf_location, "default.conf")

    with open(default_conf_path, 'r') as default_conf_file:
        default_conf = default_conf_file.read()
    
    settings_path = os.path.join(conf_dir, "settings.conf")
    with open(settings_path, 'w') as settings_file:
        settings_file.write(default_conf + "\n")
        settings_file.write(convert_json_to_string(config.decode('utf-8')))
    
    if executor_config:
        executor_config_path = os.path.join(conf_location, executor_config.decode('utf-8'))
        if os.path.exists(executor_config_path):
            files_list = os.listdir(executor_config_path)
            for file in files_list:
                if file == "settings.conf":
                    with open(os.path.join(executor_config_path, file), 'r') as src_file:
                        with open(settings_path, 'a') as dst_file:
                            dst_file.write("\n")
                            dst_file.write(src_file.read())
                            logger.info(f"Appended {file} to {settings_path}")
                else:
                    src_file = os.path.join(executor_config_path, file)
                    dst_file = os.path.join(conf_dir, file)
                    shutil.copy(src_file, dst_file)
                    logger.info(f"Copied {src_file} to {dst_file}")
        else:
            logger.warning(f"Executor config file {executor_config_path} does not exist. Skipping copy.")

    remove_duplicates_config(settings_path)

def convert_json_to_string(config) -> str:
    rows = []
    data: dict = json.loads(config)

    for k, v in data.items():
        rows.append(f"{k}={v}")
    return "\n".join(rows)

def remove_duplicates_config(config_path: str):
    config = {}

    with open(config_path, "r") as file:
        for line in file.readlines():
            if (len(line.strip()) == 0):
                continue
            split = line.split("=", 1)
            if line[0] != "#" and (len(split) == 2):
                config[split[0].strip()] = split[1].strip()
            else:
                config[line.strip()] = None

    with open(config_path, "w+") as file:
        for k, v in config.items():
            if v == None:
                file.write(f"{k}\n")
            else:
                file.write(f"{k} = {v}\n")

def copy_executor_config(config_path: str, conf_dir: str):
    """Copy the executor specific configuration to the configuration workflow folder"""
    if (len(config_path.strip()) == 0):
        return
    conf_file = os.path.join(conf_dir, "executor.json")

    shutil.copy(config_path, conf_file)
