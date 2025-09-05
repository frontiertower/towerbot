import httpx
import logging
import sentry_sdk

from typing import Optional

from telegram import Update
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Request, BackgroundTasks, Query

from app.core.config import settings
from app.core.lifespan import lifespan
from app.services.auth import auth_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
    ],
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
        update_id = update_data.get("update_id", "unknown")
        logger.info(
            f"Telegram update {update_id} received, queueing for background processing"
        )

        tg_app = request.app.state.tg_app
        background_tasks.add_task(process_telegram_update, tg_app, update_data)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to handle Telegram update: {e}")
        raise


@app.get("/auth/callback")
async def handle_oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
):
    if error:
        logger.error(f"OAuth error for user {state}: {error}")
        return {"status": "error", "error": error}

    telegram_id = int(state)
    access_token = None

    code_verifier = await auth_service.get_pkce_verifier(telegram_id)
    if not code_verifier:
        logger.error(f"Could not find PKCE code_verifier for user {telegram_id}.")
        return {
            "status": "error",
            "message": "Authentication session expired. Please try logging in again.",
        }

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": f"{settings.WEBHOOK_URL}/auth/callback",
        "client_id": settings.OAUTH_CLIENT_ID,
        "client_secret": settings.OAUTH_CLIENT_SECRET,
        "code_verifier": code_verifier,
    }

    token_url = f"{settings.BERLINHOUSE_BASE_URL}/o/token/"

    try:
        async with httpx.AsyncClient(verify=False) as client:
            token_response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get("accessToken")

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Token exchange failed: {e.response.status_code} - {e.response.text}"
        )
        return {
            "status": "error",
            "message": "Token exchange failed.",
            "details": e.response.text,
        }
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during token exchange: {e}", exc_info=True
        )
        return {"status": "error", "message": "An unexpected error occurred."}

    if access_token:
        logger.info(f"Successfully obtained access token for user {telegram_id}")
        await auth_service.clear_pkce_verifier(telegram_id)

        user_info = await auth_service.get_user_info(access_token)
        if user_info and "id" in user_info:
            await auth_service.save_user_session(
                user_id=user_info["id"],
                telegram_id=telegram_id,
                access_token=access_token,
            )
            bot_username = (await request.app.state.tg_app.bot.get_me()).username
            return RedirectResponse(f"https://t.me/{bot_username}?start=auth_success")
        else:
            logger.error(
                f"Failed to get user info for user {telegram_id} after successful token exchange."
            )
            return {"status": "error", "message": "Could not retrieve user profile."}
    else:
        logger.error("Token exchange was successful but no access_token was returned.")
        return {
            "status": "error",
            "message": "Authentication failed: no access token in response.",
        }
