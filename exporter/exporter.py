#!/usr/bin/env python3

import logging
import re
import subprocess
import threading
import time

from prometheus_client import Counter, Gauge, start_http_server

# @TODO: just in case, dynamically check system page size?
PAGE_SIZE = 4096

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


# Prometheus metrics
# Note: we avoid using pid as a label to prevent cardinality explosion
container_oomkills_total = Counter(
    "container_oomkills_total",
    "Number of OOM kills",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_oc_total_bytes = Gauge(
    "container_oomkills_oc_total_bytes",
    f"Number of bytes held by processes evaluated by OOM control, i.e. mem + swap (totalpages * {PAGE_SIZE})",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_oc_chosen_points = Gauge(
    "container_oomkills_oc_chosen_points",
    f"Number of oom_badness points for chosen process",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_cgroup_mem_usage_bytes = Gauge(
    "container_oomkills_cgroup_mem_usage_bytes",
    f"Number of bytes used by the container's memory cgroup",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_cgroup_mem_limit_bytes = Gauge(
    "container_oomkills_cgroup_mem_limit_bytes",
    f"Number of bytes limit of the container's memory cgroup",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_cgroup_mem_request_bytes = Gauge(
    "container_oomkills_cgroup_mem_request_bytes",
    f"Number of bytes request of the container's memory cgroup",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_cgroup_swap_usage_bytes = Gauge(
    "container_oomkills_cgroup_swap_usage_bytes",
    f"Number of bytes used by the container's swap cgroup",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_cgroup_swap_limit_bytes = Gauge(
    "container_oomkills_cgroup_swap_limit_bytes",
    f"Number of bytes limit of the container's swap cgroup",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_cgroup_swappiness = Gauge(
    "container_oomkills_cgroup_swappiness",
    f"Swappiness of the container's cgroup (0-100)",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_rss_filepages_bytes = Gauge(
    "container_oomkills_rss_filepages_bytes",
    f"Number of bytes used by file pages",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_rss_anonpages_bytes = Gauge(
    "container_oomkills_rss_anonpages_bytes",
    f"Number of bytes used by anonymous pages",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_rss_swapents_bytes = Gauge(
    "container_oomkills_rss_swapents_bytes",
    f"Number of bytes used by swap entries",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_rss_shmempages_bytes = Gauge(
    "container_oomkills_rss_shmempages_bytes",
    f"Number of bytes used by shared memory pages",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_pgtables_bytes = Gauge(
    "container_oomkills_pgtables_bytes",
    f"Number of bytes used by page tables",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_task_size = Gauge(
    "container_oomkills_task_size",
    f"Number of bytes used by the task's memory",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_hiwater_rss = Gauge(
    "container_oomkills_hiwater_rss",
    f"Number of bytes used by the task's RSS",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_hiwater_vm = Gauge(
    "container_oomkills_hiwater_vm",
    f"Number of bytes used by the task's VM",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_total_vm = Gauge(
    "container_oomkills_total_vm",
    f"Number of bytes used by the task's total VM",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_locked_vm = Gauge(
    "container_oomkills_locked_vm",
    f"Number of bytes used by the task's locked VM",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_pinned_vm = Gauge(
    "container_oomkills_pinned_vm",
    f"Number of bytes used by the task's pinned VM",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_data_vm = Gauge(
    "container_oomkills_data_vm",
    f"Number of bytes used by the task's data VM",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_exec_vm = Gauge(
    "container_oomkills_exec_vm",
    f"Number of bytes used by the task's exec VM",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_stack_vm = Gauge(
    "container_oomkills_stack_vm",
    f"Number of bytes used by the task's stack VM",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_oom_score_adj = Gauge(
    "container_oomkills_oom_score_adj",
    f"OOM score adjustment of the task",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_num_threads = Gauge(
    "container_oomkills_num_threads",
    f"Number of threads in the process",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_min_flt = Gauge(
    "container_oomkills_min_flt",
    f"Number of minor faults",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_maj_flt = Gauge(
    "container_oomkills_maj_flt",
    f"Number of major faults",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_flags = Gauge(
    "container_oomkills_flags",
    f"Flags of the process",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_prio = Gauge(
    "container_oomkills_prio",
    f"Priority of the process",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_static_prio = Gauge(
    "container_oomkills_static_prio",
    f"Static priority of the process",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_utime = Gauge(
    "container_oomkills_utime",
    f"User time of the process",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_stime = Gauge(
    "container_oomkills_stime",
    f"System time of the process",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_gtime = Gauge(
    "container_oomkills_gtime",
    f"Guest time of the process",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_start_time_ns = Gauge(
    "container_oomkills_start_time_ns",
    f"Start time of the process in nanoseconds",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_start_boottime_ns = Gauge(
    "container_oomkills_start_boottime_ns",
    f"Start time of the process since boot time in nanoseconds",
    [
        "container_id",
        "command",
    ],
)
container_oomkills_uptime_ms = Gauge(
    "container_oomkills_uptime_ms",
    f"Uptime of the system in milliseconds",
    [
        "container_id",
        "command",
    ],
)


def parse_line(line):
    """Parse bpftrace output line and update metrics"""
    try:
        logging.debug(f"Parsing line: {line}")
        # Examples:
        # 128MiB hard limit, no soft limit, no swap
        # 2025-06-03 16:22:12,894 probe="kprobe:oom_kill_process" host_pid="42748" container_id="257b1d14ce1c" cgroup_path="unified:/docker/257b1d14ce1c632d8d5ef53b9901f3b4583a4b95fe4bbb197623d59074059959,cgroup:/docker/257b1d14ce1c632d8d5ef53b9901f3b4583a4b95fe4bbb197623d59074059959" command="python3" oc_totalpages="32768" oc_chosen_points="33654" memcg_memory_usage_pages="32768" memcg_memory_max_pages="32768" memcg_memory_low_pages="0" memcg_swap_current_pages="0" memcg_swap_max_pages="0" memcg_swappiness="60" mm_rss_filepages="1301" mm_rss_anonpages="32245" mm_rss_swapents="0" mm_rss_shmempages="0" mm_pgtables_bytes="442368" mm_task_size="0" mm_hiwater_rss="3381" mm_hiwater_vm="4439" mm_total_vm="35325" mm_locked_vm="0" mm_pinned_vm="0" mm_data_vm="33456" mm_exec_vm="1615" mm_stack_vm="33" proc_num_threads="1" proc_min_flt="3773" proc_maj_flt="0" proc_flags="4194560" proc_prio="120" proc_static_prio="120" proc_utime="64000000" proc_stime="29000000" proc_gtime="0" proc_start_time_ns="170109788292976" proc_start_boottime_ns="170109788292976" uptime_ms="3106"
        # 128MiB hard limit, 64MiB soft limit, no swap
        # 2025-06-03 16:17:20,157 probe="kprobe:oom_kill_process" host_pid="41378" container_id="65a8b60c9857" cgroup_path="unified:/docker/65a8b60c9857747a01154894c0ceac7fd1003f0dd58e1a97964e5db091a81ffd,cgroup:/docker/65a8b60c9857747a01154894c0ceac7fd1003f0dd58e1a97964e5db091a81ffd" command="python3" oc_totalpages="32768" oc_chosen_points="33658" memcg_memory_usage_pages="32768" memcg_memory_max_pages="32768" memcg_memory_low_pages="16384" memcg_swap_current_pages="0" memcg_swap_max_pages="0" memcg_swappiness="60" mm_rss_filepages="1267" mm_rss_anonpages="32285" mm_rss_swapents="0" mm_rss_shmempages="0" mm_pgtables_bytes="434176" mm_task_size="0" mm_hiwater_rss="3299" mm_hiwater_vm="4439" mm_total_vm="35325" mm_locked_vm="0" mm_pinned_vm="0" mm_data_vm="33456" mm_exec_vm="1615" mm_stack_vm="33" proc_num_threads="1" proc_min_flt="6757" proc_maj_flt="0" proc_flags="4194560" proc_prio="120" proc_static_prio="120" proc_utime="76000000" proc_stime="30000000" proc_gtime="0" proc_start_time_ns="169818048811135" proc_start_boottime_ns="169818048811177" uptime_ms="3108"
        # 64MiB hard limit, 64MiB soft limit, 64MiB swap
        # 2025-06-03 16:15:11,491 probe="kprobe:oom_kill_process" host_pid="40464" container_id="85c60f0c4603" cgroup_path="unified:/docker/85c60f0c4603da90486468dd727752ad61d8425923376de7ef0fac897cc4f70b,cgroup:/docker/85c60f0c4603da90486468dd727752ad61d8425923376de7ef0fac897cc4f70b" command="python3" oc_totalpages="32768" oc_chosen_points="33472" memcg_memory_usage_pages="16384" memcg_memory_max_pages="16384" memcg_memory_low_pages="16384" memcg_swap_current_pages="16384" memcg_swap_max_pages="16384" memcg_swappiness="60" mm_rss_filepages="1317" mm_rss_anonpages="15697" mm_rss_swapents="16352" mm_rss_shmempages="0" mm_pgtables_bytes="434176" mm_task_size="0" mm_hiwater_rss="17494" mm_hiwater_vm="3432" mm_total_vm="35159" mm_locked_vm="0" mm_pinned_vm="0" mm_data_vm="33290" mm_exec_vm="1615" mm_stack_vm="33" proc_num_threads="1" proc_min_flt="18631" proc_maj_flt="161" proc_flags="4194560" proc_prio="120" proc_static_prio="120" proc_utime="24000000" proc_stime="84000000" proc_gtime="0" proc_start_time_ns="169688273567534" proc_start_boottime_ns="169688273567617" uptime_ms="3217"
        match = re.match(
            r'.*probe="kprobe:oom_kill_process" host_pid="(\d+)" container_id="([^"]*)" cgroup_path="([^"]*)" command="([^"]+)"(.*)',
            line,
        )

        if not match:
            return

        (
            host_pid,
            container_id,
            cgroup_path,
            command,
            stats,
        ) = match.groups()

        # Parse all key-value pairs in stats
        stats_kv = {k: v for k, v in re.findall(r'\s([^=]+)=\"([^"]*)\"', stats)}

        # Update OOM kill metrics
        container_oomkills_total.labels(
            container_id=container_id,
            command=command,
        ).inc()

        container_oomkills_oc_total_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["oc_totalpages"]) * PAGE_SIZE)
        container_oomkills_oc_chosen_points.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["oc_chosen_points"]))
        container_oomkills_cgroup_mem_usage_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["memcg_memory_usage_pages"]) * PAGE_SIZE)
        container_oomkills_cgroup_mem_limit_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["memcg_memory_max_pages"]) * PAGE_SIZE)
        container_oomkills_cgroup_mem_request_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["memcg_memory_low_pages"]) * PAGE_SIZE)
        container_oomkills_cgroup_swap_usage_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["memcg_swap_current_pages"]) * PAGE_SIZE)
        container_oomkills_cgroup_swap_limit_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["memcg_swap_max_pages"]) * PAGE_SIZE)
        container_oomkills_cgroup_swappiness.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["memcg_swappiness"]))
        container_oomkills_rss_filepages_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_rss_filepages"]) * PAGE_SIZE)
        container_oomkills_rss_anonpages_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_rss_anonpages"]) * PAGE_SIZE)
        container_oomkills_rss_swapents_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_rss_swapents"]) * PAGE_SIZE)
        container_oomkills_rss_shmempages_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_rss_shmempages"]) * PAGE_SIZE)
        container_oomkills_pgtables_bytes.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_pgtables_bytes"]))
        container_oomkills_task_size.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_task_size"]))
        container_oomkills_hiwater_rss.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_hiwater_rss"]))
        container_oomkills_hiwater_vm.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_hiwater_vm"]))
        container_oomkills_total_vm.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_total_vm"]))
        container_oomkills_locked_vm.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_locked_vm"]))
        container_oomkills_pinned_vm.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_pinned_vm"]))
        container_oomkills_data_vm.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_data_vm"]))
        container_oomkills_exec_vm.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_exec_vm"]))
        container_oomkills_stack_vm.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["mm_stack_vm"]))
        container_oomkills_oom_score_adj.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_oom_score_adj"]))
        container_oomkills_num_threads.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_num_threads"]))
        container_oomkills_min_flt.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_min_flt"]))
        container_oomkills_maj_flt.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_maj_flt"]))
        # arguably flags should be a label? worried about cardinality though
        container_oomkills_flags.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_flags"]))
        container_oomkills_prio.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_prio"]))
        container_oomkills_static_prio.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_static_prio"]))
        container_oomkills_utime.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_utime"]))
        container_oomkills_stime.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_stime"]))
        container_oomkills_gtime.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_gtime"]))
        container_oomkills_start_time_ns.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_start_time_ns"]))
        container_oomkills_start_boottime_ns.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["proc_start_boottime_ns"]))
        container_oomkills_uptime_ms.labels(
            container_id=container_id,
            command=command,
        ).set(int(stats_kv["uptime_ms"]))

        logging.info(
            f"Recorded OOM kill of {command} [{host_pid}] in container {container_id}, stats:{stats}"
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
