FROM node:20-alpine
WORKDIR /app
COPY apps/web/package.json ./apps/web/
COPY apps/web/package-lock.json ./apps/web/
RUN cd apps/web && npm install
COPY apps/web ./apps/web
RUN cd apps/web && npm run build
FROM nginx:alpine
COPY --from=0 /app/apps/web/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off"]
