#!/usr/bin/env python3

import logging
import re
import subprocess
import threading
import time

from prometheus_client import Counter, Gauge, start_http_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


# Prometheus metrics
container_oomkills_total = Counter(
    "container_oomkills_total",
    "Number of OOM kills",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_process_stat_rss = Gauge(
    "container_oomkills_process_stat_rss",
    "rss of OOM killed process",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_process_stat_vsize = Gauge(
    "container_oomkills_process_stat_vsize",
    "vsize of OOM killed process",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_process_stat_minflt = Gauge(
    "container_oomkills_process_stat_minflt",
    "minflt of OOM killed process",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_process_stat_majflt = Gauge(
    "container_oomkills_process_stat_majflt",
    "majflt of OOM killed process",
    [
        "container_id",
        "command",
    ],
)
# @TODO: add oom_score
# CONTAINER_OOMKILLS_OOM_SCORE = Gauge(
#    "container_oomkills_process_stat_oom_score",
#    "oom_score of OOM killed process",
#    [
#        "container_id",
#        "command",
#    ],
# )


def parse_line(line):
    """Parse bpftrace output line and update metrics"""
    try:
        logging.info(f"Parsing line: {line}")
        # Example line format:
        # 19:05:23 Triggered by PID 942 ("python3", "container1"), OOM kill of PID 942 ("python3", "container2"), 32768 pages, loadavg: 0.14 0.05 0.01 2/811 2773
        match = re.match(
            r'.*probe="kprobe:oom_kill_process" host_pid="(\d+)" container_id="([^"]+)" command="([^"]+)" total_pages="(\d+)" total_bytes="(\d+)" message="([^"]+)" stat=(.*)',
            line,
        )
        if match:
            (
                host_pid,
                container_id,
                command,
                total_pages,
                total_bytes,
                message,
                stat,
            ) = match.groups()

            # Update OOM kill metrics
            container_oomkills_total.labels(
                container_id=container_id,
                command=command,
            ).inc()

            stats = stat.split()

            container_oomkills_process_stat_rss.labels(
                container_id=container_id,
                command=command,
            ).set(stats[23])

            container_oomkills_process_stat_vsize.labels(
                container_id=container_id,
                command=command,
            ).set(stats[22])

            container_oomkills_process_stat_minflt.labels(
                container_id=container_id,
                command=command,
            ).set(stats[9])

            container_oomkills_process_stat_majflt.labels(
                container_id=container_id,
                command=command,
            ).set(stats[11])

            logging.info(
                f"Recorded OOM kill in container {container_id}, bytes: {total_bytes}"
            )
    except Exception as e:
        logging.error(f"Error parsing line: {e}")


def run_bpftrace():
    """Run bpftrace and process its output"""
    cmd = ["bpftrace", "coomkill.bt"]
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    for line in process.stdout:
        parse_line(line.strip())


def main():
    # Start Prometheus HTTP server
    start_http_server(9090)
    logging.info("Prometheus exporter started on port 9090")

    # Start bpftrace in a separate thread
    bpftrace_thread = threading.Thread(target=run_bpftrace, daemon=True)
    bpftrace_thread.start()

    # Keep the main thread alive
    while True:
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Shutting down...")
