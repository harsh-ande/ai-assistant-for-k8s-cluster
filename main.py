import logging
from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError
import openai
import os, subprocess

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

    try:
        # Extract the question from the request data
        request_data = request.json
        query = request_data.get('query')

        try:
            response = openai.Model.list()
            logging.info("Models generated " + response)
        except Exception as e:
            logging.info(f"Error in listing models: {e}")

        # Log the question
        logging.info(f"Received query: {query}")

        # Prepare the prompt
        command_prompt = f"I will give a query in english, you need to tell me the equivalent query in Kubernetes. The given query will only be around status of resources, information, or logs of resources deployed on Minikube. You can give just the corresponding query in Kubernetes and nothing else (not even enclosing apostrophes). If you need to, append 2 or more queries to each other to achieve the result. Query:  \"{query}\"."

        try:
        # Make the API call
            logging.info("#1")
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": command_prompt},
                    {"role": "user", "content": command_prompt}
                ],
                max_tokens=200,
                temperature=0
            )
            logging.info("#2")

            # Extract the response
            command = response['choices'][0]['message']['content'].strip()
            logging.info(f"Generated command: {command}")

            if command=="":
                return jsonify({"error": "Error while converting given query to k8s command."}), 500
        except Exception as e:
            logging.info("Got error :" + str(e))

        # Here, you can implement your logic to generate an answer for the given question.
        # For simplicity, we'll just echo the question back in the answer.
        answer = "14"

        # Log the answer
        logging.info(f"Generated answer: {answer}")

        # Create the response model
        response = QueryResponse(query=query, answer=answer)

        return jsonify(response.dict())

    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)