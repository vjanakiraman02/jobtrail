FROM node:26-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000
# Dev server; bind to all interfaces so the container port is reachable.
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
