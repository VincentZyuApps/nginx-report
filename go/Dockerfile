# Build Go
FROM golang:1.21-alpine AS builder

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
FROM alpine:latest
RUN apk --no-cache add ca-certificates sqlite
WORKDIR /app

COPY --from=builder /app/server ./
COPY --from=web-builder /web/dist ./dist

RUN mkdir -p data

EXPOSE 60418

CMD ["./server"]