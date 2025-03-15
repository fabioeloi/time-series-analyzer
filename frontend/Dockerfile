FROM node:16-alpine AS builder

# Install Python and build dependencies
RUN apk add --no-cache python3 make g++

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
COPY tsconfig.json ./
RUN npm ci --quiet

# Copy source code and build
COPY . .
RUN npm run build

# Production stage
FROM node:16-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/build ./build

# Create non-root user
RUN addgroup -S appgroup && \
    adduser -S appuser -G appgroup && \
    chown -R appuser:appgroup /app

USER appuser
EXPOSE 3000
CMD ["serve", "-s", "build"]