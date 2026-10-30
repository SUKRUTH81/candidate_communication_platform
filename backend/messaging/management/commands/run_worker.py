"""Background worker: sends queued/scheduled messages, retries, recovers crashes, reconciles statuses.

    python manage.py run_worker            # run forever
    python manage.py run_worker --once     # one cycle (tests / cron)
"""
import logging
import signal
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from messaging import services

log = logging.getLogger("worker")


class Command(BaseCommand):
    help = "Process the message queue."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=1.0)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, interval, once, **opts):
        stop = {"flag": False}
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: stop.update(flag=True))
        breaker, last_reconcile = services.CircuitBreaker(), 0.0
        log.info("Worker started")
        while not stop["flag"]:
            try:
                close_old_connections()
                services.beat()
                services.recover_stale()
                services.run_due_messages(breaker)
                if time.monotonic() - last_reconcile > 15:
                    last_reconcile = time.monotonic()
                    services.reconcile()
            except Exception:
                log.exception("Worker cycle failed; continuing")
            if once:
                break
            time.sleep(interval)
        log.info("Worker stopped")
