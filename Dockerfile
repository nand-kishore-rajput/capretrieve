FROM python:3.13.11-slim

WORKDIR /workspace

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e ".[dev]"

CMD ["/bin/bash"]