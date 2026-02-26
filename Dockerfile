
FROM python:3.13.7-alpine

ENV PYTHONUNBUFFERED=1
ARG REQSTOOL_VERSION

LABEL org.opencontainers.image.title="reqstool"
LABEL org.opencontainers.image.description="This is custom Docker Image for reqstool."
LABEL org.opencontainers.image.authors=""
LABEL org.opencontainers.image.vendor="reqstool"
LABEL org.opencontainers.image.documentation="https://github.com/reqstool/reqstool-client/blob/main/README.md"
LABEL org.opencontainers.image.source="https://github.com/reqstool/reqstool-client"
LABEL org.opencontainers.image.url="https://github.com/reqstool/reqstool-client"

RUN pip install --no-cache-dir "reqstool==${REQSTOOL_VERSION}"

