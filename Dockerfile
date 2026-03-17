# Production image — multi-stage build
# Stage 1: install dependencies
FROM python:3.13-slim AS builder

WORKDIR /build

COPY requirements/ requirements/
RUN pip install --no-cache-dir --upgrade pip --root-user-action=ignore && \
    pip install --no-cache-dir --prefix=/install --root-user-action=ignore -r requirements/prod.txt


# Stage 2: lean runtime image
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy project source
COPY app/ app/

# Copy entrypoint script
COPY scripts/docker-entrypoint.sh /entrypoint.sh

# Create non-root user for security
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chmod +x /entrypoint.sh && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
