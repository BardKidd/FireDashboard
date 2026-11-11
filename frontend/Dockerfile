FROM node:22-alpine AS build
WORKDIR /app
# Install deps first so this layer is reused until package*.json changes.
# The cache mount keeps npm's download cache between builds, so even a
# lockfile change only fetches the packages that are new.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund --prefer-offline
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
