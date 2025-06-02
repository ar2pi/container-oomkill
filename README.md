# container-oomkill (WIP)

ePBF tool to troubleshoot container OOMs.

[bpftrace](https://github.com/bpftrace/bpftrace)
- [oomkill.bt](https://github.com/bpftrace/bpftrace/blob/master/tools/oomkill.bt)

```sh
make up

docker exec -it container-oomkill-exporter bash
```

Resources
- [cgroups v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
- [bpftrace in docker](https://hemslo.io/run-ebpf-programs-in-docker-using-docker-bpf/)
- [Out-of-memory victim selection with BPF](https://lwn.net/Articles/941614/)

@TODO:
- [ ] try it out in kubernetes
