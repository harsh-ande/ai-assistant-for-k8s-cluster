import logging
import subprocess

from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError
import openai

# openai.api_key = "<redacted>"

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
        prompt = f"I will give a query in english, you need to tell me the equivalent query in Kubernetes. The given query will only be around status of resources, information, or logs of resources deployed on Minikube. You can give just the corresponding query in Kubernetes and nothing else. Query:  \"{query}\"."

        # Make the API call
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0
        )

        # Extract the response
        command = response['choices'][0]['message']['content'].strip()
        logging.info(f"Generated command: {command}")

        # For simplicity, we'll just echo the question back in the answer.
        try:
            # Split the command into a list for subprocess
            answer = subprocess.run(command, shell=True, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as e:
            return jsonify({"error": e.errors()}), 500

        # Log the answer
        logging.info(f"Generated answer: {answer}")
        
        # Create the response model
        response = QueryResponse(query=query, answer=answer)
        
        return jsonify(response.dict())
    
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
