import time
from flask import Flask, Response, g, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

REQUESTS = Counter(
    "flask_http_requests_total", "Total HTTP requests",
    ["method", "endpoint", "status"],
)
LATENCY = Histogram(
    "flask_http_request_duration_seconds", "Request latency in seconds",
    ["endpoint"],
)


@app.before_request
def start_timer():
    g.start = time.time()


@app.after_request
def record_metrics(resp):
    endpoint = request.url_rule.rule if request.url_rule else "unmatched"
    if endpoint != "/metrics":
        LATENCY.labels(endpoint).observe(time.time() - g.start)
        REQUESTS.labels(request.method, endpoint, resp.status_code).inc()
    return resp


@app.route("/")
def index():
    return "Hello from the platform demo app\n"


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/error")
def error():
    return {"status": "error"}, 500


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
