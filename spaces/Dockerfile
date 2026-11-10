# Optional self-host / future PRO Docker deploy only.
# The public Hugging Face Space is Gradio + ZeroGPU (spaces/app.py), not this Docker path.
# Build from the repository root:
#   docker build -f spaces/Dockerfile .
FROM python:3.11-slim-bookworm

RUN useradd --create-home --uid 1000 user

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY spaces/start.sh /app/start.sh

RUN mkdir -p /tmp/codebuddy-data /app/backend/data \
    && chmod 755 /app/start.sh \
    && chown -R user:user /app /tmp/codebuddy-data

USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite+aiosqlite:////tmp/codebuddy-data/codebuddy.db \
    CODEBUDDY_SPACE_DEMO=1 \
    CODEBUDDY_API=http://127.0.0.1:8000

EXPOSE 7860

CMD ["/app/start.sh"]
