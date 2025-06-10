FROM debian:stable-slim

# Install essential build tools and dependencies
RUN apt-get update && apt-get install -y \
    sudo \
    git \
    make \
    curl \
    bpftrace \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create dev user with sudo access
RUN useradd -m -s /bin/bash dev && \
    echo "dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dev && \
    chmod 0440 /etc/sudoers.d/dev

USER dev
WORKDIR /src

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/home/dev/.local/bin:${PATH}"

# Set up shell and switch to dev user
SHELL ["/bin/bash", "-c"]
