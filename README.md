# Paladium Primes Bot

## Overview
Bot to manage "primes" (bounties) for the Paladium Minecraft server.
Features:
- /prime-deploy: deploy the rules + button to open the prime modal
- Prime submission via modal, follow-up DM to upload image proof
- Admin validation with Accept/Reject (sends PM to submitter)
- Publication of accepted primes to public channel
- Ticket system for claims
- Leaderboard (updated every 5 minutes) posted as an embed in the classement channel
- Designed for deployment on Render using environment variables

## Env variables (set these in Render / your host)
- DISCORD_TOKEN: Discord bot token
- PALADIUM_API_KEY: Paladium API key

## Quick deploy (Render)
1. Push this repo to GitHub.
2. Create a Render service (Worker) linked to the repo.
3. Add environment variables (DISCORD_TOKEN, PALADIUM_API_KEY).
4. Deploy.

## Notes
- Do NOT commit your tokens or API keys to the repo.
- If the Paladium API JSON differs, adapt `utils/paladium_api.py` accordingly.
