# container-oomkill (WIP)

ePBF tool to troubleshoot container OOMs.

[bpftrace](https://github.com/bpftrace/bpftrace)
- [oomkill.bt](https://github.com/bpftrace/bpftrace/blob/master/tools/oomkill.bt)

## Run

```sh
make up
```

## Debug

```
docker container logs -f container-oomkill-exporter-1
docker exec -it container-oomkill-exporter-1 bash
```

## Resources

- [cgroups v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
- [bpftrace in docker](https://hemslo.io/run-ebpf-programs-in-docker-using-docker-bpf/)
- [Out-of-memory victim selection with BPF](https://lwn.net/Articles/941614/)

## @TODO:

- [ ] try it out in kubernetes
