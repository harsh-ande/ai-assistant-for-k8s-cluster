# import logging
# from flask import Flask, request, jsonify
# from pydantic import BaseModel, ValidationError
# import openai
# import os, subprocess
# import ast
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
#     request_data = request.json
#     query = request_data.get('query')
#
#     try:
#         tools = [
#             {
#                 "type": "function",
#                 "function": {
#                     "name": "run_kubectl_command",
#                     "description": "Run a given kubectl command. Call this whenever you need to run a kubectl command to get the results. For example when you need to know the result of `kubectl get pods -l app=harbor -n harbor`",
#                     "parameters": {
#                         "type": "object",
#                         "properties": {
#                             "kubectl_command": {
#                                 "type": "string",
#                                 "description": "The kubectl command to run.",
#                             },
#                         },
#                         "required": ["kubectl_command"],
#                         "additionalProperties": False,
#                     },
#                 }
#             }
#         ]
#
#         messages = [
#             {
#                 "role": "system",
#                 "content": "You are an ai assistant for getting status of various resources deployed in a K8s cluster. Use the supplied tool to obtain results of kubectl commands that you need to answer the query given from user. Now for the query given below, given the kubectl command to execute."
#             },
#             {
#                 "role": "user",
#                 "content": query
#             }
#         ]
#
#         response = openai.chat.completions.create(
#             model="gpt-4-turbo",
#             messages=messages,
#             tools=tools,
#         )
#         logging.info("Got response: %s", response)
#         logging.info("resp func arg %s", response.choices[0].message.tool_calls[0].function.arguments)
#         args = ast.literal_eval(response.choices[0].message.tool_calls[0].function.arguments)["kubectl_command"]
#         messages.append(
#             {
#                 "tool_call_id": response.choices[0].message.tool_calls[0].id,
#                 "role": "tool",
#                 "name": "run_kubectl_command",
#                 "content": response.choices[0].message.tool_calls[0].function.arguments
#             }
#         )  # extend conversation with function response
#
#         gpt_resp = response.choices[0].message
#         if gpt_resp.tool_calls:
#             for tool_call in gpt_resp.tool_calls:
#                 # Execute the function based on the tool call
#                 if tool_call.function.name == "run_kubectl_command":
#                     logging.info("Args - %s", tool_call.function.arguments)
#                     dict_obj = ast.literal_eval(tool_call.function.arguments)
#                     command = dict_obj["kubectl_command"]
#                     try:
#                         answer = subprocess.run(command, shell=True, check=True, capture_output=True, text=True).stdout.strip()
#                     except Exception as e:
#                         logging.info("Error while running command - " + str(e))
#                         return jsonify({"error": e}), 500
#                     # Send the weather data back to the GPT
#                     messages.append({"role": "tool", "name": "run_kubectl_command", "content": answer})
#                     response = openai.chat.completions.create(
#                         model="gpt-4-turbo",
#                         messages=messages
#                     )
#                     logging.info("Got response after running k8s command - %s", response)
#         return jsonify(response.dict())
#     except ValidationError as e:
#         return jsonify({"error": e.errors()}), 400
#
#
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=8000, debug=True)