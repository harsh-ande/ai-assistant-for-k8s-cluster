import ast
import datetime
import logging

import kubernetes
from flask import Flask, request, jsonify
from openai import OpenAI, AssistantEventHandler
from openai.types.beta.assistant import ToolResources
from pydantic import BaseModel, ValidationError
import openai
import os, subprocess
import json

openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    filename='agent.log', filemode='a')

app = Flask(__name__)

kubernetes.config.load_kube_config()

class QueryResponse(BaseModel):
    query: str
    answer: str

def custom_serializer(obj):
    """Custom serializer for non-serializable objects."""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()  # Convert datetime to ISO 8601 string
    raise TypeError(f"Type {type(obj)} not serializable")

class EventHandler(AssistantEventHandler):
  # @override
  def on_text_created(self, text) -> None:
      print(f"\nassistant > ", end="", flush=True)

  # @override
  def on_tool_call_created(self, tool_call):
      print(f"\nassistant > {tool_call.type}\n", flush=True)

  # @override
  def on_message_done(self, message) -> None:
      # print a citation to the file searched
      message_content = message.content[0].text
      annotations = message_content.annotations
      citations = []
      for index, annotation in enumerate(annotations):
          message_content.value = message_content.value.replace(
              annotation.text, f"[{index}]"
          )
          if file_citation := getattr(annotation, "file_citation", None):
              cited_file = client.files.retrieve(file_citation.file_id)
              citations.append(f"[{index}] {cited_file.filename}")

      print(message_content.value)
      print("\n".join(citations))

@app.route('/query', methods=['POST'])
def create_query():
    if openai.api_key:
        logging.info("API key successfully loaded." + openai.api_key)
    else:
        logging.info("API key is missing. Please set the OPENAI_API_KEY environment variable.")

    request_data = request.json
    query = request_data.get('query')

    core_v1 = kubernetes.client.CoreV1Api()
    apps_v1 = kubernetes.client.AppsV1Api()

    all_resources = {}
    try:
        # Get Pods
        pods = core_v1.list_pod_for_all_namespaces()
        all_resources["pods"] = [pod.to_dict() for pod in pods.items]

        # Get Secrets
        secrets = core_v1.list_secret_for_all_namespaces()
        all_resources["secrets"] = [secret.to_dict() for secret in secrets.items]

        # Get Services
        services = core_v1.list_service_for_all_namespaces()
        all_resources["services"] = [service.to_dict() for service in services.items]

        logging.info("got all data from k8s cluster - "  + str(all_resources))
    except Exception as e:
        logging.info("Error while reading all resources command - " + str(e))
        return jsonify({"error": e}), 500

    with open("/tmp/k8s_resources_all_namespaces.json", "w") as f:
        json.dump(all_resources, f, indent=4, default=custom_serializer)

    client = OpenAI()
    assistant = client.beta.assistants.create(
        name="K8s AI Assistant",
        instructions="You are an ai assitant for resources in a k8s cluster. Answer the query given by user based on the provided info.",
        tools=[{"type": "code_interpreter"}],
        model="gpt-4-turbo",
    )

    # Create a vector store caled "Financial Statements"
    vector_store = client.beta.vector_stores.create(name="Resources in a K8s cluster")

    # Ready the files for upload to OpenAI
    file_paths = ["/tmp/k8s_resources_all_namespaces.json"]
    file_streams = [open(path, "rb") for path in file_paths]

    # Use the upload and poll SDK helper to upload the files, add them to the vector store,
    # and poll the status of the file batch for completion.
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=file_streams
    )

    # You can print the status and the file counts of the batch to see the result of this operation.
    logging.info(file_batch.status)
    logging.info(file_batch.file_counts)
    logging.info("file_batch - " + str(file_batch))
    assistant = client.beta.assistants.update(
        assistant_id=assistant.id,
        tool_resources={"code_interpreter": ToolResources(files=file_batch.files)},
    )

    # Upload the user provided file to OpenAI
    message_file = client.files.create(
        file=open("/tmp/k8s_resources_all_namespaces.json", "rb"), purpose="assistants"
    )

    # Create a thread and attach the file to the message
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": query,
                # Attach the new file to the message.
                "attachments": [
                    {"file_id": message_file.id, "tools": [{"type": "file_search"}]}
                ],
            }
        ]
    )

    # The thread now has a vector store with that file in its tool resources.
    logging.info(thread.tool_resources.file_search)

    # Use the create and poll SDK helper to create a run and poll the status of
    # the run until it's in a terminal state.

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id, assistant_id=assistant.id
    )

    messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))

    message_content = messages[0].content[0].text
    annotations = message_content.annotations
    citations = []
    for index, annotation in enumerate(annotations):
        message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
        if file_citation := getattr(annotation, "file_citation", None):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(f"[{index}] {cited_file.filename}")

    logging.info(message_content.value)
    logging.info("\n".join(citations))

    ret_response = QueryResponse(query=query, answer=message_content.value)
    logging.info("Got ret_response: %s", ret_response)
    return jsonify(ret_response.dict())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)