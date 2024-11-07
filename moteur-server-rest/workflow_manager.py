import os
import subprocess
from jvm_utils import start_jvm, load_classpath
from config import get_env_variable
import jpype.imports
from jpype.types import *

def launch_workflow(base_path):
    """Launch a workflow."""
    workflow_id = os.path.basename(base_path)
    os.environ['CLASSPATH'] = load_classpath()
    
    java_command = [
        os.path.join(os.getenv('JAVA_HOME'), 'bin', 'java'),
        "-Xmx950M", "-XX:PermSize=512m", "-XX:-UseGCOverheadLimit",
        f"-Duser.home={os.getenv('CONF_LOCATION')}",
        f"-DX509_USER_PROXY=/tmp/{workflow_id}-proxy",
        "fr.cnrs.i3s.moteur2.client.Main",
        "--config", f"{os.getenv('MOTEUR_HOME')}/.moteur2",
        "-ng", "-p", os.path.basename(os.getcwd()),
        os.path.join(base_path, "workflow.xml"),
        os.path.join(base_path, "input.xml")
    ]
    
    print(f"Launching workflow with command: {' '.join(java_command)}")
    with open(f'{base_path}/workflow.out', 'w') as out, open(f'{base_path}/workflow.err', 'w') as err:
        subprocess.Popen(java_command, stdout=out, stderr=err, preexec_fn=os.setpgrp, cwd=base_path)

def kill_workflow(workflow_id):
    """Kill a specific workflow and update its status in the database."""
    print("Killing workflow...")
    
    try:
        command = f"ps -fu vip | grep moteur2.client.Main | grep {workflow_id} | awk '{{print $2}}'"
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
    moteur_home = get_env_variable('MOTEUR_HOME')
    default_conf_path = os.path.join(moteur_home, "conf/default.conf")
    
    with open(default_conf_path, 'r') as default_conf_file:
        default_conf = default_conf_file.read()
    
    settings_path = os.path.join(conf_dir, "settings.conf")
    with open(settings_path, 'w') as settings_file:
        settings_file.write(default_conf)
        settings_file.write(config.decode('utf-8'))
