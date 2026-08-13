# CIP Frontend - Setup & Integration Guide

This guide covers 4 integration options for different project architectures.

---

## Option 1: Standalone Vite Project

**Use this if:** You want a completely separate frontend application deployed independently.

### Setup Steps

```bash
# 1. Extract the archive
unzip cip-frontend.zip
cd cip-frontend

# 2. Install dependencies
npm install

# 3. Configure environment
cp .env.example .env.local

# Edit .env.local
VITE_API_BASE_URL=http://localhost:8000
VITE_POLLING_INTERVAL=2000
VITE_MAX_RETRIES=5
```

### Development

```bash
# Terminal 1: Start or deploy the backend stack
# This repo's backend is the Lambda/API Gateway stack provisioned by CDK.
# Set VITE_API_BASE_URL to the API Gateway URL from the CDK output.

# Terminal 2: Start frontend
cd ../cip-frontend
npm run dev
```

### Production Deployment

**Vercel (Recommended):**
```bash
# Push to GitHub
git push origin main

# Vercel auto-deploys from Git
# Configure env vars in Vercel dashboard:
# VITE_API_BASE_URL = https://api.your-domain.com
```

**Netlify:**
```bash
npm install -g netlify-cli
netlify deploy --prod --dir dist
```

**AWS S3 + CloudFront:**
```bash
npm run build
aws s3 cp dist s3://your-bucket --recursive
aws cloudfront create-invalidation --distribution-id XXX --paths "/*"
```

