# Build Go
FROM golang:1.21-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . ./
RUN CGO_ENABLED=1 GOOS=linux go build -o server .

# Build Vue
FROM node:20-alpine AS web-builder
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN npm install
COPY web/ ./
RUN npm run build

# Final image
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates sqlite3 && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY --from=builder /app/server ./
COPY --from=web-builder /web/dist ./dist

RUN mkdir -p data

EXPOSE 60418

CMD ["./server"]