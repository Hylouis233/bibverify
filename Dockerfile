ARG PYTHON_IMAGE=python:3.13-slim-bookworm@sha256:00faa2debb87529f9f0764e9491d8ba400a3678976616c3bd7cb193745ac20d1
FROM ${PYTHON_IMAGE} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY . .

RUN python -m pip wheel --wheel-dir /wheels .

FROM ${PYTHON_IMAGE}

LABEL org.opencontainers.image.title="Bibverify" \
      org.opencontainers.image.description="Cross-platform BibTeX verification CLI and MCP server" \
      org.opencontainers.image.source="https://github.com/Hylouis233/bibverify" \
      org.opencontainers.image.licenses="MIT" \
      io.modelcontextprotocol.server.name="io.github.Hylouis233/bibverify"

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-index --find-links=/wheels bibverify \
    && rm -rf /wheels \
    && useradd --create-home --uid 10001 bibverify \
    && mkdir /workspace \
    && chown bibverify:bibverify /workspace \
    && bibverify --version

USER 10001:10001
WORKDIR /workspace
ENTRYPOINT ["bibverify"]
CMD ["mcp", "--workspace-root", "/workspace"]
