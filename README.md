## Introduction
An AI agent capable of interacting with a K8s cluster and accurately answer queries about applications deployed in the cluster.

### Requirements
- Python 3.10
- The kubeconfig file to be located at `~/.kube/config`

### Environment variables
- An API key should be passed as `OPENAI_API_KEY` to the environment before running the script.

### API Specifications
- URL: `http://localhost:8000/query`
- Port: 8000
- Payload format:
  ```json
  {
      "query": "How many pods are in the default namespace?"
  }
  ```
- Response format (using Pydantic):
  ```python
  from pydantic import BaseModel

  class QueryResponse(BaseModel):
      query: str
      answer: str
  ```

## Running locally
1. Install [Minikube](https://minikube.sigs.k8s.io/docs/start/)
2. Set up a local Kubernetes cluster
3. Deploy sample applications
4. Run the AI agent and test with sample queries
