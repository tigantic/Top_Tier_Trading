# syntax=docker/dockerfile:1.4

# Stage 1 – build the TypeScript application
FROM node:18 AS builder
WORKDIR /usr/src/app

# Copy dependency definitions
COPY package.json package-lock.json* ./

# Install dependencies with npm ci for reproducibility
RUN npm ci

# Copy source files
COPY tsconfig.json ./
COPY src ./src

# Compile TypeScript to JavaScript
RUN npm run build

# Stage 2 – runtime image
FROM node:18-slim
WORKDIR /usr/src/app

# Copy only the built artefacts and necessary files
COPY --from=builder /usr/src/app/package.json /usr/src/app/
COPY --from=builder /usr/src/app/dist /usr/src/app/dist

# Install production dependencies only
RUN npm install --omit=dev && npm cache clean --force

# Expose the API port
EXPOSE 8000

# Healthcheck for Docker
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8000/healthz || exit 1

# Run the API
CMD [ "node", "dist/index.js" ]
