# CIP Frontend - Windows Standalone Setup & Local Development

This guide is for running the frontend as a **separate, independent project on Windows** with local development support.

---

## 📋 Prerequisites

### Required
- **Node.js 18+** → Download from [nodejs.org](https://nodejs.org)
- **Git for Windows** (optional) → [git-scm.com](https://git-scm.com)
- **Text Editor** → VS Code recommended ([code.visualstudio.com](https://code.visualstudio.com))

### Verify Installation

Open PowerShell or Command Prompt and run:

```powershell
node --version      # Should show v18.x.x or higher
npm --version       # Should show 9.x.x or higher
```

---

## 🚀 Step 1: Setup on Windows

### Extract Archive

1. Download `cip-frontend.zip`
2. Right-click → **Extract All...**
3. Choose folder (e.g., `C:\Projects\cip-frontend`)
4. Click **Extract**

OR use PowerShell:

```powershell
Expand-Archive -Path cip-frontend.zip -DestinationPath C:\Projects\
cd C:\Projects\cip-frontend
```

### Install Dependencies

```powershell
npm install
```

This creates `node_modules/` folder (~400 MB)

---

## 💻 Step 2: Local Development (No Backend Required)

### Option A: Use Demo/Mock Data (Recommended for Testing)

Create `src/utils/mockData.ts`:

```typescript
// Mock data for local testing without backend
export const mockStatusResponse = {
  run_id: 'run-demo-001',
  status: 'COMPLETED' as const,
  progress: 100,
  executive_summary: `
    Strong financial performance driven by enterprise customer growth.
    Revenue increased 15% YoY with improved margins. Leadership team
    expansion supports international expansion plans.
  `,
  agent_results: {
    financial: {
      title: 'Financial Analysis',
      confidence_score: 92,
      detailed_insight: 'Q4 2023 earnings exceeded expectations with $250M in revenue. Enterprise segment grew 18% YoY.',
      system_evidence: [
        'Q4 2023 earnings: $250M (↑15% YoY)',
        'Gross margin: 68% (↑2% YoY)',
        'Enterprise ARR: $180M (↑18% YoY)',
        'Customer retention: 98%',
      ],
      metadata: {
        sources: ['SEC EDGAR', 'Earnings Call Transcript'],
        data_points: 15,
        last_updated: new Date().toISOString(),
      },
    },
    litigation: {
      title: 'Litigation & Legal',
      confidence_score: 88,
      detailed_insight: 'No material pending litigation. 3 minor regulatory inquiries, all routine. IP portfolio strong with 150+ patents.',
      system_evidence: [
        'No material lawsuits pending',
        '3 routine regulatory inquiries (FDA)',
        '150+ patents filed',
        'No recalled products',
      ],
      metadata: {
        sources: ['SEC Filings', 'Legal Database'],
        data_points: 8,
        last_updated: new Date().toISOString(),
      },
    },
    leadership: {
      title: 'Leadership & Management',
      confidence_score: 85,
      detailed_insight: 'CEO in role for 8 years with strong track record. CFO hired 2 years ago from Fortune 500. Board has 60% independent directors.',
      system_evidence: [
        'CEO: John Smith (8 years tenure)',
        'CFO: Jane Doe (ex-Fortune 500)',
        'Board: 6 independent, 4 executive directors',
        'Executive comp: Within industry benchmarks',
      ],
      metadata: {
        sources: ['SEC Proxy', 'Company Website'],
        data_points: 12,
        last_updated: new Date().toISOString(),
      },
    },
    product: {
      title: 'Product & Technology',
      confidence_score: 90,
      detailed_insight: 'Market-leading product with 40% feature lead over competitors. R&D investment at 18% of revenue. Strong security posture.',
      system_evidence: [
        'Product NPS: 72 (industry avg: 55)',
        'R&D: 18% of revenue',
        'SOC 2 Type II certified',
        '99.99% uptime SLA',
      ],
      metadata: {
        sources: ['Product Analysis', 'Security Audit'],
        data_points: 10,
        last_updated: new Date().toISOString(),
      },
    },
  },
  created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 min ago
  completed_at: new Date().toISOString(),
};
```

Update `src/utils/api.ts`:

```typescript
// Add this at the top of the file, after imports
const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true';

// Replace the fetchRunStatus function
async function fetchRunStatus(runId: string): Promise<StatusResponse> {
  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 500));

  if (USE_MOCK_DATA) {
    // Import mock data at top: import { mockStatusResponse } from './mockData';
    return mockStatusResponse;
  }

  const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const response = await fetch(`${apiUrl}/status/${runId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(
      `Failed to fetch run status: ${response.status} ${response.statusText}`
    );
  }

  const data = (await response.json()) as StatusResponse;
  return data;
}
```

Create `.env.local`:

```env
# Use mock data for local development
VITE_USE_MOCK_DATA=true

# Comment out when using real backend
# VITE_API_BASE_URL=http://localhost:8000
```

Now start the dev server:

```powershell
npm run dev
```

Open browser: `http://localhost:5173?runId=run-demo-001`

✅ **You now have a working UI without needing the backend!**

---

### Option B: Run with Mock Backend (Lite)

Create a simple mock server in `mock-server.js`:

```javascript
const http = require('http');
const fs = require('fs');

const mockData = {
  run_id: 'run-demo-001',
  status: 'COMPLETED',
  progress: 100,
  executive_summary: 'Strong financial performance...',
  agent_results: {
    financial: {
      title: 'Financial Analysis',
      confidence_score: 92,
      detailed_insight: 'Q4 2023 earnings exceeded expectations...',
      system_evidence: ['Q4 2023 earnings: $250M', 'Gross margin: 68%'],
    },
    litigation: {
      title: 'Litigation & Legal',
      confidence_score: 88,
      detailed_insight: 'No material pending litigation...',
      system_evidence: ['No material lawsuits', '3 routine regulatory inquiries'],
    },
    leadership: {
      title: 'Leadership & Management',
      confidence_score: 85,
      detailed_insight: 'CEO in role for 8 years...',
      system_evidence: ['CEO: John Smith (8 years)', 'Board: independent directors'],
    },
    product: {
      title: 'Product & Technology',
      confidence_score: 90,
      detailed_insight: 'Market-leading product...',
      system_evidence: ['Product NPS: 72', 'R&D: 18% of revenue'],
    },
  },
  created_at: new Date().toISOString(),
  completed_at: new Date().toISOString(),
};

const server = http.createServer((req, res) => {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Content-Type', 'application/json');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  if (req.url.match(/^\/status\//)) {
    res.writeHead(200);
    res.end(JSON.stringify(mockData));
  } else {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});

server.listen(3001, () => {
  console.log('Mock server running on http://localhost:3001');
});
```

Run in **separate PowerShell window**:

```powershell
node mock-server.js
```

Update `.env.local`:

```env
VITE_API_BASE_URL=http://localhost:3001
```

---

## 🔌 Step 3: Connect to Real Backend

### When Backend is Ready

Update `.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000
# Or production: VITE_API_BASE_URL=https://api.your-domain.com
```

Restart dev server:

```powershell
# Stop current server (Ctrl + C)
# Then restart
npm run dev
```

### Backend Requirements

Your backend must provide:

```
GET /status/{runId}

Response:
{
  "run_id": "run-123",
  "status": "COMPLETED",  // PENDING | PROCESSING | COMPLETED | FAILED
  "progress": 100,
  "executive_summary": "...",
  "agent_results": {
    "financial": {
      "title": "...",
      "confidence_score": 92,
      "detailed_insight": "...",
      "system_evidence": ["...", "..."]
    },
    "litigation": { ... },
    "leadership": { ... },
    "product": { ... }
  },
  "created_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T10:05:00Z"
}
```

### CORS Configuration

Backend must allow requests from frontend:

**Python FastAPI:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Node Express:**
```javascript
const cors = require('cors');

app.use(cors({
  origin: ["http://localhost:5173", "http://localhost:3000"],
  credentials: true,
}));
```

---

## 📁 Windows File Structure

```
C:\Projects\cip-frontend\
├── src/
│   ├── components/
│   ├── hooks/
│   ├── types/
│   ├── utils/
│   │   ├── api.ts              (← Configure here)
│   │   └── mockData.ts         (← Create for local dev)
│   ├── styles/
│   ├── App.tsx
│   └── main.tsx
│
├── .env.local                  (← Create here)
├── .env.example
├── package.json
├── vite.config.ts
├── tsconfig.json
└── mock-server.js              (← Optional)
```

---

## 🛠️ Windows Commands

### Open Project

```powershell
# Navigate to project
cd C:\Projects\cip-frontend

# Open in VS Code
code .
```

### Development

```powershell
# Start dev server
npm run dev

# Open in browser
# http://localhost:5173?runId=run-demo-001
```

### Testing

```powershell
# Run tests
npm run test

# Run tests with UI
npm run test:ui

# Type check
npm run type-check

# Format code
npm run format
```

### Building

```powershell
# Create production build
npm run build

# Preview production build
npm run preview
```

### Troubleshooting

```powershell
# Clear cache and reinstall
rmdir -Recurse -Force node_modules
rmdir -Force package-lock.json
npm install

# Check TypeScript errors
npm run type-check

# Clear browser cache
# Ctrl + Shift + Delete in browser
```

---

## 🎯 Development Workflow on Windows

### Development Without Backend

```powershell
# Terminal 1: Start frontend
cd C:\Projects\cip-frontend
npm run dev

# Browser: http://localhost:5173?runId=run-demo-001
# Uses mock data from mockData.ts
```

### Development With Backend

```powershell
# Terminal 1: Start backend (if separate)
cd C:\Projects\your-backend
python main.py  # or node server.js

# Terminal 2: Start frontend
cd C:\Projects\cip-frontend
npm run dev

# Frontend now connects to http://localhost:8000
```

### Development with Mock Server

```powershell
# Terminal 1: Start mock server
cd C:\Projects\cip-frontend
node mock-server.js

# Terminal 2: Start frontend
npm run dev

# Frontend connects to http://localhost:3001
```

---

## 🌐 Environment Variables Explained

Create `.env.local` in project root:

```env
# For local development with mock data
VITE_USE_MOCK_DATA=true

# For local development with mock server
VITE_API_BASE_URL=http://localhost:3001

# For local development with real backend
VITE_API_BASE_URL=http://localhost:8000

# For production
VITE_API_BASE_URL=https://api.your-domain.com

# Polling configuration
VITE_POLLING_INTERVAL=2000
VITE_MAX_RETRIES=5
```

### How to Use Different Configs

**Local development (no backend):**
```env
VITE_USE_MOCK_DATA=true
```

**With mock server:**
```env
VITE_API_BASE_URL=http://localhost:3001
```

**With real backend locally:**
```env
VITE_API_BASE_URL=http://localhost:8000
```

**With production backend:**
```env
VITE_API_BASE_URL=https://api.your-domain.com
```

---

## 🧪 Testing Without Backend

### Test URL Parameters

```
http://localhost:5173?runId=run-demo-001&company=Acme%20Corporation
```

### Mock Different Statuses

Update `mockStatusResponse` in `src/utils/mockData.ts`:

```typescript
// For PENDING state:
status: 'PENDING' as const,
progress: 25,
// Remove agent_results

// For PROCESSING state:
status: 'PROCESSING' as const,
progress: 50,
// Remove agent_results

// For FAILED state:
status: 'FAILED' as const,
progress: 0,
error_message: 'Analysis failed due to network error',
// Remove agent_results

// For COMPLETED state:
status: 'COMPLETED' as const,
progress: 100,
// Include agent_results
```

### Test Different Confidence Scores

```typescript
financial: {
  // High confidence
  confidence_score: 92,  // Green badge
},
litigation: {
  // Medium confidence
  confidence_score: 65,  // Yellow badge
},
leadership: {
  // Low confidence
  confidence_score: 45,  // Red badge
},
```

---

## 🚀 Production Deployment on Windows

### Build

```powershell
npm run build
```

Output: `dist/` folder (~500 KB)

### Deploy to Vercel

```powershell
npm install -g vercel
vercel
# Follow prompts, then share link
```

### Deploy to Netlify

```powershell
npm install -g netlify-cli
npm run build
netlify deploy --prod --dir dist
```

### Deploy to Your Server

```powershell
# Build locally
npm run build

# Upload dist/ folder to your server:
# 1. FTP: Upload dist/* to /var/www/html/
# 2. GitHub: Push to repo, enable auto-deploy
# 3. AWS S3: Upload dist/* to bucket
```

---

## ❓ Frequently Asked Questions

### Q: Can I develop without running backend?
**A:** Yes! Use mock data option (Option A above)

### Q: How do I switch between mock and real backend?
**A:** Just change `.env.local` and restart `npm run dev`

### Q: What if I get CORS errors?
**A:** Make sure backend CORS is configured to allow `http://localhost:5173`

### Q: Can I run frontend and backend on same machine?
**A:** Yes! Use 2 PowerShell windows:
- Window 1: Frontend on localhost:5173
- Window 2: Backend on localhost:8000

### Q: How do I test different API responses?
**A:** Edit `mockStatusResponse` in `src/utils/mockData.ts`

### Q: What ports are used?
**A:**
- Frontend: `localhost:5173`
- Backend: `localhost:8000` (your choice)
- Mock server: `localhost:3001` (your choice)

### Q: Do I need to commit .env.local?
**A:** NO! Add to .gitignore (already done)

---

## 📝 Checklist for Windows Setup

- [ ] Node.js 18+ installed
- [ ] Project extracted to `C:\Projects\cip-frontend`
- [ ] Run `npm install`
- [ ] Create `.env.local` with config
- [ ] Run `npm run dev`
- [ ] Open `http://localhost:5173?runId=run-demo-001`
- [ ] See Dashboard with mock data ✅

---

## 🎓 Next Steps

1. **Understand the UI** → Use mock data locally
2. **Learn the code** → Read ARCHITECTURE.md
3. **Write tests** → Check example tests
4. **Connect backend** → Update VITE_API_BASE_URL when ready
5. **Deploy** → Follow production deployment steps

---

## 📞 Windows-Specific Issues

**PowerShell permission error?**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Port already in use?**
```powershell
# Find what's using the port
netstat -ano | findstr :5173

# Kill the process (replace PID)
taskkill /PID 1234 /F
```

**npm install slow?**
```powershell
npm cache clean --force
npm install
```

**Git line ending issues?**
```powershell
git config core.autocrlf true
```

---

**You're all set for Windows development!** 🎉

Start with mock data locally, then connect your backend when it's ready.
