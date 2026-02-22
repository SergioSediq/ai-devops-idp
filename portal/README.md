# Backstage Developer Portal

This directory contains the **AI Ops Assistant** plugin and scaffolder templates for the IDP Developer Portal.

## Contents

- `plugins/ai-ops-assistant/` — Chat UI component that calls the AI Agent `/diagnose` API
- `scaffolder-templates/` — Backstage scaffolder templates (e.g., React SSR)
- `Dockerfile` — Multi-stage build for the full Backstage application

## Portal Dockerfile — Build Prerequisites

The `Dockerfile` expects a **fully scaffolded Backstage app** with:

- `package.json`, `yarn.lock` at the repo root
- `packages/backend/dist/skeleton.tar.gz` — backend skeleton
- `packages/backend/dist/bundle.tar.gz` — backend bundle

These artifacts are produced by:

1. Creating a Backstage app: `npx @backstage/create-app@latest`
2. Adding this repo's plugin (e.g., copy `plugins/ai-ops-assistant` into the app)
3. Running `yarn install` and `yarn build`

### Option: Use as Plugin Source Only

To integrate the AI Ops Assistant into an existing Backstage app:

1. Copy `plugins/ai-ops-assistant` into your app's `plugins/` directory
2. Register the plugin in `packages/app/src/App.tsx`
3. Point the chat component at your AI Agent URL (e.g. `http://ai-agent:80/diagnose`)

The `Dockerfile` in this folder is provided for building a complete Backstage image once the app is scaffolded.
