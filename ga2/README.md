# TDS GA2 services

FastAPI endpoints for statistics with CORS, RS256 verification, Redis counters,
analytics, live Prometheus metrics and structured logs, idempotent orders with
cursor pagination, per-client rate limits, and local Ollama inference.

Start: docker compose -f ga2/docker-compose.yml up -d --build

The API is available at port 8001. Redis and Ollama share a private network
namespace with the API; their ports are not published. Persistent Docker volumes
store Redis data and downloaded Ollama models. Initialize qwen2.5:0.5b before
checking inference endpoints. The ga2/bin/ollama wrapper invokes the real Ollama
binary in its container.

Recordings are excluded from git because signed receipts contain identity data.
Run python ga2/validate_recordings.py to validate the completed recordings and
package their archives. Publish them only with the account owner's permission.

Codespace endpoints require the Codespace to remain running; they can be
restarted with the Compose command before checking or saving the exam again.
