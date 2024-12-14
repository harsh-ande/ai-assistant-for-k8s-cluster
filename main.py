import logging
import subprocess

from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError
import openai

openai.api_key = "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"

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
    try:
        # Extract the question from the request data
        request_data = request.json
        query = request_data.get('query')
        
        # Log the question
        logging.info(f"Received query: {query}")

        # Here, you can implement your logic to generate an answer for the given question.
        # Prepare the prompt
        command_prompt = f"I will give a query in english, you need to tell me the equivalent query in Kubernetes. The given query will only be around status of resources, information, or logs of resources deployed on Minikube. You can give just the corresponding query in Kubernetes and nothing else (not even enclosing apostrophes). If you need to, append 2 or more queries to each other to achieve the result. Query:  \"{query}\"."

        # Make the API call
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": command_prompt},
                {"role": "user", "content": command_prompt}
            ],
            max_tokens=200,
            temperature=0
        )

        # Extract the response
        command = response['choices'][0]['message']['content'].strip()
        logging.info(f"Generated command: {command}")

        if command=="":
            return jsonify({"error": "Error while converting given query to k8s command."}), 500

        # For simplicity, we'll just echo the question back in the answer.
        try:
            # Split the command into a list for subprocess
            answer = subprocess.run(command, shell=True, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as e:
            return jsonify({"error": e}), 500

        # Log the answer
        logging.info(f"Generated answer: {answer}")

        # Prepare the prompt for formatting the obtained text
        command_prompt = f"I will give you a text to format, can you show it in an easy and human readable way? Give me only the formatted text, nothing else. You should omit any auto generated substrings in names of resources in the given text. (For example if there are 2 pods named mongodb-6575f54b8f-tvfxgh and mongodb-6575f54b8f-qkhjw, just show them as mongodb-1 and mongodb-2.) \n The text is an answer to the query:\"{query}\" and the answer to format is :  \"{answer}\"."

        # Make the API call
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": command_prompt},
                {"role": "user", "content": command_prompt}
            ],
            max_tokens=4096,
            temperature=0
        )

        # Extract the formatted answer
        formatted_answer = response['choices'][0]['message']['content'].strip()
        logging.info(f"Formatted answer: {formatted_answer}")
        
        # Create the response model
        response = QueryResponse(query=query, answer=formatted_answer)
        
        return jsonify(response.dict())
    
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
