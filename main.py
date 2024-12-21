import logging
from flask import Flask, request, jsonify
from openai import OpenAI
from pydantic import BaseModel, ValidationError
import openai
import os, subprocess
import json

openai.api_key = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    filename='agent.log', filemode='a')

app = Flask(__name__)


class QueryResponse(BaseModel):
    query: str
    answer: str

prep_commands = {
    "all_resources": "kubectl get all -o json",
    # "pv": "kubectl get pv -o json",
    # "pvc": "kubectl get pvc -o json",
    # "cm": "kubectl get configmap -o json",
    # "crd": "kubectl get crd -o json",
    "secret": "kubectl get secret -o json",
    "sa": "kubectl get serviceaccount -o json",
    # "hpa": "kubectl get hpa -o json",
    # "pdb": "kubectl get pdb -o json",
    # "ns": "kubectl get namespaces -o json",
    # "endpoints": "kubectl get endpoints -o json",
    # "statefulset": "kubectl get statefulset -o json"
}


@app.route('/query', methods=['POST'])
def create_query():
    if openai.api_key:
        logging.info("API key successfully loaded." + openai.api_key)
    else:
        logging.info("API key is missing. Please set the OPENAI_API_KEY environment variable.")

    request_data = request.json
    query = request_data.get('query')

    client = OpenAI()
    file_ids = []
    for command in prep_commands.keys():
        try:
            answer = subprocess.run(prep_commands[command], shell=True, check=True, capture_output=True, text=True).stdout.strip()
            logging.info("all resources - %s", answer)
        except Exception as e:
            logging.info("Error while running command - " + str(e))
            return jsonify({"error": e}), 500

        with open("/tmp/{}.json".format(command), "w") as outfile:
            json.dump(answer, outfile)
        file = client.files.create(file=open("/tmp/{}.json".format(command), "rb"), purpose="fine-tune")
        file_ids.append(file.id)

    datas = []
    for command in prep_commands.keys():
        with open("/tmp/{}.json".format(command), 'r') as f:
            datas.append(json.load(f))
    combined_data = {**datas}  # Merge dictionaries
    with open("/tmp/combined_data.json", "w") as outfile:
        json.dump(combined_data, outfile)
    file = client.files.create(file=open("/tmp/combined_data.json", "rb"), purpose="fine-tune")
    try:
        messages = [
            {
                "role": "system",
                "content": "You are an ai assistant who will answer questions asked in english, about various k8s resources. You will be given a json file containing details of all k8s resources in a k8s cluster. Answer the query posed by a user based on those details. Since a human is giving the query, you might need to look for resource names which are similar, and not necessarily exact. Give only the answer, nothing else. If the answer contains any autogenerated id like mongodb-56c598c8f, then just return mongodb. Answer properly based on the provided files only."
            },
            {
                "role": "user",
                "content": "Query - {}\nDetails of resources - {}".format(query, file.id)
            }
        ]

        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,

        )
        ret_response = QueryResponse(query=query, answer=response.choices[0].message.content)
        logging.info("Got ret_response: %s", ret_response)
        return jsonify(ret_response.dict())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)