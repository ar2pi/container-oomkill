FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y \
    linux-headers-generic \
    bpftrace \
    python3 \
    python3-prometheus-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY coomkill.bt exporter.py /app

EXPOSE 9090

CMD ["/app/exporter.py"]
