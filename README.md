# container-oomkill (WIP)

[Probe Docker image](https://hub.docker.com/repository/docker/ar2pi/container-oomkill-probe/general) | [Exporter Docker image](https://hub.docker.com/repository/docker/ar2pi/container-oomkill-exporter/general)

eBPF tool to troubleshoot container OOM kills. Consists of an eBPF probe and a Prometheus exporter to expose `container_oomkill_*` metrics.

## Run

Single probe
```sh
docker run --privileged --pid=host -v /sys:/sys:ro ar2pi/container-oomkill-probe
```

Local project with the exporter
```sh
make up
```

| Service | URL | Credentials |
|---------|-----|-------------|
| Prometheus exporter | http://localhost:9262 | - |
| Prometheus UI | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | user: admin, password: admin |

## Build

```sh
# Build the probe
docker build -t container-oomkill-probe .

# Build the exporter
docker build -t container-oomkill-exporter -f Dockerfile.exporter .
```

Build and push all at once
```sh
make push
```

## Debug

```sh
# tail journal logs
sudo journalctl -k -f | grep -B 90 -i 'out of memory'

# list oom kernel probes
docker exec -it container-oomkill-exporter-1 bpftrace -l "kprobe:oom*"

docker container logs -f container-oomkill-exporter-1

docker exec -it container-oomkill-exporter-1 ./container_oomkill.bt

docker exec -it container-oomkill-exporter-1 bash
  # memory usage in bytes
  $ cat /sys/fs/cgroup/docker/CONTAINER_ID/memory.current
  # memory hard limit in bytes
  # e.g.: 671088640 => 640MiB
  $ cat /sys/fs/cgroup/docker/CONTAINER_ID/memory.max
  # memory soft request in bytes
  # e.g.: 67108864 => 64MiB
  $ cat /sys/fs/cgroup/docker/CONTAINER_ID/memory.low
  
# enter docker-desktop ns (useful on macos)
docker run -it --privileged --pid=host debian:stable-slim nsenter -t 1 -m -u -n -i bash
```

## Resources

[bpftrace](https://github.com/bpftrace/bpftrace)
- [oomkill.bt](https://github.com/bpftrace/bpftrace/blob/master/tools/oomkill.bt)

- [Memory Management in Linux - Concepts overview](https://docs.kernel.org/admin-guide/mm/concepts.html)
- [cgroups v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
- [bpftrace in docker](https://hemslo.io/run-ebpf-programs-in-docker-using-docker-bpf/)
- [Out-of-memory victim selection with BPF](https://lwn.net/Articles/941614/)
- [oom_kill.c](https://github.com/torvalds/linux/blob/master/mm/oom_kill.c#L1112)
- [oom_score](https://elixir.bootlin.com/linux/v6.15/source/fs/proc/base.c#L585) -> https://github.com/torvalds/linux/blob/master/Documentation/filesystems/proc.rst#32-procpidoom_score---display-current-oom-killer-score
- [oom_badness](https://elixir.bootlin.com/linux/v6.15/source/mm/oom_kill.c#L227-L232)
- [oc<oom_control>](https://github.com/torvalds/linux/blob/master/include/linux/oom.h#L28) > [memcg<mem_cgroup>](https://github.com/torvalds/linux/blob/master/include/linux/memcontrol.h#L177-L312) | [chosen<task_struct>](https://github.com/torvalds/linux/blob/master/include/linux/sched.h#L816-L1665) > [mm<mm_struct>](https://github.com/torvalds/linux/blob/master/include/linux/mm_types.h#L933-L1216)

    > Simple selection loop. We choose the process with the highest number of 'points'. In case scan was aborted, oc->chosen is set to -1.
    
    > The baseline for the badness score is the proportion of RAM that each task's rss, pagetable and swap space use.

    > ```
    > /**
    > * out_of_memory - kill the "best" process when we run out of memory
    > * @oc: pointer to struct oom_control
    > *
    > * If we run out of memory, we have the choice between either
    > * killing a random task (bad), letting the system crash (worse)
    > * OR try to be smart about which process to kill. Note that we
    > * don't have to be perfect here, we just have to be good.
    > */
    > bool out_of_memory(struct oom_control *oc)
    > ```
    > https://github.com/torvalds/linux/blob/master/mm/oom_kill.c#L1103-L1112

    > ```
    > /**
    > * oom_badness - heuristic function to determine which candidate task to kill
    > * @p: task struct of which task we should calculate
    > * @totalpages: total present RAM allowed for page allocation
    > *
    > * The heuristic for determining which task to kill is made to be as simple and
    > * predictable as possible.  The goal is to return the highest value for the
    > * task consuming the most memory to avoid subsequent oom failures.
    > */
    > long oom_badness(struct task_struct *p, unsigned long totalpages)
    > ```
    > https://github.com/torvalds/linux/blob/master/mm/oom_kill.c#L193-L202

    ```
    out_of_memory -> select_bad_process -> mem_cgroup_scan_tasks -> oom_evaluate_task -> oom_badness
    
    oom_badness points = (get_mm_rss(p->mm) + get_mm_counter(p->mm, MM_SWAPENTS) + mm_pgtables_bytes(p->mm) / PAGE_SIZE) + totalpages / 1000;  
        = (
            (
                get_mm_counter(mm, MM_FILEPAGES) 
                + get_mm_counter(mm, MM_ANONPAGES) 
                + get_mm_counter(mm, MM_SHMEMPAGES)
            ) 
            + get_mm_counter(p->mm, MM_SWAPENTS) 
            + mm_pgtables_bytes(p->mm) / PAGE_SIZE
        ) + oom_score_adj * totalpages / 1000;
    ```
    ```
    enum {
        MM_FILEPAGES,	/* Resident file mapping pages */
        MM_ANONPAGES,	/* Resident anonymous pages */
        MM_SWAPENTS,	/* Anonymous swap entries */
        MM_SHMEMPAGES,	/* Resident shared memory pages */
    ```
    https://github.com/torvalds/linux/blob/master/include/linux/mm_types_task.h#L26-L30

    For obtaining file, anon, shmem see task_mmu https://github.com/torvalds/linux/blob/master/fs/proc/task_mmu.c#L39-L55

    oom_score_adj: user defined value between [-1000, 1000], -1000 disables oom killing for pid
    https://github.com/torvalds/linux/blob/master/include/uapi/linux/oom.h#L5-L10
    https://github.com/torvalds/linux/blob/master/Documentation/filesystems/proc.rst#31-procpidoom_adj--procpidoom_score_adj--adjust-the-oom-killer-score

    oom_adj: legacy param, prefer to use oom_score_adj

## @TODO:

- [ ] dev container
- [ ] build grafana dashboard
- [ ] try it out in kubernetes
- [ ] build container-oomkill-exporter image and push to public repository
