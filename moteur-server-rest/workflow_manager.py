import os
import shutil
import subprocess
import shlex
from jvm_utils import start_jvm, load_classpath
from config import get_env_variable
from config import get_workflow_filename
from jpype.types import *

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
    print(f"Launching workflow with ID: {workflow_id}")
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
    
    print(f"Launching workflow with command: {' '.join(java_command)}")
    with open(f'{base_path}/workflow.out', 'w') as out, open(f'{base_path}/workflow.err', 'w') as err:
        subprocess.Popen(java_command, stdout=out, stderr=err, preexec_fn=os.setpgrp, cwd=base_path)

def kill_workflow(workflow_id):
    """Kill a specific workflow and update its status in the database."""
    print("Killing workflow...")
    
    moteur_process_class = get_env_variable('MOTEUR_MAIN_CLASS', required=True)
    user_name = get_env_variable('USER', required=True)
    try:
        command = f"ps -fu {user_name} | grep {moteur_process_class} | grep {workflow_id} | awk '{{print $2}}'"
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8').strip()
        
        if output:
            os.system(f"kill -9 {output}")
            print(f"Process {output} has been killed.")
        else:
            print("No matching process found.")
    except subprocess.CalledProcessError as e:
        print(f"Error finding or killing process: {e}")

    update_workflow_status(workflow_id, "Killed")
    return True

def update_workflow_status(workflow_id, status):
    """Update the status of a workflow in the database."""
    start_jvm()
    from java.sql import DriverManager
    conn = DriverManager.getConnection(get_env_variable("DB_URL"), get_env_variable("DB_USER"), get_env_variable("DB_PASSWORD"))
    stmt = conn.createStatement()
    
    try:
        stmt.execute(f"UPDATE Workflows SET status='{status}' WHERE id='{workflow_id}'")
        conn.commit()
        print(f"Workflow {workflow_id} status updated to {status}")
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

    remove_duplicates_config(settings_path)

def remove_duplicates_config(config_path: str):
    config = {}

    with open(config_path, "r") as file:
        for line in file.readlines():
            if (len(line.strip()) == 0):
                continue
            split = line.split("=", 1)
            if (len(split) == 2):
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
