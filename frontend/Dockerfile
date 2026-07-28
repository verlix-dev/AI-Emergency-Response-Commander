FROM node:20-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
