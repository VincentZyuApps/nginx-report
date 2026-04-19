FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY server /app/server
COPY index.html /app/index.html

EXPOSE 8080

CMD ["/app/server"]