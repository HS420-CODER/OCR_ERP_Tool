"""
ERP Arabic OCR Microservice - Gunicorn Configuration
=====================================================
Production WSGI server configuration for high-performance OCR processing.
"""

import os
import multiprocessing

# ==============================================================================
# Server Socket
# ==============================================================================

# Bind to localhost for reverse proxy setup (Apache/nginx)
bind = os.getenv("GUNICORN_BIND", "127.0.0.1:8000")

# Alternative: bind to all interfaces for direct access
# bind = "0.0.0.0:8000"

# Backlog - number of pending connections
backlog = int(os.getenv("GUNICORN_BACKLOG", "2048"))

# ==============================================================================
# Worker Processes
# ==============================================================================

# Worker count formula: (2 * CPU cores) + 1
# For OCR workloads (CPU-intensive), use fewer workers
# For I/O-bound workloads, use more workers
workers = int(os.getenv("GUNICORN_WORKERS", (multiprocessing.cpu_count() * 2) + 1))

# Worker class
# - sync: Simple synchronous workers (default)
# - gevent: Async workers for high concurrency (pip install gevent)
# - gthread: Threaded workers
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")

# Threads per worker (for gthread worker class)
# OCR processing benefits from multiple threads
threads = int(os.getenv("GUNICORN_THREADS", "2"))

# Maximum concurrent connections per worker (for async workers)
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "1000"))

# ==============================================================================
# Timeouts
# ==============================================================================

# Worker timeout (seconds)
# OCR processing can take time, especially for large documents
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

# Graceful timeout (seconds)
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# Keep-alive timeout (seconds)
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# ==============================================================================
# Worker Lifecycle
# ==============================================================================

# Maximum requests before worker restart (prevents memory leaks)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))

# Random jitter to prevent all workers restarting simultaneously
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))

# Preload application code before forking workers
# Saves memory but requires careful handling of resources
preload_app = os.getenv("GUNICORN_PRELOAD", "false").lower() == "true"

# ==============================================================================
# Logging
# ==============================================================================

# Access log
# - "-" for stdout
# - path for file
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")

# Error log
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")

# Log level: debug, info, warning, error, critical
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Access log format
# Common Log Format with additional OCR-specific fields
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
)
# %(h)s - remote address
# %(l)s - '-' (identd)
# %(u)s - user name (or '-')
# %(t)s - date/time
# %(r)s - request line
# %(s)s - status code
# %(b)s - response length
# %(f)s - referrer
# %(a)s - user agent
# %(D)s - request time in microseconds

# Capture stdout/stderr from workers
capture_output = True

# Enable request line logging even if not using access log
enable_stdio_inheritance = True

# ==============================================================================
# Process Naming
# ==============================================================================

# Process name prefix
proc_name = os.getenv("GUNICORN_PROC_NAME", "ocr-microservice")

# ==============================================================================
# Security
# ==============================================================================

# Limit request line size (default 4094)
limit_request_line = int(os.getenv("GUNICORN_LIMIT_REQUEST_LINE", "4094"))

# Limit HTTP headers
limit_request_fields = int(os.getenv("GUNICORN_LIMIT_REQUEST_FIELDS", "100"))

# Limit header field size
limit_request_field_size = int(os.getenv("GUNICORN_LIMIT_REQUEST_FIELD_SIZE", "8190"))

# ==============================================================================
# Server Mechanics
# ==============================================================================

# Daemonize (run in background)
# Usually False when managed by systemd/supervisor
daemon = False

# PID file
pidfile = os.getenv("GUNICORN_PID_FILE", None)

# User to run as (requires root to change)
user = os.getenv("GUNICORN_USER", None)

# Group to run as
group = os.getenv("GUNICORN_GROUP", None)

# Temp directory for worker heartbeat files
tmp_upload_dir = os.getenv("GUNICORN_TMP_DIR", None)

# ==============================================================================
# SSL (if not using reverse proxy for SSL termination)
# ==============================================================================

# SSL certificate file
# certfile = os.getenv("GUNICORN_SSL_CERT", None)

# SSL key file
# keyfile = os.getenv("GUNICORN_SSL_KEY", None)

# SSL ciphers
# ssl_version = ssl.PROTOCOL_TLS
# ciphers = 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256'

# ==============================================================================
# Hooks
# ==============================================================================

def on_starting(server):
    """Called before master process is initialized."""
    print(f"Starting OCR Microservice: {workers} workers, {threads} threads/worker")


def on_reload(server):
    """Called before reloading."""
    print("Reloading OCR Microservice configuration...")


def when_ready(server):
    """Called after server is ready to receive requests."""
    print(f"OCR Microservice ready at {bind}")


def worker_int(worker):
    """Called when a worker receives INT or QUIT signal."""
    print(f"Worker {worker.pid} interrupted")


def worker_abort(worker):
    """Called when a worker receives SIGABRT signal."""
    print(f"Worker {worker.pid} aborted")


def pre_fork(server, worker):
    """Called before a worker is forked."""
    pass


def post_fork(server, worker):
    """Called after a worker is forked."""
    print(f"Worker {worker.pid} spawned")


def post_worker_init(worker):
    """Called after a worker has initialized the application."""
    print(f"Worker {worker.pid} initialized")


def worker_exit(server, worker):
    """Called when a worker exits."""
    print(f"Worker {worker.pid} exited")


def nworkers_changed(server, new_value, old_value):
    """Called when number of workers changes."""
    print(f"Workers changed: {old_value} -> {new_value}")


def on_exit(server):
    """Called before exiting Gunicorn."""
    print("OCR Microservice shutting down...")


# ==============================================================================
# Environment-Specific Configurations
# ==============================================================================

# Development overrides
if os.getenv("FLASK_ENV") == "development":
    workers = 2
    threads = 1
    loglevel = "debug"
    reload = True
    reload_engine = "auto"
    reload_extra_files = []

# Production optimizations
if os.getenv("FLASK_ENV") == "production":
    # Use uvloop if available (requires: pip install uvloop)
    try:
        import uvloop
        worker_class = "uvicorn.workers.UvicornWorker"
    except ImportError:
        pass

# ==============================================================================
# Recommended Production Settings Summary
# ==============================================================================
#
# For a typical OCR workload on a 4-core server:
#   workers = 9              # (4 * 2) + 1
#   threads = 2              # 2 threads per worker
#   timeout = 120            # OCR can be slow
#   max_requests = 1000      # Prevent memory leaks
#   worker_class = "gthread" # Threaded workers
#
# Memory usage estimate:
#   Base: ~500MB (PaddleOCR + EasyOCR models)
#   Per worker: ~200MB additional
#   Total for 9 workers: ~2.3GB RAM recommended
#
# ==============================================================================
