import logging
import os
import subprocess
import shlex
import threading
from jvm_utils import start_jvm, load_classpath
from config import get_env_variable
from config import get_workflow_filename
import jpype.imports
from jpype.types import *

logger = logging.getLogger(__name__)

def launch_workflow(base_path, proxy_file):
    """Launch a workflow."""
    workflow_id = os.path.basename(base_path)
    os.environ['CLASSPATH'] = load_classpath()

    java_command_template = get_env_variable('JAVA_COMMAND', required=True)
    java_home = get_env_variable('JAVA_HOME', required=True)
    moteur_home = get_env_variable('MOTEUR_HOME', required=True)
    conf_location = get_env_variable('CONF_LOCATION', required=True)
    current_dir = os.path.basename(os.getcwd())
    workflow_name = get_workflow_filename()
    moteur_main_class = get_env_variable('MOTEUR_MAIN_CLASS', required=True)
    if proxy_file:
        proxy_file = f'-DX509_USER_PROXY={proxy_file}'
    else:
        proxy_file = ""
    logger.info(f"Launching workflow with ID: {workflow_id}")
    java_command = shlex.split(java_command_template.format(
        JAVA_HOME=java_home,
        CONF_LOCATION=conf_location,
        PROXY_FILE=proxy_file,
        MOTEUR_HOME=moteur_home,
        MOTEUR_MAIN_CLASS=moteur_main_class,
        workflow_id=workflow_id,
        workflow_file_path=f'{base_path}/{workflow_name}',
        inputs_file_path=f'{base_path}/inputs.xml',
    ))
    
    logger.info(f"Launching workflow with command: {' '.join(java_command)}")
    with open(f'{base_path}/workflow.out', 'w') as out, open(f'{base_path}/workflow.err', 'w') as err:
        subprocess.Popen(java_command, stdout=out, stderr=err, preexec_fn=os.setpgrp, cwd=base_path)

def _kill_workflow(workflow_id, hard_kill):
    """Kill a specific workflow and update its status in the database."""
    
    signal = 9 if hard_kill else 15
    moteur_process_class = get_env_variable('MOTEUR_MAIN_CLASS', required=True)
    user_name = get_env_variable('USER', required=True)
    try:
        command = f"ps -fu {user_name} | grep {moteur_process_class} | grep {workflow_id} | grep -v grep | awk '{{print $2}}' "
        logger.debug(f"Running command: {command}")
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8').strip()

        if output:
            logger.info(f"Process {output} killed with signal {signal}.")
            os.system(f"kill -{signal} {output}")

            if hard_kill:
                update_workflow_status(workflow_id, "Killed")
        elif not hard_kill:
            logger.warning("No matching process found.")
    
    except subprocess.CalledProcessError as e:
        logger.warning(f"Error finding or killing process: {e}")

def kill_workflow(workflow_id):
    """Trigger the `kill_workflow(workflow_id)` method after a specific delay."""
    delay = get_env_variable("KILL_DELAY", 120, False)

    try:
        _kill_workflow(workflow_id, False)
        threading.Timer(delay, kill_workflow, args=[workflow_id, True]).start()

        return True
    except RuntimeError:
        return False

def update_workflow_status(workflow_id, status):
    """Update the status of a workflow in the database."""
    start_jvm()
    from java.sql import DriverManager
    conn = DriverManager.getConnection(get_env_variable("DB_URL"), get_env_variable("DB_USER"), get_env_variable("DB_PASSWORD"))
    stmt = conn.createStatement()
    
    try:
        stmt.execute(f"UPDATE Workflows SET status='{status}' WHERE id='{workflow_id}'")
        conn.commit()
        logger.info(f"Workflow {workflow_id} status updated to {status}")
    finally:
        stmt.close()
        conn.close()

def process_settings(config, conf_dir):
    """Process and write configuration settings."""
    conf_location = get_env_variable('CONF_LOCATION')
    default_conf_path = os.path.join(conf_location, "default.conf")
    
    with open(default_conf_path, 'r') as default_conf_file:
        default_conf = default_conf_file.read()
    
    settings_path = os.path.join(conf_dir, "settings.conf")
    with open(settings_path, 'w') as settings_file:
        settings_file.write(default_conf)
        settings_file.write(config.decode('utf-8'))
