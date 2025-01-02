import ast
import datetime
import logging

import kubernetes
from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError
import openai
import os, subprocess
import json
from kubernetes import config

# Configs can be set in Configuration class directly or using helper utility
config.load_kube_config()

openai.api_key = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    filename='agent.log', filemode='a')

app = Flask(__name__)


class QueryResponse(BaseModel):
    query: str
    answer: str

# # Utility function to execute kubectl commands
# def execute_kubectl_command(command):
#     try:
#         result = subprocess.check_output(command, shell=True, text=True)
#         return result.strip()
#     except subprocess.CalledProcessError as e:
#         return f"Error executing command: {e}"
#
# # Function to parse user query using ChatGPT API (v1.58+ syntax)
# def parse_query(query):
#     messages = [
#         {"role": "system", "content": "You are an ai assistant specialized in Kubernetes queries."},
#         {"role": "user", "content": f"Extract the intent, resource, and attribute from the following Kubernetes-related query:\n\n{query}\n\nRespond with only a JSON in this format, nothing else:\n{{\"intent\": \"<intent>\", \"resource\": \"<resource>\", \"attribute\": \"<attribute>\"}}. Possible values for intent are - get_pod_count, get_container_port, get_status, get_service_port, get_probe_path, get_secret_association, get_mount_path, get_env_variable, get_database_name."}
#     ]
#     response = openai.chat.completions.create(
#         model="gpt-4-turbo",
#         messages=messages,
#     )
#     logging.info(response)
#     logging.info("returning " + response.choices[0].message.content)
#     return response.choices[0].message.content
#
# # Function to generate kubectl commands based on parsed query
# def generate_kubectl_command(intent, resource, attribute):
#     if intent == "get_namespace":
#         return f"kubectl get svc {resource} -o jsonpath='{{.metadata.namespace}}'"
#     elif intent == "get_pod_count":
#         return "kubectl get pods --all-namespaces | wc -l"
#     elif intent == "get_container_port":
#         return f"kubectl get pod {resource} -o jsonpath='{{.spec.containers[0].ports[0].containerPort}}'"
#     elif intent == "get_status":
#         return f"kubectl get pod {resource} -o jsonpath='{{.status.phase}}'"
#     elif intent == "get_service_port":
#         return f"kubectl get svc {resource} -o jsonpath='{{.spec.ports[0].port}}'"
#     elif intent == "get_probe_path":
#         return f"kubectl get pod {resource} -o jsonpath='{{.spec.containers[0].readinessProbe.httpGet.path}}'"
#     elif intent == "get_secret_association":
#         return f"kubectl get pod -o json | jq -r '.items[] | select(.spec.volumes[].secret.secretName==\"{resource}\") | .metadata.name'"
#     elif intent == "get_mount_path":
#         return f"kubectl get pod {resource} -o jsonpath='{{.spec.volumes[0].persistentVolumeClaim.claimName}}'"
#     elif intent == "get_env_variable":
#         return f"kubectl get pod {resource} -o jsonpath='{{.spec.containers[0].env[?(@.name==\"{attribute}\")].value}}'"
#     elif intent == "get_database_name":
#         return f"kubectl exec {resource} -- psql -c 'SELECT current_database()'"
#     else:
#         return None

@app.route('/query', methods=['POST'])
def create_query():
    if openai.api_key:
        logging.info("API key successfully loaded." + openai.api_key)
    else:
        logging.info("API key is missing. Please set the OPENAI_API_KEY environment variable.")

    request_data = request.json
    query = request_data.get('query')

    # # Step 1: Parse the query
    # parsed_query = parse_query(query)
    # logging.info("1234")
    # logging.info(type(parsed_query))
    # logging.info(parsed_query)
    #
    # try:
    #     parsed_data = eval(parsed_query)  # Parse the JSON response
    #     intent = parsed_data.get("intent")
    #     resource = parsed_data.get("resource")
    #     attribute = parsed_data.get("attribute")
    # except Exception as e:
    #     return jsonify({"error": f"Failed to parse query: {e}"}), 500
    #
    # # Step 2: Generate kubectl command
    # kubectl_command = generate_kubectl_command(intent, resource, attribute)
    # logging.info("generated command " + kubectl_command)
    # if not kubectl_command:
    #     return jsonify({"error": "Unsupported query or intent"}), 400
    #
    # # Step 3: Execute kubectl command
    # kubectl_output = execute_kubectl_command(kubectl_command)
    #
    # # # Step 4: Format the response
    # # response = format_response(kubectl_output, intent)
    #
    # # Step 5: Return the response
    # ret_response = QueryResponse(query=query, answer=kubectl_output)
    ret_response = QueryResponse(query=query, answer="14")
    logging.info("Got ret_response: %s", ret_response)
    return jsonify(ret_response.dict())
    # try:
    #
    #     return jsonify(ret_response.dict())
    # except ValidationError as e:
    #     return jsonify({"error": e.errors()}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)