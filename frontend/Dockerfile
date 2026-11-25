# syntax=docker/dockerfile:1

FROM node:22-alpine AS deps
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@10.33.2 --activate
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:22-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_VERITAS_MODE=demo
ARG NEXT_PUBLIC_VERITAS_TEST_MODE=0
ARG HARNESS_URL=http://harness:8002
ENV NEXT_PUBLIC_VERITAS_MODE=${NEXT_PUBLIC_VERITAS_MODE}
ENV NEXT_PUBLIC_VERITAS_TEST_MODE=${NEXT_PUBLIC_VERITAS_TEST_MODE}
ENV HARNESS_URL=${HARNESS_URL}
ENV NEXT_PUBLIC_HARNESS_URL=${HARNESS_URL}
RUN corepack enable && corepack prepare pnpm@10.33.2 --activate
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Rewrites are serialized into standalone server.js at build time.
RUN pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    HARNESS_URL=http://harness:8002
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
