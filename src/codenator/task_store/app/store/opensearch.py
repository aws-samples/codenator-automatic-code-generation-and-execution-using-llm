from opensearchpy import OpenSearch, AWSV4SignerAuth, RequestsHttpConnection
from store.base import BaseStore
from utils import Euclidean_distance, cosine_similarity
import boto3
import os

scoring = {
    "Euclidean": Euclidean_distance,
    "Cosine": cosine_similarity
}

class AOSSStore(BaseStore):
    def __init__(self, similarity="Cosine"):
        super().__init__()
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, self.region, service="aoss")
        self.client = OpenSearch(
            hosts=[{"host": self.endpoint, "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )
        self.scorer = scoring[similarity]
        try:
            response = self.client.get(index="_all")
            if self.index not in response:
                index_body = {
                    "settings": {
                        "index": {
                            "knn": True,
                            "knn.algo_param.ef_search": 512
                        }
                    },
                    "mappings": {
                        "properties": {
                            "embedding": {
                                "type": "knn_vector",
                                "dimension": 1536,
                                "method": {
                                    "name": "hnsw",
                                    "engine": "nmslib",
                                    "parameters": {},
                                    "space_type": "cosinesimil"
                                }
                            }
                        }
                    }
                }
                response = self.client.indices.create(self.index, body=index_body)
        except Exception as e:
            raise e

    def get_config(self):
        return {
            "index": os.getenv("AOSS_INDEX", "task-store-index"),
            "region": os.getenv("AWS_REGION", "us-east-1"),
            "endpoint": os.getenv("AOSS_ENDPOINT", "")
        }

    def save(self, embedding, task_desc, code, language):
        task = {
            "embedding": embedding,
            "task_desc": task_desc,
            "code": code,
            "language": language
        }

        response = self.client.index(
            index = self.index,
            body = task
        )

        return True if response.get("result") == "created" else False
    
    def search(self, embedding, threshold=0.1, limit=1):
        query = {
          "size": limit,
          "query": {
              "knn": {
                  "embedding": {
                      "vector": embedding,
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
            res_embedding = hit.get("_source")["embedding"]
            if self.scorer(embedding, res_embedding) <= threshold:
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

        
        
        