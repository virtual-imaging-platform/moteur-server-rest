import logging
import base64
import random
import os
import subprocess
from flask import Flask, request, jsonify
from file_utils import create_directory, write_file
from workflow_manager import find_process_pids, launch_workflow, kill_workflow, process_settings
from config import get_env_variable
from config import get_workflow_filename
from auth import auth
import logging


logger = logging.getLogger(__name__)
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
        process_settings(base64.b64decode(json_data['settings']), conf_dir, base64.b64decode(json_data['executorConfig']))
    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        return jsonify({"error": f"Missing required parameter: {e}"}), 400

    proxy_file = None
    if json_data['proxy'] is not None and json_data['proxy'] != "":
        proxy_file = f"/tmp/{workflow_id}-proxy"
        write_file(proxy_file, base64.b64decode(json_data['proxy']))
        os.chmod(proxy_file, 0o400)
        
    launch_workflow(workflow_dir, proxy_file)

    logger.info(f"Workflow {workflow_id} submitted.")
    return workflow_id

@app.route('/kill', methods=['PUT'])
@auth.login_required
def handle_kill():
    data = request.get_json()
    try:
        workflow_id = data['workflowID']
        logger.debug("Received kill request for workflow_id: %s", workflow_id)
    except KeyError:
        logger.error("Missing required parameter: workflowID")
        return jsonify({"error": "Missing required parameter: workflow_id"}), 400

    killed = kill_workflow(workflow_id)
    if killed:
        return jsonify({"success": f"Kill signal sent to workflow {workflow_id}"})
    else:
        return jsonify({"error": f"Failed to send kill signal to workflow {workflow_id}"}), 500

@app.route('/status/<workflow_id>', methods=['GET'])
@auth.login_required
def handle_status(workflow_id):
    document_root = get_env_variable("WORKFLOWS_ROOT")
    
    pids = find_process_pids(workflow_id)
    workflow_status = "RUNNING" if pids else "UNKNOWN"

    if workflow_status != "RUNNING":
        workflow_out_path = os.path.join(document_root, workflow_id, "process.out")
        logger.debug(f"Checking completion status in file: {workflow_out_path}")
        
        try:
            with open(workflow_out_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "workflow finished with status COMPLETED" in content or "completed execution of workflow" in content:
                    workflow_status = "COMPLETE"
                elif "workflow finished with status ERROR" in content:
                    workflow_status = "FAILED"
                else:
                    workflow_status = "TERMINATED"
        except FileNotFoundError:
            logger.warning(f"process.out not found for workflow {workflow_id}")
            workflow_status = "UNKNOWN"

        logger.info(f"Workflow: {workflow_id}, status: {workflow_status}")
    else:
        logger.debug(f"Workflow: {workflow_id}, status: {workflow_status}")

    return workflow_status



@app.route("/")
def index():
    app.logger.debug("This is moteur serveur rest")
    return "Hello, World!"
