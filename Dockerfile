FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git openssh-client \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY pyproject.toml ./
COPY scripts/csf.sh /etc/profile.d/csf.sh

RUN chmod 0644 /etc/profile.d/csf.sh \
  && printf '\n# Load CSF helper function\n[ -f /etc/profile.d/csf.sh ] && . /etc/profile.d/csf.sh\n' >> /etc/bash.bashrc

RUN uv sync --all-groups --no-install-project

ENV PATH="/opt/venv/bin:$PATH"
