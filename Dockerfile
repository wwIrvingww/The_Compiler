# Use an official Python base image
FROM python:3.12-slim

# Install dependencies for ANTLR and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre \
    curl \
    unzip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install ANTLR4
ENV ANTLR_VERSION=4.13.1
RUN curl -O https://www.antlr.org/download/antlr-${ANTLR_VERSION}-complete.jar && \
    mv antlr-${ANTLR_VERSION}-complete.jar /usr/local/lib/ && \
    echo 'alias antlr4="java -jar /usr/local/lib/antlr-${ANTLR_VERSION}-complete.jar"' >> ~/.bashrc && \
    echo 'alias grun="java org.antlr.v4.gui.TestRig"' >> ~/.bashrc



WORKDIR /app
COPY requirements.txt .
COPY src ./src
COPY tests ./tests
RUN pip install --no-cache-dir -r requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt


# Ensure pip is up-to-date
RUN pip install --upgrade pip

# Install some useful dev pip packages
RUN pip install ipython black mypy pylint pytest

# Set working directory
WORKDIR /app

# Optional: mount local source code here at runtime
# (done via docker run -v $(pwd):/app)

# Default shell
CMD ["/bin/bash"]
