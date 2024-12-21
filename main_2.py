# import logging
# from flask import Flask, request, jsonify
# from pydantic import BaseModel, ValidationError
# import openai
# import os, subprocess
#
# openai.api_key = os.getenv("OPENAI_API_KEY")
#
# # Configure logging
# logging.basicConfig(level=logging.DEBUG,
#                     format='%(asctime)s %(levelname)s - %(message)s',
#                     filename='agent.log', filemode='a')
#
# app = Flask(__name__)
#
#
# class QueryResponse(BaseModel):
#     query: str
#     answer: str
#
#
# @app.route('/query', methods=['POST'])
# def create_query():
#     if openai.api_key:
#         logging.info("API key successfully loaded." + openai.api_key)
#     else:
#         logging.info("API key is missing. Please set the OPENAI_API_KEY environment variable.")
#
#     try:
#         # Extract the question from the request data
#         request_data = request.json
#         query = request_data.get('query')
#
#         logging.info("Generating models")
#         _ = openai.Model.list()
#         logging.info("Models generated")
#
#         # Log the query
#         logging.info(f"Received query: {query}")
#
#         # Prepare the prompt
#         command_prompt = """I will give you a query in english. You will need to give me a set of kubectl commands to execute. I will give execute the given kubectl commands and give you the results of each command. You will need to then answer the given query based on the results of the commands.
#
#                             Query: {}
#
#                             Give me the kubectl commands to execute in a format so that I can read it programmatically. Do not give anything other than the commands to execute on each line.""".format(
#             query)
#         commands_list = []
#         try:
#             # Make the API call
#             logging.info("#1")
#             response = openai.ChatCompletion.create(
#                 model="gpt-4-turbo",
#                 messages=[
#                     {"role": "system", "content": command_prompt},
#                     {"role": "user", "content": command_prompt}
#                 ],
#                 max_tokens=200,
#                 temperature=0
#             )
#             logging.info("#2")
#
#             # Extract the response
#             commands = response['choices'][0]['message']['content'].strip()
#             logging.info(f"Generated commands: {commands}")
#
#             if commands == "":
#                 return jsonify({"error": "Error while converting given query to k8s command."}), 500
#             commands_list = commands.strip().splitlines()
#
#         except Exception as e:
#             logging.info("Got error :" + str(e))
#             return jsonify({"error": e.errors()}), 400
#
#         # Here, you can implement your logic to generate an answer for the given question.
#         answer = "14"
#         answers_list = []
#         for c in commands_list:
#             try:
#                 # Split the command into a list for subprocess
#                 answer = subprocess.run(c, shell=True, check=True, capture_output=True, text=True).stdout.strip()
#                 answers_list.append(answer)
#             except Exception as e:
#                 logging.info("Error while running command - " + str(e))
#                 # return jsonify({"error": e}), 500
#
#         # Log the answer
#         logging.info(f"Generated answers list")
#
#         question2_prompt = """Earlier I had asked on query in english - {}
#
# To answer this, you had provided some kubectl commands to run. I have run those commands and have given the results below.""".format(
#             query)
#         for q, r in zip(commands_list, answers_list):
#             question2_prompt += "\n Command: {}\nAnswer: {}\n".format(q, r[:1000])
#         question2_prompt += "\nNow answer the original english query using the results from above."
#
#         response = openai.ChatCompletion.create(
#             model="gpt-4-turbo",
#             messages=[
#                 {"role": "system", "content": question2_prompt},
#                 {"role": "user", "content": question2_prompt}
#             ],
#             max_tokens=4096,
#             temperature=0
#         )
#
#         # Extract the formatted answer
#         formatted_answer = response['choices'][0]['message']['content'].strip()
#         logging.info(f"Formatted answer: {formatted_answer}")
#
#         # Create the response model
#         response = QueryResponse(query=query, answer=formatted_answer)
#
#         return jsonify(response.dict())
#
#     except ValidationError as e:
#         return jsonify({"error": e.errors()}), 400
#
#
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=8000, debug=True)