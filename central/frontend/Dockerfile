# Stage 1: Build the React application
FROM node:20-slim AS builder

WORKDIR /app

# Only copy package.json (ignores the Windows package-lock.json if present)
COPY package.json ./
RUN npm install

# Copy the rest of the code and build
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy the compiled output from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# ADD THIS LINE: Copy the custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]