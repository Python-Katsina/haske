# benchmarks/locustfile.py
from locust import HttpUser, task, between

class BenchmarkUser(HttpUser):
    wait_time = between(0.1, 0.5)
    
    @task
    def simple_get(self):
        self.client.get("/")
    
    @task
    def json_response(self):
        self.client.get("/json")
    
    @task
    def path_params(self):
        self.client.get("/users/123")
    
    @task
    def post_request(self):
        self.client.post("/users", json={"name": "test", "email": "test@example.com"})
    
    @task
    def template(self):
        self.client.get("/template")