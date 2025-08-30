
import logging

import sentry_sdk
from telegram import Update
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request, BackgroundTasks

from app.core.config import settings
from app.core.lifespan import lifespan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
    ]
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

if settings.SENTRY_DNS and settings.APP_ENV == "prod":
    sentry_sdk.init(
        dsn=settings.SENTRY_DNS,
        send_default_pii=True,
    )

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

async def process_telegram_update(tg_app, update_data):
    try:
        update = Update.de_json(data=update_data, bot=tg_app.bot)
        logger.debug(f"Processing Telegram update {update.update_id}")
        await tg_app.process_update(update)
        logger.info(f"Finished processing Telegram update {update.update_id}")
    except Exception as e:
        logger.error(f"Failed to process Telegram update: {e}")
        raise

@app.get("/health")
def check_health():
    logger.info("Health check requested")
    return {"status": "ok", "message": "TowerBot is running"}

@app.post("/telegram")
async def handle_telegram_update(request: Request, background_tasks: BackgroundTasks):
    try:
        update_data = await request.json()
        update_id = update_data.get('update_id', 'unknown')
        logger.info(f"Telegram update {update_id} received, queueing for background processing")
        
        tg_app = request.app.state.tg_app
        background_tasks.add_task(process_telegram_update, tg_app, update_data)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to handle Telegram update: {e}")
        raise