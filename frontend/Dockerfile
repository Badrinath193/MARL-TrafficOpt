FROM node:22-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

EXPOSE 5173
CMD ["sh", "-c", "printf 'window.__MARL_TRAFFICOPT_CONFIG__ = { BACKEND_URL: \"%s\" };\\n' \"${VITE_BACKEND_URL:-}\" > /app/dist/env.js && npx vite preview --host 0.0.0.0 --port ${PORT:-5173}"]
