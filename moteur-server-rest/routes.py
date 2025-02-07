from flask import Flask, request, jsonify
import base64
import random
import os
import subprocess
from file_utils import create_directory, write_file
from workflow_manager import launch_workflow, kill_workflow, process_settings, copy_executor_config
from config import get_env_variable
from config import get_workflow_filename
from auth import auth

app = Flask(__name__)

@app.route('/submit', methods=['POST'])
@auth.login_required
def handle_submit():
    document_root = get_env_variable("WORKFLOWS_ROOT", required=True)
    
    alpanum = 'abcdefghijklmnopqrstuvwxyz0123456789'
    workflow_id = f"workflow-{''.join(random.choices(alpanum, k=6))}"
    while os.path.exists(os.path.join(document_root, workflow_id)):
        workflow_id = f"workflow-{''.join(random.choices(alpanum, k=6))}"
        
    workflow_dir = os.path.join(document_root, workflow_id)
    conf_dir = os.path.join(workflow_dir, "conf")
    create_directory(conf_dir)
    json_data = request.get_json()
    try:
        write_file(os.path.join(workflow_dir, get_workflow_filename()), base64.b64decode(json_data['workflow']))
        write_file(os.path.join(workflow_dir, "inputs.xml"), base64.b64decode(json_data['inputs']))
        process_settings(base64.b64decode(json_data['settings']), conf_dir)
        copy_executor_config(base64.b64decode(json_data['executorConfig']), conf_dir)
    except KeyError as e:
        print(f"Missing required parameter: {e}")
        return jsonify({"error": f"Missing required parameter: {e}"}), 400

    proxy_file = None
    if json_data['proxy'] is not None and json_data['proxy'] != "":
        proxy_file = f"/tmp/{workflow_id}-proxy"
        write_file(proxy_file, base64.b64decode(json_data['proxy']))
        os.chmod(proxy_file, 0o400)
        
    launch_workflow(workflow_dir, proxy_file)

    print(f"Workflow {workflow_id} submitted.")
    return workflow_id

@app.route('/kill', methods=['PUT'])
@auth.login_required
def handle_kill():
    data = request.get_json()
    try:
        workflow_id = data['workflowID']
    except KeyError:
        return jsonify({"error": "Missing required parameter: workflow_id"}), 400

    killed = kill_workflow(workflow_id)
    if killed:
        return jsonify({"success": f"Workflow {workflow_id} successfully terminated."})
    else:
        return jsonify({"error": f"Failed to terminate workflow {workflow_id}."}), 500

@app.route('/status/<workflow_id>', methods=['GET'])
@auth.login_required
def handle_status(workflow_id):
    document_root = get_env_variable("WORKFLOWS_ROOT")
    current_user = get_env_variable("USER")
    workflow_file_name = get_workflow_filename()
    check_process_command = f"ps -fu {current_user} | grep {workflow_id}/{workflow_file_name} | grep -v grep"

    status = subprocess.run(check_process_command, shell=True, stdout=subprocess.PIPE)
    workflow_status = "RUNNING" if status.returncode == 0 else "UNKNOWN"
    
    if workflow_status != "RUNNING":
        check_completion_command = f"grep 'completed execution of workflow' {document_root}/{workflow_id}/workflow.out"
        completed_status = subprocess.run(check_completion_command, shell=True)
        
        if completed_status.returncode == 0:
            workflow_status = "COMPLETE"
        elif completed_status.returncode == 1:
            workflow_status = "TERMINATED"
        else:
            workflow_status = "UNKNOWN"
    print(workflow_status)
    return workflow_status


@app.route("/")
def index():
    app.logger.debug("This is moteur serveur rest")
    return "Hello, World!"
