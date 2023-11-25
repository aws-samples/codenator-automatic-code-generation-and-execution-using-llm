from opensearchpy import OpenSearch, AWSV4SignerAuth, RequestsHttpConnection
import boto3

class AmazonOpenSearchServerless(BaseStore):
    def __init__(self, index, region:str , endpoint: str):
        self.index = index
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, region, service="aoss")
        self.client = OpenSearch(
            hosts=[{"host": endpoint, "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )

    def save(self, embedding, task_desc, code):
        task = {
          "embedding": embedding,
          "task_desc": task_desc,
          "code": code
        }

        response = self.client.index(
            index = self.index,
            body = task
        )

        return True if response.get("result") == "created" else False
    
    def search(self, embedding, limit=1):
        query = {
          "size": limit,
          "query": {
              "knn": {
                  "embedding": {
                      "vector": [0] * 1536,
                      "k": limit
                  }
              }
          }
        }

        response = self.client.search(
            body = query,
            index = self.index
        )
        hits = response.get("hits")
        if not isinstance(hits, dict):
            return []
        results = []
        for hit in hits.get("hits"):
            results.append(hit.get("_source"))
                        
        return  results
    
    def delete(self, _id):
        self.client.delete(
            index=self.index,
            id=_id
        )
    
    def list_tasks(self, limit=100):
        query = {
          "size": limit,
          "query": {
              "match_all": {
              }
          }
        }

        response = self.client.search(
            body = query,
            index = self.index
        )
        hits = response.get("hits")
        if not isinstance(hits, dict):
            return []
                        
        return  hits.get("hits", [])

        
        
        