**Docker:**
```dockerfile
# Dockerfile
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Nginx Config:**
```nginx
server {
    listen 80;
    server_name app.your-domain.com;
    
    root /var/www/html;
    index index.html;
    
    location / {
        try_files $uri /index.html;
    }
    
    location ~* \.(js|css|png|jpg|gif|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## Option 2: Monorepo Integration (Recommended)

**Use this if:** You have a Nx/Turborepo monorepo with backend and want unified development.

### Project Structure

```
your-monorepo/
├── apps/
│   ├── backend/                 # Your Python/Node backend
│   │   ├── src/
│   │   ├── requirements.txt / package.json
│   │   └── ...
│   │
│   └── cip-frontend/            # ← Copy cip-frontend here
│       ├── src/
│       ├── package.json
│       └── ...
│
├── packages/
│   └── cip-types/               # Shared types (optional)
│       ├── api.ts
│       ├── index.ts
│       └── package.json
│
├── package.json                 # Root workspace config
└── nx.json / turbo.json        # Workspace config
```

### Step 1: Copy to Monorepo

```bash
cp -r cip-frontend/ your-monorepo/apps/
```

### Step 2: Update package.json

**Root package.json:**
```json
{
  "private": true,
  "workspaces": [
    "apps/*",
    "packages/*"
  ],
  "scripts": {
    "dev": "concurrently \"npm run dev -w apps/backend\" \"npm run dev -w apps/cip-frontend\"",
    "build": "npm run build -w apps/backend && npm run build -w apps/cip-frontend",
    "test": "npm run test -w apps/cip-frontend"
  },
  "devDependencies": {
    "concurrently": "^8.2.0"
  }
}
```

**apps/cip-frontend/package.json:**
```json
{
  "name": "@workspace/cip-frontend",
  "private": true,
  // ... rest of config
}
```

### Step 3: Share Types (Optional but Recommended)

Create `packages/cip-types/`:

```bash
mkdir -p packages/cip-types/src
```

**packages/cip-types/package.json:**
```json
{
  "name": "@workspace/cip-types",
  "version": "1.0.0",
  "private": true,
  "exports": {
    ".": "./src/index.ts"
  }
}
```

**packages/cip-types/src/index.ts:**
```typescript
export interface StatusResponse {
  run_id: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress?: number;
  error_message?: string;
  executive_summary?: string;
  agent_results?: AgentResults;
  created_at: string;
  completed_at?: string;
}

export interface AgentResult {
  title: string;
  confidence_score: number;
  detailed_insight: string;
  system_evidence: string[];
  metadata?: {
    sources?: string[];
    data_points?: number;
    last_updated?: string;
  };
}

export interface AgentResults {
  [key: string]: AgentResult;
}
```

### Step 4: Update Frontend to Use Shared Types

**apps/cip-frontend/package.json:**
```json
{
  "dependencies": {
    "@workspace/cip-types": "workspace:*"
  }
}
```

**apps/cip-frontend/src/types/index.ts:**
```typescript
export type {
  StatusResponse,
  AgentResult,
  AgentResults,
} from '@workspace/cip-types';

// Add frontend-only types here
export interface UseRunStatusOptions {
  runId: string;
  enabled?: boolean;
  polling_interval?: number;
  max_retries?: number;
}
```

### Step 5: Run Development Server

```bash
# From root directory
npm run dev

# Starts both backend and frontend in one command
# Backend on http://localhost:8000
# Frontend on http://localhost:5173
```

### Step 6: Deploy from Monorepo

```bash
# Build both apps
npm run build

# Deploy apps independently
# apps/backend -> container registry or server
# apps/cip-frontend/dist -> CDN or static hosting
```

---

## Option 3: Next.js Integration

**Use this if:** You're using Next.js and want the frontend integrated into your existing app.

### Prerequisites

Existing Next.js 13+ app with App Router

### Step 1: Copy Source Files

```bash
# Copy components, hooks, types, utils
cp -r cip-frontend/src/components your-nextjs-app/app/
cp -r cip-frontend/src/hooks your-nextjs-app/app/
cp -r cip-frontend/src/types your-nextjs-app/app/
cp -r cip-frontend/src/utils your-nextjs-app/app/
cp cip-frontend/src/styles/globals.css your-nextjs-app/app/
```

### Step 2: Install Dependencies

```bash
npm install @tanstack/react-query @radix-ui/react-collapsible lucide-react
```

### Step 3: Setup TanStack Query Provider

**app/providers.tsx:**
```typescript
'use client';

import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000,
      gcTime: 5 * 60 * 1000,
    },
  },
});

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

**app/layout.tsx:**
```typescript
import { Providers } from './providers';
import './globals.css';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

### Step 4: Create Report Page

**app/report/page.tsx:**
```typescript
'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { Dashboard } from '@/components/Dashboard';

function ReportContent() {
  const searchParams = useSearchParams();
  const runId = searchParams.get('runId') || '';
  const company = searchParams.get('company') || 'Company';

  if (!runId) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-lg text-slate-600">No run ID provided</p>
      </div>
    );
  }

  return <Dashboard runId={runId} companyName={company} />;
}

export default function ReportPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading...</div>}>
      <ReportContent />
    </Suspense>
  );
}
```

### Step 5: Configure API Routes (Optional)

If you want to proxy API calls through Next.js:

**app/api/proxy/status/[runId]/route.ts:**
```typescript
export async function GET(
  request: Request,
  { params }: { params: { runId: string } }
) {
  try {
    const response = await fetch(
      `${process.env.BACKEND_API_URL}/status/${params.runId}`,
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    const data = await response.json();
    return Response.json(data, { status: response.status });
  } catch (error) {
    return Response.json(
      { error: 'Failed to fetch status' },
      { status: 500 }
    );
  }
}
```

**app/utils/api.ts:**
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/proxy';

export async function getRunStatus(runId: string) {
  const response = await fetch(`${API_BASE_URL}/status/${runId}`);
  if (!response.ok) throw new Error('Failed to fetch status');
  return response.json();
}
```

### Step 6: Environment Setup

**.env.local:**
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
BACKEND_API_URL=http://localhost:8000
```

### Step 7: Run Development

```bash
npm run dev
# Frontend: http://localhost:3000/report?runId=test-run-123
```

---

## Option 4: Add to Existing React App

**Use this if:** You have an existing React/Vite app and want to add the intelligence dashboard.

### Step 1: Copy Source Files

```bash
cp -r cip-frontend/src/components src/
cp -r cip-frontend/src/hooks src/
cp -r cip-frontend/src/types src/
cp -r cip-frontend/src/utils src/
cp cip-frontend/src/styles/globals.css src/styles/
```

### Step 2: Install Dependencies

```bash
npm install @tanstack/react-query @radix-ui/react-collapsible lucide-react
```

### Step 3: Setup QueryProvider

**src/main.tsx:**
```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'
import './styles/globals.css'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
```

### Step 4: Add Route

**src/pages/ReportPage.tsx:**
```typescript
import { Dashboard } from '@/components/Dashboard'

export function ReportPage() {
  const runId = new URLSearchParams(location.search).get('runId') || ''
  const company = new URLSearchParams(location.search).get('company') || 'Company'
  
  return <Dashboard runId={runId} companyName={company} />
}
```

**src/App.tsx:**
```typescript
import { ReportPage } from './pages/ReportPage'

function App() {
  return <ReportPage />
}

export default App
```

### Step 5: Configure Environment

**.env.local:**
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_POLLING_INTERVAL=2000
```

### Step 6: Run

```bash
npm run dev
# Open http://localhost:5173?runId=test-run-123
```

---

## Environment Variables

### Development (All Options)

**.env.local:**
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_POLLING_INTERVAL=2000
VITE_MAX_RETRIES=5
VITE_ENABLE_DEMO_MODE=false
```

### Staging

**.env.staging:**
```env
VITE_API_BASE_URL=https://staging-api.your-domain.com
VITE_POLLING_INTERVAL=3000
VITE_MAX_RETRIES=3
```

### Production

**.env.production:**
```env
VITE_API_BASE_URL=https://api.your-domain.com
VITE_POLLING_INTERVAL=5000
VITE_MAX_RETRIES=2
```

---

## Docker Compose Setup

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  backend:
    build: ./apps/backend
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
      - DATABASE_URL=postgresql://user:password@db:5432/cip
    depends_on:
      - db
    volumes:
      - ./apps/backend:/app

  frontend:
    build: ./apps/cip-frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_BASE_URL=http://backend:8000
    depends_on:
      - backend
    volumes:
      - ./apps/cip-frontend:/app

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=cip
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

**Run:**
```bash
docker-compose up

# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

---

## CORS Configuration

### Backend Setup

**Python FastAPI:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Development
        "http://localhost:3000",      # Next.js dev
        "https://your-domain.com",    # Production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

**Node Express:**
```javascript
const cors = require('cors');

app.use(cors({
  origin: [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://your-domain.com",
  ],
  credentials: true,
}));
```

**Nginx Reverse Proxy:**
```nginx
location /status {
    add_header Access-Control-Allow-Origin "*";
    add_header Access-Control-Allow-Methods "GET, OPTIONS";
    add_header Access-Control-Allow-Headers "Content-Type";
    
    if ($request_method = 'OPTIONS') {
        return 204;
    }
    
    proxy_pass http://backend:8000;
}
```

---

## Monorepo with Nx

**nx.json:**
```json
{
  "tasksRunnerOptions": {
    "default": {
      "runner": "@nx/workspace/tasks-runners/default",
      "options": {
        "cacheableOperations": ["build", "test"]
      }
    }
  }
}
```

**apps/cip-frontend/project.json:**
```json
{
  "name": "cip-frontend",
  "projectType": "application",
  "sourceRoot": "apps/cip-frontend/src",
  "prefix": "cip",
  "targets": {
    "serve": {
      "executor": "@nx/vite:dev-server",
      "configurations": {
        "development": {
          "browserTarget": "cip-frontend:build:development"
        }
      }
    },
    "build": {
      "executor": "@nx/vite:build"
    },
    "test": {
      "executor": "@nx/vite:test"
    }
  }
}
```

**Run:**
```bash
nx serve cip-frontend
nx build cip-frontend
nx test cip-frontend
```

---

## Troubleshooting Integration Issues

### Issue: Module Not Found

```
Cannot find module '@/components/Dashboard'
```

**Solution:** Update path aliases in build config
- Vite: `vite.config.ts`
- Next.js: `jsconfig.json` or `tsconfig.json`
- Webpack: `webpack.config.js`

### Issue: QueryClient Errors

```
No QueryClientProvider found
```

**Solution:** Wrap app with `<QueryClientProvider>`
- Check `main.tsx` or `layout.tsx` has provider
- Verify provider wraps child components
- Check `QueryClient` instance is created

### Issue: Tailwind CSS Not Working

```
Tailwind classes not applying
```

**Solutions:**
1. Verify Tailwind installed: `npm list tailwindcss`
2. Check `tailwind.config.ts` includes correct paths
3. Verify `globals.css` is imported in entry point
4. Clear cache: `rm -rf .next node_modules/.next`
5. Rebuild: `npm run dev`

### Issue: CORS Errors in Production

```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution:**
1. Verify backend CORS middleware is configured
2. Check allowed origins include your domain
3. Test with `curl -H "Origin: https://your-domain.com"`
4. Check Nginx/proxy configuration

---

## Quick Reference

| Option | Best For | Complexity | Deployment |
|--------|----------|-----------|-----------|
| **Standalone** | Microservices | Low | Independent |
| **Monorepo** | Full-stack teams | Medium | Coordinated |
| **Next.js** | Full-stack apps | Medium | Unified |
| **Existing React** | Adding features | Low | Existing pipeline |

---

## Additional Resources

- [Vite Docs](https://vitejs.dev)
- [Next.js Docs](https://nextjs.org/docs)
- [Nx Docs](https://nx.dev)
- [Docker Compose](https://docs.docker.com/compose)
- [TanStack Query](https://tanstack.com/query)
