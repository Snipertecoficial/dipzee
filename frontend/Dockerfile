FROM node:24-alpine AS build
WORKDIR /app

COPY package.json yarn.lock* ./
RUN yarn install --frozen-lockfile

COPY . .

# Vite exposes the compatible REACT_APP_* variable at build time, so it
# must be passed as a build ARG, not a runtime env var.
ARG REACT_APP_BACKEND_URL
ARG GIT_SHA=dev
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
ENV GIT_SHA=$GIT_SHA
RUN yarn build
RUN node -e "require('fs').writeFileSync('/app/build/version.json', JSON.stringify({commit: process.env.GIT_SHA}) + '\\n')"

FROM nginx:alpine
ARG GIT_SHA=dev
LABEL org.opencontainers.image.revision=$GIT_SHA
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=10s \
  CMD wget -q -O /dev/null http://127.0.0.1/version.json || exit 1
