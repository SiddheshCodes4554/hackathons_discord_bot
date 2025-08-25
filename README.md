# India Hackathons Discord Bot (Python)

A Discord bot that scrapes **latest hackathons & tech competitions in India** from multiple sources and posts to a Discord channel every few hours.

## Local Setup
1) Copy `.env.example` to `.env` and fill values.
2) Install deps & run:
```bash
pip install -r requirements.txt
python main.py
```

## Deploy (Railway/Render)
Build: `pip install -r requirements.txt`
Start: `python main.py`

## Environment Variables
- `DISCORD_TOKEN` (required)
- `HACKATHON_CHANNEL_ID` (required)
- `SCRAPE_INTERVAL_HOURS` (default `6`)
- `MAX_ITEMS_PER_CYCLE` (default `6`)
- `SOURCES_ENABLED` (csv: `hacker_earth,devpost,techgig`)
