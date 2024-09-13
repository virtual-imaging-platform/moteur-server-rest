import os
import shutil

import jpype
import subprocess
import jpype.imports
from jpype.types import *


h2_jar = "h2/bin/h2-1.3.173.jar"

db_url = "jdbc:h2:~/test"

def start_jvm():
    if not jpype.isJVMStarted():
        jpype.startJVM(classpath=[h2_jar])

def fake_init_db():
    start_jvm()
    from java.sql import DriverManager
    conn = DriverManager.getConnection(db_url, "sa", "")
    
    stmt = conn.createStatement()

    # Create table workflows
    stmt.execute("""
    CREATE TABLE IF NOT EXISTS workflows (
        id VARCHAR(255),
        status VARCHAR(255)
    )
    """)
    
    # Erase and insert some data for testing
    stmt.execute("DELETE FROM workflows")
    stmt.execute("INSERT INTO workflows (id, status) VALUES ('1', 'running')")
    stmt.execute("INSERT INTO workflows (id, status) VALUES ('2', 'running')")
    stmt.execute("INSERT INTO workflows (id, status) VALUES ('3', 'running')")
    
    conn.commit()
    
    stmt.close()
    conn.close()

def kill_workflow(workflow_id):
    fake_init_db()

    print("Kill workflow")

    result = subprocess.run(['ps', 'aux'], stdout=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    
    for line in output.splitlines():
        # Test with sleep
        if 'sleep' in line and 'grep' not in line:
            pid = line.split()[1]
            print(f'PID de sleep: {pid}')
            subprocess.run(['kill', pid])
            break

    # Update workflow in db
    kill_in_db(workflow_id)
    
    return True

def kill_in_db(workflow_id):
    start_jvm()

    conn = DriverManager.getConnection(db_url, "sa", "")
    
    stmt = conn.createStatement()

    # Table before
    rs = stmt.executeQuery("SELECT * FROM workflows")
    while rs.next():
        print(f"id: {rs.getString('id')}, status: {rs.getString('status')}")
    
    stmt.execute(f"UPDATE workflows SET status='deleted' WHERE id='{workflow_id}'")
    
    # Table after
    rs = stmt.executeQuery("SELECT * FROM workflows")
    while rs.next():
        print(f"id: {rs.getString('id')}, status: {rs.getString('status')}")

    conn.commit()

    stmt.close()
    conn.close()

def shutdown_jvm():
    if jpype.isJVMStarted():
        jpype.shutdownJVM()

def create_directory(path):
    try:
        os.makedirs(path, exist_ok=True)
        print(f"Directory {path} created.")
    except OSError as e:
        print(f"Error creating directory {path}: {e}")
        raise

def write_file(file_path, content):
    try:
        with open(file_path, "wb") as file:
            file.write(content)
        print(f"File {file_path} successfully written.")
    except IOError as e:
        print(f"Error writing file {file_path}: {e}")
        raise


def load_classpath():
    classpath = f"{os.environ['MOTEUR_HOME']}/moteur2.jar"
    for jar_file in os.listdir(f"{os.environ['MOTEUR_HOME']}/libs") + os.listdir(f"{os.environ['MOTEUR_HOME']}/plugins"):
        classpath += f":{os.path.join(os.environ['MOTEUR_HOME'], 'libs', jar_file)}"
    return classpath

def process_settings(config, conf_dir):
    default_conf_path = f"{os.environ['MOTEUR_HOME']}/conf/default.conf"
    with open(default_conf_path, 'r') as default_conf_file:
        default_conf = default_conf_file.read()
    
    with open(f"{conf_dir}/settings.conf", 'w') as settings_file:
        settings_file.write(default_conf)
        # Config is bytes. Convert to string
        config_str = config.decode('utf-8')
        settings_file.write(config_str)
    
# Function that is doing the job of submitWorkflow.sh
def launch_workflow(base_path):
    workflow_id = os.path.basename(base_path)
    
    # Get classpath
    classpath = load_classpath()
    # Add to environment
    os.environ['CLASSPATH'] = classpath
    
    # Launching command
    java_command = [
        f"{os.environ['JAVA_HOME']}/bin/java", "-Xmx950M", "-XX:PermSize=512m", "-XX:-UseGCOverheadLimit",
        f"-Duser.home={os.path.expanduser('~/prod')}", f"-DX509_USER_PROXY=/tmp/{workflow_id}-proxy",
        "fr.cnrs.i3s.moteur2.client.Main", "--config", f"{os.environ['MOTEUR_HOME']}/.moteur2", "-ng", "-p", os.path.basename(os.getcwd()),
        f"{base_path}/workflow.xml", f"{base_path}/input.xml"
    ]
    
    # Execute command with out and err redirection
    print(f"---- LAUNCHING WORKFLOW: {' '.join(java_command)}")
    with open(f'/{base_path}/workflow.out', 'w') as out, open(f'/{base_path}/workflow.err', 'w') as err:
        subprocess.Popen(java_command, stdout=out, stderr=err, preexec_fn=os.setpgrp, cwd=base_path)
