# Agent Amigos Deployment (Vercel + GoDaddy)

## 1. Deploy frontend to Vercel

- Create a new Vercel project from this repo.
- Framework: Vite (root directory: frontend).
- Build command: npm run build
- Output directory: dist
- Environment variable (Production): VITE_AGENT_API_URL=https://<YOUR_BACKEND_HOST>

## 2. Configure GoDaddy DNS (agentamigos.com)

- Remove the parked A record for @
- Add A record: @ -> 76.76.21.21 (TTL 1 Hour)
- Update CNAME: www -> cname.vercel-dns.com (TTL 1 Hour)
- Keep \_domainconnect record as-is

## 3. Verify

- Wait for DNS propagation (5–60 minutes)
- Visit <https://agentamigos.com> and <https://www.agentamigos.com>
- Confirm landing page metrics load (requires backend URL above)

## Backend hosting

- The backend is separate from the Vercel frontend.
- Deploy the FastAPI backend to a server and set VITE_AGENT_API_URL to that server.

## Subscriber-only security (production)

- Set `AMIGOS_SUBSCRIBER_GATING=true` in the backend environment.
- Set `AMIGOS_SUBSCRIBER_TOKEN` to a strong random secret.
- Ensure only subscriber-authenticated requests can reach protected endpoints.
- Keep public endpoints limited to marketing and public metrics only.
