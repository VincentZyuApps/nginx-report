# Build Go
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod ./
RUN go mod download
COPY go/ ./
RUN CGO_ENABLED=1 GOOS=linux go build -o server .

# Build Vue
FROM node:20-alpine AS web-builder
WORKDIR /web
COPY go/web/package.json go/web/package-lock.json* ./
RUN npm install
COPY go/web/ ./
RUN npm run build

# Final image
FROM alpine:latest
RUN apk --no-cache add ca-certificates sqlite
WORKDIR /app

COPY --from=builder /app/server ./
COPY --from=web-builder /web/dist ./dist

RUN mkdir -p data

EXPOSE 60418

CMD ["./server"]