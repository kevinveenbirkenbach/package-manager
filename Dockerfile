FROM python:3.11-slim

# Install system dependencies (make, pip) as per README
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    make \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Ensure local bin is in PATH (for aliases) as per README
ENV PATH="/root/.local/bin:$PATH"

# Create and activate a virtual environment
ENV VIRTUAL_ENV=/root/.venvs/pkgmgr
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy local package-manager source into the image
WORKDIR /root/Repositories/github.com/kevinveenbirkenbach/package-manager
COPY . .

# Install Python dependencies and set up the tool non-interactively
RUN pip install --upgrade pip \
    && pip install PyYAML \
    && chmod +x main.py \
    && python main.py install package-manager --no-verification --quiet

# Default entrypoint for pkgmgr
ENTRYPOINT ["pkgmgr"]
CMD ["--help"]
