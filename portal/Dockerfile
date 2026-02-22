# Stage 1 - Create the build-image
FROM node:18-bullseye-slim AS build-image

# Install isolate-vm dependencies, these are needed by some of the backstage packages
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends python3 g++ build-essential && \
    yarn config set python /usr/bin/python3

# Install sqlite3 dependencies. You can skip this if you don't use sqlite3 in the image,
# in which case you should also replace better-sqlite3 with "better-sqlite3-mock" in packages/backend/package.json
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get install -y --no-install-recommends libsqlite3-dev

WORKDIR /app

# Copy repo skeleton first, to avoid unnecessary docker cache invalidation.
# The skeleton contains the package.json of each package in the monorepo,
# and along with yarn.lock and the root package.json, that's enough to run yarn install.
COPY yarn.lock package.json packages/backend/dist/skeleton.tar.gz ./
RUN tar xzf skeleton.tar.gz && rm skeleton.tar.gz

RUN --mount=type=cache,target=/home/node/.cache/yarn,sharing=locked,uid=1000,gid=1000 \
    yarn install --frozen-lockfile --production --network-timeout 300000

# Then copy the rest of the backend bundle, along with any other files we might want.
COPY packages/backend/dist/bundle.tar.gz ./
RUN tar xzf bundle.tar.gz && rm bundle.tar.gz

# Stage 2 - Build the actual image
FROM node:18-bullseye-slim

WORKDIR /app

# Copy the install dependencies from the build stage and context
COPY --from=build-image /app .

# Default to port 7007
EXPOSE 7007

# startup command
CMD ["node", "packages/backend", "--config", "app-config.yaml"]
