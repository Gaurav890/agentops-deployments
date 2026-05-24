# Task 01 — Project setup

## Goal
Scaffold the repo, install dependencies, wire up environment, get Flask running locally.

## Done when
- [ ] Folder structure matches `docs/architecture.md` exactly
- [ ] Flask app starts with `flask run` and returns 200 on `GET /health`
- [ ] Supabase schema created (run `schema.sql`)
- [ ] `.env.example` created with all required keys (values blank)
- [ ] `requirements.txt` matches approved list in `docs/architecture.md`
- [ ] Next.js app starts with `npm run dev` and renders landing page

## Steps

### 1. Create folder structure
```
fleetpanda-agent/
  backend/
    app.py
    requirements.txt
    webhook/__init__.py
    webhook/avoma.py
    agent/__init__.py
    agent/extractor.py
    agent/prompt_builder.py
    agent/generator.py
    integrations/__init__.py
    integrations/gmail.py
    integrations/calendar.py
    integrations/slack.py
    auth/__init__.py
    auth/google_oauth.py
    db/__init__.py
    db/models.py
    db/schema.sql
  frontend/   (Next.js scaffold via create-next-app)
  .env.example
```

### 2. Backend bootstrap
- `backend/app.py`: Flask app with `/health` route only for now. Load env with `python-dotenv`.
- `backend/db/schema.sql`: Write full schema from `docs/database.md`
- All other files: create empty with a `# TODO` comment and the purpose from `docs/architecture.md`

### 3. Supabase setup
- Create project at supabase.com
- Run `schema.sql` in the SQL editor
- Copy `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to `.env`

### 4. Frontend scaffold
```bash
cd frontend
npx create-next-app@14 . --typescript --app --tailwind --no-src-dir
npm install @supabase/supabase-js
```
Landing page (`app/page.tsx`): just a "Sign in with Google" button for now. No OAuth wiring yet — that's Task 02.

### 5. Generate encryption key
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Add output to `.env` as `TOKEN_ENCRYPTION_KEY`.

## Out of scope
- OAuth flow (Task 02)
- Any agent logic (Task 03+)
- Any real API calls

## Test
```bash
cd backend && flask run
curl http://localhost:5000/health
# should return {"status": "ok"}
```
