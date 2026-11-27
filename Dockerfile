FROM scratch AS wheels

FROM python:3.15.2-alpine

ENV PYTHONUNBUFFERED=1
ARG VERSION

LABEL org.opencontainers.image.title="reqstool"
LABEL org.opencontainers.image.description="This is custom Docker Image for reqstool."
LABEL org.opencontainers.image.authors=""
LABEL org.opencontainers.image.vendor="reqstool"
LABEL org.opencontainers.image.documentation="https://github.com/reqstool/reqstool-client/blob/main/README.md"
LABEL org.opencontainers.image.source="https://github.com/reqstool/reqstool-client"
LABEL org.opencontainers.image.url="https://github.com/reqstool/reqstool-client"

RUN --mount=type=bind,from=wheels,target=/wheels \
    set -- /wheels/reqstool-*.whl; \
    if [ ! -e "$1" ]; then set -- "reqstool==${VERSION}"; fi; \
    test $# -eq 1 || { echo "expected exactly one reqstool wheel in /wheels" >&2; exit 1; }; \
    pip install --no-cache-dir "$1"

