import os

port = os.environ.get("PORT", "8080")
bind = f"0.0.0.0:{port}"

workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
loglevel = "info"
accesslog = "-"
errorlog = "-"
timeout = 120
graceful_timeout = 30
keepalive = 5
proxy_headers = True
forwarded_allow_ips = "*"
