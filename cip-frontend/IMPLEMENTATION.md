# CIP Frontend - Complete Implementation Guide

## Quick Start (3 Minutes)

```bash
# 1. Extract
unzip cip-frontend.zip
cd cip-frontend

# 2. Install
npm install

# 3. Configure
cp .env.example .env.local
# Edit .env.local: VITE_API_BASE_URL=http://localhost:8000

# 4. Develop
npm run dev
# Open http://localhost:5173?runId=test-run-123

# 5. Build
npm run build
npm run preview
```

---

## NPM Scripts Reference

```bash
npm run dev              # Start development server (port 5173)
npm run build           # Build optimized production bundle
npm run preview         # Preview production build locally
npm run type-check      # Verify TypeScript types (no runtime)
npm run lint            # Run ESLint for code quality
npm run format          # Format code with Prettier
npm run test            # Run unit tests
npm run test:ui         # Interactive test UI with visual runner
```

---

## Architecture Overview

### Data Flow

```
Backend API (/status/{runId})
         ↓
useRunStatus Hook (TanStack Query)
    - Polling
    - Caching
    - Retry logic
         ↓
Dashboard Component
    - useIsResultReady()
    - useAgentCardsData()
         ↓
    ├── HeroSection (Executive summary)
    ├── StatusIndicator (Progress)
    └── Grid of AgentCards
           ↓
        Each AgentCard
        - Title + Confidence (always visible)
        - Expandable details (collapsed by default)
```

### State Management

**Server State (TanStack Query):**
- Backend data (status, results)
- Polling lifecycle
- Caching strategy
- Retry logic

**UI State (React useState):**
- Card expand/collapse
- Tab selection
- Modal open/close

---

## Polling Behavior

### How It Works

```
t=0s:  startPolling()
       Poll #1 → PENDING (progress: 20%)
       ↓ refetch after 2000ms

t=2s:  Poll #2 → PROCESSING (progress: 50%)
       ↓ refetch after 2000ms

t=4s:  Poll #3 → PROCESSING (progress: 75%)
       ↓ refetch after 2000ms

t=6s:  Poll #4 → COMPLETED (full results)
       ↓ STOP POLLING (terminal state reached)

t=∞:   Show cached results
```

### Configuration

```typescript
// Default configuration
useRunStatus({
  runId: 'run-123',
  enabled: true,
  polling_interval: 2000,    // milliseconds
  max_retries: 5
})

// Custom configuration
useRunStatus({
  runId: 'run-123',
  polling_interval: 5000,    // Poll every 5 seconds
  max_retries: 3             // Give up after 3 failures
})
```

### Retry Logic

```
Attempt 1: Fail immediately → Retry after 1s
Attempt 2: Fail → Retry after 2s
Attempt 3: Fail → Retry after 4s
Attempt 4: Fail → Retry after 8s
Attempt 5: Fail → Retry after 16s
Attempt 6: Fail → GIVE UP (max_retries reached)
```

---

## Type Safety

### API Contracts

All data structures are TypeScript interfaces in `src/types/index.ts`:

```typescript
StatusResponse {
  run_id: string
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  progress?: number           // 0-100, optional
  error_message?: string      // Only if FAILED
  executive_summary?: string
  agent_results?: AgentResults
  created_at: string          // ISO 8601
  completed_at?: string       // ISO 8601
}

AgentResults = { [key: string]: AgentResult }

AgentResult {
  title: string
  confidence_score: number    // 0-100
  detailed_insight: string
  system_evidence: string[]
  metadata?: {
    sources?: string[]
    data_points?: number
    last_updated?: string
  }
}
```

### Type Checking

```bash
# Check all types without compiling
npm run type-check

# Compile TypeScript (Vite does this during build)
npm run build

# IDE will show type errors in editor
# ESLint will catch type issues
```

---

## Testing Strategy

### Unit Tests

**Components (AgentCard.test.tsx):**
- Rendering with data
- Expand/collapse functionality
- Confidence color coding
- Evidence display
- Metadata rendering

**Hooks (useRunStatus.test.ts):**
- Initial load
- Polling behavior
- Status transitions
- Error handling
- Retry logic
- Caching behavior

**Utilities:**
- API client error handling
- Formatting functions
- Data transformation

### Run Tests

```bash
# Run all tests once
npm run test

# Run tests in watch mode
npm run test -- --watch

# Interactive test UI
npm run test:ui

# Generate coverage report
npm run test -- --coverage
```

### Example Test

```typescript
test('expands to show detailed insight on click', async () => {
  const data = {
    title: 'Financial Analysis',
    confidence_score: 92,
    detailed_insight: 'Strong revenue growth...',
    system_evidence: ['Q4 earnings up 15%'],
  };

  render(<AgentCard id="financial" data={data} />);
  
  // Initially collapsed
  expect(screen.queryByText('Detailed Insight')).not.toBeInTheDocument();
  
  // Click to expand
  await userEvent.click(screen.getByRole('button'));
  
  // Now visible
  expect(screen.getByText('Detailed Insight')).toBeInTheDocument();
  expect(screen.getByText(/Strong revenue growth/)).toBeInTheDocument();
});
```

