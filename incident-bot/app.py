import os
import threading
from datetime import datetime, timezone

import requests
from flask import Flask, Response, request
from kubernetes import client, config

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODELS = [m.strip() for m in os.environ.get(
    "GEMINI_MODELS",
    "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-2.5-flash",
).split(",") if m.strip()]

INCIDENTS = []
LOCK = threading.Lock()

try:
    config.load_incluster_config()
    core = client.CoreV1Api()
    apps = client.AppsV1Api()
except Exception:
    core = apps = None


def gather_context(labels):
    ns = labels.get("namespace", "default")
    dep = labels.get("deployment")
    ctx = {"namespace": ns, "deployment": dep}
    if core is None:
        ctx["context_error"] = "no kubernetes access"
        return ctx
    try:
        if dep:
            d = apps.read_namespaced_deployment(dep, ns)
            ctx["deployment_status"] = {
                "desired": d.spec.replicas,
                "ready": d.status.ready_replicas or 0,
                "available": d.status.available_replicas or 0,
            }
        pods = core.list_namespaced_pod(ns).items
        ctx["pods"] = [{
            "name": p.metadata.name,
            "phase": p.status.phase,
            "restarts": sum(c.restart_count for c in (p.status.container_statuses or [])),
        } for p in pods]
        warns = [e for e in core.list_namespaced_event(ns).items if e.type == "Warning"]
        ctx["warning_events"] = [
            {"reason": e.reason, "message": (e.message or "")[:200]} for e in warns[-5:]
        ]
    except Exception as e:
        ctx["context_error"] = str(e)[:200]
    return ctx


def build_prompt(alert, ctx):
    return (
        "You are an SRE assistant. A Prometheus alert fired on a Kubernetes cluster.\n"
        "Using only the data below, reply in plain text (no markdown) with exactly three sections:\n"
        "SUMMARY: two sentences.\n"
        "LIKELY CAUSE: one or two sentences.\n"
        "FIX STEPS: 3 to 5 numbered steps, with kubectl commands where useful.\n\n"
        f"Alert labels: {alert.get('labels', {})}\n"
        f"Alert annotations: {alert.get('annotations', {})}\n"
        f"Cluster context: {ctx}\n"
    )


def ask_llm(alert, ctx):
    if not API_KEY:
        raise RuntimeError("no GEMINI_API_KEY set")
    last = "no models configured"
    for model in MODELS:
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": build_prompt(alert, ctx)}]}]},
                timeout=30,
            )
            if r.status_code == 200:
                parts = r.json()["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    return model, text
                last = f"{model}: empty response"
            else:
                last = f"{model}: HTTP {r.status_code}"
        except Exception as e:
            last = f"{model}: {str(e)[:80]}"
    raise RuntimeError(last)


def rule_based(alert, ctx):
    ns = ctx.get("namespace", "default")
    dep = ctx.get("deployment") or "<deployment>"
    ds = ctx.get("deployment_status", {})
    if ds.get("desired") == 0:
        cause = f"Deployment {dep} is scaled to 0 replicas."
        steps = [
            f"kubectl scale deployment {dep} -n {ns} --replicas=2",
            f"kubectl rollout history deployment {dep} -n {ns}   (was the scale-down intentional?)",
        ]
    else:
        cause = f"Only {ds.get('available', '?')} of {ds.get('desired', '?')} pods are available."
        steps = [
            f"kubectl get pods -n {ns}",
            f"kubectl describe deployment {dep} -n {ns}",
            f"kubectl get events -n {ns} --sort-by=.lastTimestamp | tail",
            "kubectl describe nodes | grep -A5 Allocated",
        ]
    numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    return (
        f"SUMMARY: Alert {alert.get('labels', {}).get('alertname')} is firing for {dep} in {ns}.\n"
        f"LIKELY CAUSE: {cause}\n"
        f"FIX STEPS:\n{numbered}"
    )


def handle_alert(alert):
    ctx = gather_context(alert.get("labels", {}))
    try:
        model, text = ask_llm(alert, ctx)
        source = f"LLM ({model})"
    except Exception as e:
        text = rule_based(alert, ctx)
        source = f"rule-based fallback (LLM unavailable: {e})"
    record = {
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "alert": alert.get("labels", {}).get("alertname"),
        "source": source,
        "text": text,
    }
    with LOCK:
        INCIDENTS.insert(0, record)
    print(f"[incident] {record['alert']} via {source}", flush=True)


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json(force=True, silent=True) or {}
    for a in payload.get("alerts", []):
        if a.get("status") == "firing":
            threading.Thread(target=handle_alert, args=(a,), daemon=True).start()
    return {"received": True}


@app.route("/incidents")
def incidents():
    with LOCK:
        items = list(INCIDENTS)
    if not items:
        return Response("No incidents yet.\n", mimetype="text/plain")
    out = []
    for i in items:
        out.append(f"=== {i['time']} | {i['alert']} | {i['source']} ===\n{i['text']}\n")
    return Response("\n".join(out), mimetype="text/plain")


@app.route("/health")
def health():
    return {"status": "ok"}
