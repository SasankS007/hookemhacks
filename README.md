# PicklePro — Pickleball Skill Development Platform

AI-powered pickleball training with stroke analysis, interactive AI rally, and match footage review.

## Tech Stack

- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Framer Motion
- **Backend:** FastAPI (Python)
- **Database/Storage:** Supabase (PostgreSQL + file storage)
- **State Management:** Zustand

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+
- npm

### 1. Clone & Install Frontend

```bash
npm install
```

### 2. Environment Variables

Copy the example env file and fill in your Supabase credentials:

```bash
cp .env.example .env.local
```

Edit `.env.local` with your values:

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
BACKEND_URL=http://localhost:8000
```

### 3. Run the Frontend

```bash
npm run dev
```

The app runs at [http://localhost:3000](http://localhost:3000).

### 4. Set Up & Run the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at [http://localhost:8000](http://localhost:8000). API docs available at [http://localhost:8000/docs](http://localhost:8000/docs).

The Next.js app proxies `/api/*` requests to the FastAPI backend automatically.

## Project Structure

```
/
├── app/                          # Next.js App Router pages
│   ├── layout.tsx                # Root layout with navbar
│   ├── page.tsx                  # Landing page
│   ├── dashboard/page.tsx        # Main dashboard hub
│   ├── stroke-analysis/page.tsx  # Stroke analysis mode
│   ├── ai-rally/page.tsx         # AI rally game
│   └── footage/page.tsx          # Footage upload & analysis
├── components/
│   ├── ui/                       # shadcn/ui components
│   ├── nav/                      # Navbar
│   └── PageTransition.tsx        # Framer Motion wrapper
├── store/
│   └── useAppStore.ts            # Zustand global state
├── lib/
│   ├── utils.ts                  # Utility functions (cn)
│   └── supabase.ts               # Supabase client
└── backend/                      # FastAPI service
    ├── main.py                   # App entry point
    ├── routers/
    │   ├── stroke.py             # Stroke analysis endpoints
    │   ├── rally.py              # Rally game endpoints
    │   └── footage.py            # Footage analysis endpoints
    └── requirements.txt
```

## Features

| Mode | Description |
|------|-------------|
| **Stroke Analysis** | Select stroke type, view camera placeholder, get AI coaching tips |
| **AI Rally** | 2D pickleball court game with keyboard/mouse controls and difficulty levels |
| **Footage Review** | Drag-and-drop video upload, court heatmap, shot statistics, shot timeline |
