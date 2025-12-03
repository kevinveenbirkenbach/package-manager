FROM archlinux:latest

# Update system and install core tooling
RUN pacman -Syu --noconfirm \
    && pacman -S --noconfirm --needed \
        git \
        make \
        sudo \
        python \
        python-pip \
        python-virtualenv \
        python-setuptools \
        python-wheel \
    && pacman -Scc --noconfirm

# Ensure local bin is in PATH (for pkgmgr links)
ENV PATH="/root/.local/bin:$PATH"

# Create virtual environment
ENV VIRTUAL_ENV=/root/.venvs/pkgmgr
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Working directory for the package-manager project
WORKDIR /root/Repositories/github.com/kevinveenbirkenbach/package-manager

# Copy local package-manager source into container
COPY . .

# Install Python dependencies and register pkgmgr inside the venv
RUN pip install --upgrade pip \
    && pip install PyYAML \
    && chmod +x main.py \
    && python main.py install package-manager --quiet --clone-mode shallow --no-verification

# Copy again to allow rebuild-based code changes
COPY . .

ENTRYPOINT ["pkgmgr"]
CMD ["--help"]
