import httpx
import logging
import sentry_sdk

from telegram import Update
from fastapi.staticfiles import StaticFiles
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
async def oauth_callback_debug(code: str, state: str, error: str):
    print(f"code: {code}")
    print(f"state: {state}")
    if error:
        print(f"error: {error}")
        return {"status": "error", "error": error}

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": f"{settings.WEBHOOK_URL}/auth/callback",
        "client_id": settings.OAUTH_CLIENT_ID,
        "client_secret": settings.OAUTH_CLIENT_SECRET,
    }

    token_url = f"{settings.BERLINHOUSE_BASE_URL}/o/token/"

    # token_data = {
    #     "grant_type": "refresh_token",
    #     "code": code,
    #     "refresh_token": YOUR_REFRESH_TOKEN,
    #     "redirect_uri": f"{settings.WEBHOOK_URL}/auth/callback",
    #     "client_id": settings.OAUTH_CLIENT_ID,
    #     "client_secret": settings.OAUTH_CLIENT_SECRET,
    # }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            print(f"Token exchange response status: {response.status_code}")
            print(f"Token exchange response: {response.text}")

            if response.status_code == 200:
                token_response = response.json()
                print(f"Access token received: {token_response}")

                access_token = token_response.get("accessToken")
                if access_token:
                    print(f"Fetching user info with access token...")

                    user_info = await auth_service.get_user_info(access_token)

                    if user_info:
                        print(f"User info received: {user_info}")

                        user_id = user_info.get("id")

                        if user_id:
                            session_saved = await auth_service.save_user_session(
                                user_id=user_id,
                                telegram_id=state,
                                access_token=access_token,
                            )
                            print(f"Session saved: {session_saved}")
                        else:
                            print("No user ID found in user info")

                        return {
                            "status": "success",
                            "token_response": token_response,
                            "user_info": user_info,
                        }
                    else:
                        print("Failed to get user info")
                        return {
                            "status": "user_info_failed",
                            "token_response": token_response,
                        }
                else:
                    print("No access token found in response")
                    return {
                        "status": "no_access_token",
                        "token_response": token_response,
                    }
            else:
                print(
                    f"Token exchange failed: {response.status_code} - {response.text}"
                )
                return {
                    "status": "token_exchange_failed",
                    "status_code": response.status_code,
                    "response": response.text,
                }

    except Exception as e:
        print(f"Error during token exchange: {e}")
        return {"status": "error", "message": str(e)}
