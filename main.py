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


@app.route('/query', methods=['POST'])
def create_query():
    if openai.api_key:
        logging.info("API key successfully loaded." + openai.api_key)
    else:
        logging.info("API key is missing. Please set the OPENAI_API_KEY environment variable.")

    request_data = request.json
    query = request_data.get('query')

    try:
        answer = subprocess.run("kubectl get all -o json", shell=True, check=True, capture_output=True, text=True).stdout.strip()
        # logging.info("all resources - %s", answer)
    except Exception as e:
        logging.info("Error while running command - " + str(e))
        return jsonify({"error": e}), 500

    # resources_json = ast.literal_eval(answer)
    with open("/tmp/resources.json", "w") as outfile:
        json.dump(answer, outfile)

    client = OpenAI()
    file = client.files.create(file=open("/tmp/resources.json", "rb"), purpose="fine-tune")
    try:
        messages = [
            {
                "role": "system",
                "content": "You are an ai assistant who will answer questions asked in english, about various k8s resources. You will be given a json file containing details of all k8s resources in a k8s cluster. Answer the query posed by a user based on those details. Since a human is giving the query, you might need to look for resource names which are similar, and not necessarily exact. Give only the answer, nothing else. If the answer contains any autogenerated id like mongodb-56c598c8f, then just return mongodb."
            },
            {
                "role": "user",
                "content": "Query - {}\nDetails of resources - {}".format(query, {file.id})
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