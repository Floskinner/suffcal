FROM python:3.13
COPY --from=docker.io/astral/uv:0.9.8 /uv /uvx /bin/

ENV PATH="/app/.venv/bin:${PATH}"
ENV PADDLE_OCR_BASE_DIR="/app/downloads/models/paddle_ocr"

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        ffmpeg \
        libsm6 \
        libxext6

COPY . /app
WORKDIR /app

RUN uv sync --no-dev --frozen

RUN mkdir -p /app/downloads/models /app/downloads/instagram

VOLUME [ "/app/downloads" ]

CMD ["suffcal", "--help" ]
