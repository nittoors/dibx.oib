FROM node:26.8.2-alpine

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@11.19.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

RUN chown -R node:node /app
USER node

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]
