from flask import Flask, request, jsonify
import random
import os
import base64
from utils import kill_workflow, create_directory, write_file, launch_workflow, process_settings
from dotenv import load_dotenv

load_dotenv(override=True)

app = Flask(__name__)


@app.route('/submit', methods=['POST'])
def handle_submit():
    print("Submit")

    document_root = os.getenv("DOCUMENT_ROOT")
    if not document_root:
        raise EnvironmentError("DOCUMENT_ROOT is not defined")

    workflows_dir = os.path.join(document_root, "workflows")
    create_directory(workflows_dir)

    workflow_id = f"workflow-{''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))}"
    workflow_dir = os.path.join(workflows_dir, workflow_id)
    create_directory(workflow_dir)

    conf_dir = os.path.join(workflow_dir, "conf")
    create_directory(conf_dir)

    # Write workflow, input, and settings files
    workflow_b64 = request.get_json()['workflow']
    input_b64 = request.get_json()['input']
    settings_b64 = request.get_json()['settings']
    write_file(os.path.join(workflow_dir, "workflow.xml"), base64.b64decode(workflow_b64))
    write_file(os.path.join(workflow_dir, "input.xml"), base64.b64decode(input_b64))
    
    process_settings(base64.b64decode(settings_b64), conf_dir)

    # Write proxy file
    proxy_file = f"/tmp/{workflow_id}-proxy"
    write_file(proxy_file, base64.b64decode(request.get_json()['proxy']))
    os.chmod(proxy_file, 0o400)
    print("Proxy file successfully written")

    # Check proxy lifetime
    # lifetime_command = f"X509_USER_PROXY={proxy_file} /opt/glite/bin/voms-proxy-info --timeleft"
    # result = subprocess.run(lifetime_command, shell=True, capture_output=True, text=True)
    # if result.returncode != 0 or int(result.stdout.strip()) < 18000:
    #     raise ValueError(f"Proxy lifetime too short: {result.stdout.strip()} seconds")

    # Launch MOTEUR
    launch_workflow(workflow_dir)
    
    hostname = os.uname()[1]
    port = os.getenv("SERVER_PORT", "5000")
    workflow_url = f"https://{hostname}:{port}/workflows/{workflow_id}/html/{workflow_id}.html"
    
    print(f"Workflow URL: {workflow_url}")
    return workflow_url


@app.route('/kill', methods=['PUT'])
def handle_kill():
    print("Kill")
    data = request.get_json()
    workflow_id = data['workflow_id']
    killed = kill_workflow(workflow_id)
    return jsonify(killed)


@app.route('/status/<workflow_id>', methods=['GET'])
def handle_status(workflow_id):
    workflow_status = ""

    print(f"Getting status of workflow {workflow_id}")
    
    command = f"ps -fu apache | grep {workflow_id}/workflow.xml &>/dev/null"

    status = os.system(command)

    if status == -1:
        error_message = "[moteur_server] Cannot get workflow status"
        return jsonify({'error': error_message}), 500

    # Check the result of the command
    if os.WEXITSTATUS(status) == 0:
        workflow_status = "RUNNING"
    else:
        # If not running, check if it is completed
        command = f"grep 'completed execution of workflow' {os.environ['DOCUMENT_ROOT']}/workflows/{workflow_id}/workflow.out &>/dev/null"

        stat = os.system(command)

        if stat == -1:
            error_message = "[moteur_server] Cannot grep workflow status"
            return jsonify({'error': error_message}), 500

        ret = os.WEXITSTATUS(stat)
        print(f"Workflow status (WEXITSTATUS): {ret}")
        if ret == 0:
            workflow_status = "COMPLETE"
        elif ret == 1:
            workflow_status = "TERMINATED"
        else:
            workflow_status = "UNKNOWN WORKFLOW"
    
    return workflow_status


if __name__ == '__main__':
    # host is 0.0.0.0 to allow external access
    app.run(debug=True, host='0.0.0.0', port=os.getenv("SERVER_PORT", "5000"))
