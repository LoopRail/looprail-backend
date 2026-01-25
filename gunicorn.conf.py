import os

bind = "0.0.0.0:8000"
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
loglevel = os.environ.get("LOG_LEVEL", "info")
accesslog = "-"
errorlog = "-"
backlog = 2048
timeout = 5
graceful_timeout = 30
max_requests = 10000
limit_concurrency = 1000
proxy_headers = True
forwarded_allow_ips = ""
reload = os.environ.get("ENVIRONMENT", "dev") == "dev"
