#!/usr/bin/env python3

import logging
import re
import subprocess
import threading
import time

from prometheus_client import Counter, Gauge, start_http_server

# @TODO: just in case,dynamically check system page size?
PAGE_SIZE = 4096

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
container_oomkills_oc_pages = Gauge(
    "container_oomkills_oc_pages",
    f"Number of pages in OOM control (usually {PAGE_SIZE} bytes per page)",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_oc_bytes = Gauge(
    "container_oomkills_oc_bytes",
    f"Number of bytes in OOM control (oc_pages * {PAGE_SIZE})",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_unreliable_process_stat_rss_pages = Gauge(
    "container_oomkills_unreliable_process_stat_rss_pages",
    f"rss of OOM killed process in number of pages (usually {PAGE_SIZE} bytes per page), unreliable value from /proc/PID/stat",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_unreliable_process_stat_rss_bytes = Gauge(
    "container_oomkills_unreliable_process_stat_rss_bytes",
    f"rss of OOM killed process in bytes (rss_pages * {PAGE_SIZE}), unreliable value from /proc/PID/stat",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_unreliable_process_stat_vsize_bytes = Gauge(
    "container_oomkills_unreliable_process_stat_vsize_bytes",
    "vsize of OOM killed process in bytes, unreliable value from /proc/PID/stat",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_unreliable_process_stat_minflt = Gauge(
    "container_oomkills_unreliable_process_stat_minflt",
    "minflt of OOM killed process, unreliable value from /proc/PID/stat",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_unreliable_process_stat_majflt = Gauge(
    "container_oomkills_unreliable_process_stat_majflt",
    "majflt of OOM killed process, unreliable value from /proc/PID/stat",
    [
        "container_id",
        "command",
    ],
)


def parse_line(line):
    """Parse bpftrace output line and update metrics"""
    try:
        logging.debug(f"Parsing line: {line}")
        # Example line format:
        # 2025-06-02 11:00:53,435 probe="kprobe:oom_kill_process" host_pid="16478" container_id="f1f8308e277d" cgroup_path="unified:/docker/f1f8308e277d7df58daef7aba869a6f1eb6c42187f061169d2fc4d55c567b571,cgroup:/docker/f1f8308e277d7df58daef7aba869a6f1eb6c42187f061169d2fc4d55c567b571" command="python3" total_pages="32768" message="OOM kill in container f1f8308e277d (python3)" stat=16478 (python3) R 16412 16478 16478 0 -1 4195596 28169 0 111 0 2 17 0 0 20 0 1 0 9857125 0 0 18446744073709551615 0 0 0 0 0 0 0 16781312 2 0 0 0 17 0 0 0 0 0 0 0 0 0 0 0 0 0 9
        match = re.match(
            r'.*probe="kprobe:oom_kill_process" host_pid="(\d+)" container_id="([^"]*)" cgroup_path="([^"]*)" command="([^"]+)" total_pages="(\d+)" stat=(.*)',
            line,
        )

        if not match:
            return

        (
            host_pid,
            container_id,
            cgroup_path,
            command,
            total_pages,
            stat,
        ) = match.groups()

        # Update OOM kill metrics
        container_oomkills_total.labels(
            container_id=container_id,
            command=command,
        ).inc()

        stats = stat.split()

        container_oomkills_oc_pages.labels(
            container_id=container_id,
            command=command,
        ).set(int(total_pages))

        container_oomkills_oc_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(total_pages) * PAGE_SIZE)

        # start: unreliable values from /proc/PID/stat
        # @TODO: check process flags properly for (PF_SIGNALED | PF_EXITING)
        # https://github.com/torvalds/linux/blob/master/include/linux/sched.h#L1709-L1745
        if int(stats[8]) == 4195596 or int(stats[8]) == 4195404:
            logging.warning(
                f"Process exited before being able to check /proc/PID/stat, flags: {stats[8]}"
            )
        else:
            # only emit metrics if process is not yet exiting, hence we can get proper values from /proc/PID/stat
            container_oomkills_unreliable_process_stat_rss_pages.labels(
                container_id=container_id,
                command=command,
            ).set(int(stats[23]))

            container_oomkills_unreliable_process_stat_rss_bytes.labels(
                container_id=container_id,
                command=command,
            ).set(int(stats[23]) * PAGE_SIZE)

            container_oomkills_unreliable_process_stat_vsize_bytes.labels(
                container_id=container_id,
                command=command,
            ).set(int(stats[22]))

            container_oomkills_unreliable_process_stat_minflt.labels(
                container_id=container_id,
                command=command,
            ).set(int(stats[9]))

            container_oomkills_unreliable_process_stat_majflt.labels(
                container_id=container_id,
                command=command,
            ).set(int(stats[11]))
        # end: unreliable values from /proc/PID/stat

        logging.info(
            f"Recorded OOM kill in container {container_id}, oc_bytes: {int(total_pages) * PAGE_SIZE}, vsize_bytes: {stats[22]}, rss_bytes: {int(stats[23]) * PAGE_SIZE}"
        )

    except Exception as e:
        logging.error(f"Error parsing line: {e}")


def run_bpftrace():
    """Run bpftrace and process its output"""
    cmd = ["bpftrace", "container_oomkill.bt"]
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