---

## Backend Integration

### Required Endpoint

```
GET /status/{runId}

Response: StatusResponse (see Type Safety section)
```

### Example Backend Implementation

**Python FastAPI:**
```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/status/{run_id}")
async def get_status(run_id: str):
    # Fetch from database or cache
    run = await db.get_run(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    response = {
        "run_id": run.id,
        "status": run.status,
        "progress": run.progress,
        "created_at": run.created_at.isoformat(),
    }
    
    if run.status == "FAILED":
        response["error_message"] = run.error_message
    
    if run.status == "COMPLETED":
        response.update({
            "executive_summary": run.executive_summary,
            "agent_results": run.agent_results,  # JSON from DB
            "completed_at": run.completed_at.isoformat(),
        })
    
    return JSONResponse(response)
```

**Node Express:**
```javascript
app.get('/status/:runId', async (req, res) => {
  const { runId } = req.params;
  
  try {
    const run = await Run.findById(runId);
    
    if (!run) {
      return res.status(404).json({ error: 'Run not found' });
    }
    
    const response = {
      run_id: run.id,
      status: run.status,
      progress: run.progress,
      created_at: run.created_at,
    };
    
    if (run.status === 'COMPLETED') {
      response.executive_summary = run.executive_summary;
      response.agent_results = run.agent_results;
      response.completed_at = run.completed_at;
    }
    
    if (run.status === 'FAILED') {
      response.error_message = run.error_message;
    }
    
    res.json(response);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

### CORS Configuration

**FastAPI:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Express:**
```javascript
const cors = require('cors');

app.use(cors({
  origin: ["http://localhost:5173", "https://your-domain.com"],
  credentials: true,
}));
```

**Nginx:**
```nginx
location /status {
    add_header Access-Control-Allow-Origin "http://localhost:5173";
    add_header Access-Control-Allow-Methods "GET, OPTIONS";
    add_header Access-Control-Allow-Headers "Content-Type";
    
    if ($request_method = 'OPTIONS') {
        return 204;
    }
    
    proxy_pass http://backend:8000;
}
```

---

## Environment Variables

### Development (.env.local)
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_POLLING_INTERVAL=2000
VITE_MAX_RETRIES=5
VITE_ENABLE_DEMO_MODE=false
```

### Staging (.env.staging)
```env
VITE_API_BASE_URL=https://staging-api.your-domain.com
VITE_POLLING_INTERVAL=3000
VITE_MAX_RETRIES=3
```

### Production (.env.production)
```env
VITE_API_BASE_URL=https://api.your-domain.com
VITE_POLLING_INTERVAL=5000
VITE_MAX_RETRIES=2
```

### Vite Environment Loading

Vite automatically loads:
1. `.env` (always)
2. `.env.local` (never committed)
3. `.env.{mode}` (based on `--mode` flag)
4. `.env.{mode}.local` (mode-specific overrides)

Access in code:
```typescript
const apiUrl = import.meta.env.VITE_API_BASE_URL;
const pollingInterval = parseInt(import.meta.env.VITE_POLLING_INTERVAL);
```

---

## Performance Optimization

### Bundle Size

Current gzipped: ~25-30 KB

**Breakdown:**
- React: ~42 KB
- TanStack Query: ~15 KB
- Tailwind CSS: ~20 KB
- UI Components: ~8 KB

### Optimization Techniques

1. **Code Splitting** - Vite automatically splits by chunk
2. **Tree Shaking** - Unused code removed during build
3. **Minification** - Terser minifies JavaScript
4. **CSS Purging** - Tailwind removes unused styles
5. **Image Optimization** - SVG icons are inlined
6. **Lazy Loading** - Components can be loaded on-demand

### Lighthouse Checklist

```
Performance: >90       # Fast load time
Accessibility: >90    # WCAG compliant
Best Practices: >90   # Security & standards
SEO: >90             # Search engine friendly
```

Run audit:
```bash
npm run build
npm run preview
# Then use Chrome DevTools Lighthouse
```

---

## Deployment

### Build for Production

```bash
npm run build

# Output: dist/ folder
# Contains:
# - index.html (minified)
# - js/main-XXXXX.js (minified, gzipped)
# - css/style-XXXXX.css (minified, gzipped)
```

### Deployment Options

**1. Vercel (Recommended)**
```bash
npm install -g vercel
vercel
# Automatically deploys from Git
```

**2. Netlify**
```bash
npm install -g netlify-cli
netlify deploy --prod --dir dist
```

**3. AWS S3 + CloudFront**
```bash
npm run build
aws s3 cp dist s3://your-bucket --recursive
# Configure CloudFront to invalidate cache
```

**4. Your Own Server (Nginx)**
```bash
npm run build
scp -r dist/* user@server:/var/www/html/
```

