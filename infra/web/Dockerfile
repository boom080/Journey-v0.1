FROM node:22.23.1-bookworm-slim AS builder

WORKDIR /repo
COPY package.json package-lock.json ./
COPY apps/mobile/package.json apps/mobile/package.json
COPY packages/contracts/package.json packages/contracts/package.json
COPY packages/design-tokens/package.json packages/design-tokens/package.json
RUN npm ci

COPY apps/mobile apps/mobile
COPY packages packages
ARG APP_VARIANT=production
ARG EXPO_PUBLIC_API_BASE_URL
ENV APP_VARIANT=${APP_VARIANT} \
    EXPO_PUBLIC_API_BASE_URL=${EXPO_PUBLIC_API_BASE_URL} \
    EXPO_NO_TELEMETRY=1
RUN test -n "${EXPO_PUBLIC_API_BASE_URL}" && \
    if [ "${APP_VARIANT}" = "production" ]; then \
      case "${EXPO_PUBLIC_API_BASE_URL}" in https://*) ;; *) exit 1 ;; esac; \
    fi
RUN npm run mobile:web:build

FROM nginx:1.29.5-alpine
COPY infra/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /repo/apps/mobile/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
