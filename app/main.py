import logging

from telegram import Update
from fastapi import FastAPI, Request, BackgroundTasks

from app.core.lifespan import lifespan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="TowerBot", lifespan=lifespan)

async def process_telegram_update(tg_app, update_data):
    update = Update.de_json(data=update_data, bot=tg_app.bot)
    await tg_app.process_update(update)
    logger.info("Finished processing Telegram update in the background.")

@app.get("/health")
def check_health():
    logger.info("Health check requested")
    return {"status": "ok", "message": "TowerBot is running"}

@app.post("/telegram")
async def handle_telegram_update(request: Request, background_tasks: BackgroundTasks):
    logger.info("Telegram update received, queueing for background processing.")
    tg_app = request.app.state.tg_app
    update_data = await request.json()

    background_tasks.add_task(process_telegram_update, tg_app, update_data)
    return {"status": "ok"}