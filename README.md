# Vita - Health Analysis Platform

This project is structured as a monorepo with a separate frontend and backend for easy deployment.

## Project Structure

- `frontend/`: Next.js application (intended for deployment on Vercel).
- `backend/`: FastAPI Python server (intended for deployment on Render).

## Deployment

### Backend (Render)
1. Create a new Web Service on Render.
2. Connect your repository.
3. Set the **Root Directory** to `backend`.
4. Build Command: `pip install -r requirements.txt`.
5. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
6. Add environment variables:
   - `NVIDIA_API_KEY`: Your NVIDIA API key for lab analysis.
   - `GEMINI_API_KEY`: Your Gemini API key for X-ray analysis.

### Frontend (Vercel)
1. Create a new Project on Vercel.
2. Connect your repository.
3. Set the **Root Directory** to `frontend`.
4. Add environment variables:
   - `BACKEND_URL`: The URL of your deployed backend on Render.
   - `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL.
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase anon key.
   - `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role key.
