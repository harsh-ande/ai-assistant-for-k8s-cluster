import ast
import logging
import os, subprocess

from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    filename='agent.log', filemode='a')

app = Flask(__name__)


class QueryResponse(BaseModel):
    query: str
    answer: str

# Function to parse user query using ChatGPT API
def extract_intent_resource_from_query(query):
    messages = [
        {
            "role": "system",
            "content": "You are an ai assistant who will answer questions about various resources deployed in a k8s cluster."
        },
        {
            "role": "user",
            "content": f"""
    Extract the intent, and resource from the following Kubernetes-related query:
    "{query}"
    Respond in JSON format as:
    {{
        "intent": "<intent>",
        "resource": "<resource>",
    }}
    Available options for intent are get_pod_count, get_container_port, get_pod_status, get_service_port, get_probe_path, get_secret_association, get_mount_path, get_env_variable, get_database_name.   
    """
        }
    ]
    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages,

    )
    return response.choices[0].message.content

# Function to generate kubectl commands based on parsed query
def get_kubectl_command(intent, resource, namespace):
    if intent == "get_namespace":
        return f"kubectl get svc {resource} -o jsonpath='{{.metadata.namespace}}'"
    elif intent == "get_pod_count":
        return "kubectl get pods --all-namespaces | wc -l"
    elif intent == "get_container_port":
        return f"kubectl -n {namespace} get pod {resource} -o jsonpath='{{.spec.containers[0].ports[0].containerPort}}'"
    elif intent == "get_pod_status":
        return f"kubectl -n {namespace} get pod {resource} -o jsonpath='{{.status.phase}}'"
    elif intent == "get_service_port":
        return f"kubectl -n {namespace} get svc {resource} -o jsonpath='{{.spec.ports[0].port}}'"
    elif intent == "get_probe_path":
        return f"kubectl -n {namespace} get pod {resource} -o jsonpath='{{.spec.containers[0].readinessProbe.httpGet.path}}'"
    elif intent == "get_secret_association":
        return f"kubectl -n {namespace} get pod -o json | jq -r '.items[] | select(.spec.volumes[].secret.secretName==\"{resource}\") | .metadata.name'"
    elif intent == "get_mount_path":
        return f"kubectl -n {namespace} get pod {resource} -o jsonpath='{{.spec.volumes[0].persistentVolumeClaim.claimName}}'"
    elif intent == "get_env_variable":
        return f"kubectl -n {namespace} get pod {resource} -o jsonpath='{{.spec.containers[0].env[?(@.name==CHART_CACHE_DRIVER)].value}}'"
    elif intent == "get_database_name":
        return f"kubectl -n {namespace} exec {resource} -- psql -c 'SELECT current_database()'"
    else:
        return None

@app.route('/query', methods=['POST'])
def create_query():
    if openai.api_key:
        logging.info("API key successfully loaded." + openai.api_key)
    else:
        logging.info("API key is missing. Please set the OPENAI_API_KEY environment variable.")
    try:
        # Extract the question from the request data
        request_data = request.json
        query = request_data.get('query')

        # Log the question
        logging.info(f"Received query: {query}")

        try:
            answer = subprocess.run("kubectl get ns -o json", shell=True, check=True, capture_output=True,
                                    text=True).stdout.strip()
            json_ns = ast.literal_eval(answer)
            namespaces = [i["metadata"]["name"] for i in json_ns["items"]]
            logging.info("namespaces list - %s", namespaces)
        except Exception as e:
            logging.info("Error while running get ns command - " + str(e))
            return jsonify({"error": e}), 500
        namespaces.remove('kube-node-lease')
        namespaces.remove('kube-public')
        namespaces.remove('kube-system')

        intent_resource = extract_intent_resource_from_query(query)
        if intent_resource.startswith("json"):
            intent_resource.replace("json", "")
        intent_resource = intent_resource.strip()
        intent_resource_json = ast.literal_eval(intent_resource)
        logging.info("Got intent_resource - " + str(intent_resource_json))
        for ns in namespaces:
            k8s_cmd = get_kubectl_command(intent_resource_json["intent"], intent_resource_json["resource"], ns)
            if k8s_cmd:
                logging.info("Generated k8s command - "+k8s_cmd)
            try:
                answer = subprocess.run(k8s_cmd, shell=True, check=True, capture_output=True, text=True).stdout.strip()
                logging.info("Answer rcvd - %s", answer)
            except Exception as e:
                logging.info("Error while running generated k8s command - " + str(e))
                return jsonify({"error": e}), 500

        # Log the answer
        logging.info(f"Generated answer: {answer}")

        # Create the response model
        response = QueryResponse(query=query, answer=answer)

        return jsonify(response.dict())

    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
