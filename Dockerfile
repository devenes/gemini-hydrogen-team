# Stage 1: Build the Mission Control React + TypeScript UI
FROM node:22-slim AS ui-builder
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY web/ ./
RUN npm run build

# Stage 2: Python 3.13 + FFmpeg + Google ADK Runtime
FROM python:3.13-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
COPY adk_agents/ ./adk_agents/
COPY --from=ui-builder /app/src/hydrogen_team/static ./src/hydrogen_team/static

RUN pip install --no-cache-dir .

ENV HYDROGEN_HOST=0.0.0.0
ENV HYDROGEN_PORT=8042
ENV GOOGLE_GENAI_USE_VERTEXAI=TRUE
ENV GOOGLE_CLOUD_LOCATION=global

EXPOSE 8042

CMD ["hydrogen-team", "web", "--host", "0.0.0.0", "--port", "8042"]
