# Stage 1: Build source code bằng Node.js
FROM node:20-alpine AS builder
WORKDIR /app

# Copy package.json và cài đặt dependencies
COPY package*.json ./
RUN npm install

# Copy mã nguồn
COPY . .

# Tắt mock data để kết nối API backend thật
ENV VITE_USE_MOCK=false

# Build production bundle
RUN npm run build

# Stage 2: Serve bằng Nginx gọn nhẹ
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# Cấu hình Nginx để hỗ trợ định tuyến Single Page App (React Router)
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
