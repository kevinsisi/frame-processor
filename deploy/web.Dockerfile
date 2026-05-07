FROM node:20-alpine AS build

WORKDIR /app

COPY web/package.json web/package-lock.json* ./
RUN npm install

COPY web/ .

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_SETTINGS_ADMIN_TOKEN=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_SETTINGS_ADMIN_TOKEN=$VITE_SETTINGS_ADMIN_TOKEN
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
