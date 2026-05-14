"""Gunicorn production configuration for Facebook Ad Scaler."""
import multiprocessing

# Server socket
bind = "0.0.0.0:8080"

# Worker processes
workers = max(2, int(multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
threads = 2

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "ad-scaler"

# Server mechanics
max_requests = 1000
max_requests_jitter = 50


def post_fork(server, worker):
    """Start scheduler in each worker after fork."""
    try:
        import scheduler
        scheduler.start()
        server.log.info("Scheduler started in worker")
    except Exception as e:
        server.log.error(f"Failed to start scheduler: {e}")


def worker_exit(server, worker):
    """Stop scheduler when worker exits."""
    try:
        import scheduler
        scheduler.stop()
    except Exception:
        pass
