
import logging
import sentry_sdk

from telegram import Update
from fastapi.responses import HTMLResponse
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


@app.get("/oauth/callback", response_class=HTMLResponse)
async def oauth_callback(
    request: Request,
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter (our token)"),
    error: str = Query(None, description="OAuth error parameter")
):
    """Handle OAuth callback from provider"""
    try:
        # Check for OAuth error
        if error:
            logger.error(f"OAuth error: {error}")
            return HTMLResponse(
                content="""
                <html>
                    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                        <h2>❌ Authorization Failed</h2>
                        <p>There was an error during authorization: {}</p>
                        <p>You can close this window and try again.</p>
                    </body>
                </html>
                """.format(error),
                status_code=400
            )
        
        # Validate the state (our OAuth token)
        token_data = auth_service.get_oauth_token_data(state)
        if not token_data:
            logger.warning(f"Invalid or expired OAuth token: {state[:8]}...")
            return HTMLResponse(
                content="""
                <html>
                    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                        <h2>❌ Invalid or Expired Link</h2>
                        <p>The authorization link has expired or is invalid.</p>
                        <p>Please request a new authorization link from the bot.</p>
                    </body>
                </html>
                """,
                status_code=400
            )
        
        # Mark token as used
        auth_service.mark_oauth_token_used(state)
        
        user_id = token_data['user_id']
        logger.info(f"OAuth callback successful for user {user_id}")
        
        # Here you would normally:
        # 1. Exchange the 'code' for an access token from the OAuth provider
        # 2. Store the access token linked to the Telegram user_id
        # 3. Optionally send a confirmation message via the bot
        
        # For now, we'll just show success
        tg_app = request.app.state.tg_app
        try:
            await tg_app.bot.send_message(
                chat_id=user_id,
                text="✅ <b>Authorization Successful!</b>\n\n"
                     "Your account has been successfully linked via OAuth.\n"
                     "You can now close this browser window.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Could not send confirmation message to user {user_id}: {e}")
        
        return HTMLResponse(
            content="""
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2>✅ Authorization Successful!</h2>
                    <p>Your account has been successfully linked.</p>
                    <p>You can now close this window and return to Telegram.</p>
                    <script>
                        setTimeout(function() {
                            window.close();
                        }, 3000);
                    </script>
                </body>
            </html>
            """
        )
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return HTMLResponse(
            content="""
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2>❌ Server Error</h2>
                    <p>An unexpected error occurred during authorization.</p>
                    <p>Please try again later.</p>
                </body>
            </html>
            """,
            status_code=500
        )