**Nginx Config:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /var/www/html;
    index index.html;
    
    location / {
        # Enable SPA routing
        try_files $uri /index.html;
    }
    
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## Troubleshooting

### CORS Errors
```
Error: Access to XMLHttpRequest at 'http://...' from origin 'http://localhost:5173' 
has been blocked by CORS policy
```

**Solution:** Configure CORS on backend
- Allow `http://localhost:5173` for development
- Allow your production domain in production

### Polling Not Stopping
```
Backend keeps receiving requests even after COMPLETED
```

**Solution:** Verify backend returns terminal status
```json
{
  "status": "COMPLETED",  // or "FAILED"
  "agent_results": { ... },
  "executive_summary": "..."
}
```

### Styling Issues
```
Tailwind classes not applying
```

**Solutions:**
1. Verify Tailwind CSS imported: check `src/main.tsx`
2. Check `tailwind.config.ts` content paths
3. Clear build cache: `rm -rf dist node_modules/.vite`
4. Rebuild: `npm run dev`

### TypeScript Errors
```
Type 'X' is not assignable to type 'Y'
```

**Solution:** Run type check
```bash
npm run type-check

# Fix errors in src/types/index.ts or update usage
```

### Module Not Found
```
Cannot find module '@/components/Dashboard'
```

**Solution:** Check path aliases in `vite.config.ts`
- `@` → `src/`
- `@components` → `src/components/`

---

## Deployment Checklist

Before deploying to production:

**Code Quality**
- [ ] `npm run type-check` passes
- [ ] `npm run lint` has no errors
- [ ] `npm run test` passes
- [ ] No console warnings or errors

**Build**
- [ ] `npm run build` completes successfully
- [ ] `npm run preview` works locally
- [ ] No TypeScript errors during build
- [ ] No console errors in preview

**Backend**
- [ ] `/status/{runId}` endpoint implemented
- [ ] CORS configured for production domain
- [ ] Error responses return proper status codes
- [ ] API returns correct data format

**Configuration**
- [ ] `.env.production` configured with prod API URL
- [ ] API base URL points to production backend
- [ ] Polling interval tuned for your use case
- [ ] Error messages reviewed for clarity

**Testing**
- [ ] Tested with real backend API
- [ ] Error handling verified (404, 500, timeout)
- [ ] Mobile responsiveness tested
- [ ] Accessibility audit completed
- [ ] Lighthouse score > 90

**Security**
- [ ] HTTPS enabled in production
- [ ] CSP headers configured
- [ ] Rate limiting configured (if needed)
- [ ] Secrets not committed to repository

**Monitoring**
- [ ] Error tracking setup (if using)
- [ ] Analytics configured (if needed)
- [ ] Logging enabled for debugging
- [ ] Performance monitoring setup

---

## Maintenance

### Dependencies Update

Check for updates:
```bash
npm outdated
```

Update dependencies:
```bash
npm update
npm install
```

### Security

```bash
# Check for vulnerabilities
npm audit

# Fix vulnerabilities
npm audit fix

# Install latest patches only
npm update --depth=0
```

### Performance Monitoring

Lighthouse score over time:
```bash
npm run build
npm run preview
# Run Lighthouse in DevTools
```

Monitor metrics:
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Cumulative Layout Shift (CLS)
- Time to Interactive (TTI)

---

## Advanced Topics

### Adding Authentication

In `src/utils/api.ts`:
```typescript
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('auth_token');
  
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });
}
```

### Adding Real-time Updates

Replace polling with WebSocket in `src/hooks/useRunStatus.ts`:
```typescript
export function useRunStatus(options: UseRunStatusOptions) {
  const [data, setData] = useState<StatusResponse>();
  
  useEffect(() => {
    const ws = new WebSocket(`ws://api/status/${options.runId}`);
    
    ws.onmessage = (event) => {
      const status = JSON.parse(event.data);
      setData(status);
      
      if (status.status === 'COMPLETED' || status.status === 'FAILED') {
        ws.close();
      }
    };
    
    return () => ws.close();
  }, [options.runId]);
  
  return { data, ... };
}
```

### Adding Dark Mode

In `tailwind.config.ts`:
```typescript
export default {
  darkMode: 'class',  // or 'media'
  // ...
}
```

Use in components:
```tsx
<div className="bg-white dark:bg-slate-900">
  <h1 className="text-slate-900 dark:text-white">Title</h1>
</div>
```

---

## Support & Resources

### Internal Documentation
- **README.md** - Quick start guide
- **ARCHITECTURE.md** - Design decisions
- **PROJECT_STRUCTURE.md** - Folder walkthrough

### External Resources
- [React Docs](https://react.dev)
- [TypeScript Docs](https://www.typescriptlang.org/docs/)
- [TanStack Query Docs](https://tanstack.com/query/latest)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Vite Docs](https://vitejs.dev)

### Getting Help
1. Check inline comments in source files
2. Read corresponding documentation file
3. Check troubleshooting section above
4. Run `npm run type-check` for type errors
5. Check browser DevTools console for runtime errors
