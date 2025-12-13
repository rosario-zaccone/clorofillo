#!/usr/bin/env python3
import logging
import os, time
import asyncio, redis
from telegram.constants import ParseMode
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, BotCommand, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from clorofillo.persistence.configuration_repository import ConfigurationRepository
from clorofillo.persistence.plant_pot_repository import PlantPotRepository
from clorofillo.persistence.plant_photo_repository import PlantPhotoRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clorofillo.model.configuration import Configuration
from clorofillo.model.plant_pot import PlantPot
from clorofillo.business.plant_pot_service import PlantPotService
from clorofillo.persistence.orm_models import *
load_dotenv()

engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
conf_repository = ConfigurationRepository(session)
pot_repository = PlantPotRepository(session)
photo_repository = PlantPhotoRepository(session)
pot_service = PlantPotService(pot_repository)
r = redis.Redis(host='localhost', port=6379, db=0)
CALIB_DIR = "data/calibration"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

AUTHORIZED_CHAT_IDS = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    AUTHORIZED_CHAT_IDS.add(chat_id)

    # Nice UI: quick-reply keyboard with the main bot commands
    keyboard = [
        ["/settings", "/setsettings", "/timelapse"],
        ["/calibrate", "/diary", "/info"],
        ["/help", "/start"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Hi! You are authorized. Use the keyboard below or type a command.\n\n"
        "Tip: use /info to see command details and parameter meanings.",
        reply_markup=reply_markup
    )

def authorized_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        chat_id = update.effective_chat.id
        if chat_id not in AUTHORIZED_CHAT_IDS:
            await update.message.reply_text("⚠️ You must use /start first to access commands.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

async def send_telegram_message(bot, chat_id: int, message: str):
    try:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Failed to send message: {e}")

async def notify_manager(application):
    loop = asyncio.get_event_loop()
    while True:
        message = await loop.run_in_executor(None, r.lpop, "rasp_to_bot")
        if message:
            value = int(message)
            if value == 1:
                message_text = "⚠️ Empty tank!"
                for chat_id in AUTHORIZED_CHAT_IDS:
                    await send_telegram_message(application.bot, chat_id, message_text)
            elif value in (2, 3):
                message_text = "⚠️ Calibration finished!" if value == 2 else "⚠️ Calibration failed!"
                for chat_id in AUTHORIZED_CHAT_IDS:
                    await send_telegram_message(application.bot, chat_id, message_text)
                    if os.path.exists(CALIB_DIR):
                        files = sorted(os.listdir(CALIB_DIR))
                        for file in files:
                            if file.lower().endswith(".jpg"):
                                angle = file.split("_")[1].split(".")[0]  # estrae l'angolo dal nome
                                path = os.path.join(CALIB_DIR, file)
                                with open(path, "rb") as f:
                                    await application.bot.send_photo(chat_id=chat_id, photo=f, caption=f"Angle: {angle}°")
            if value == 4: # MOSTRARE ANCHE FOTO OLTRE CHE MESSAGGIO
                message_text = "⚠️ Insect detected!"
                for chat_id in AUTHORIZED_CHAT_IDS:
                    await send_telegram_message(application.bot, chat_id, message_text)        
                        
        await asyncio.sleep(0.1) 


#DEBUG
@authorized_only
async def clear_insect_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Remove from database
        count = photo_repository.remove_insect_photos()

        # Remove files from disk
        folders = ["data/photos/insect", "data/photos/test/patch"]
        removed_files = 0

        for folder in folders:
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                            removed_files += 1
                        except Exception as e:
                            print(f"Failed to remove {file_path}: {e}")

        await update.message.reply_text(
            f"✅ Deleted {count} insect photos from the database.\n"
            f"🗑️ Removed {removed_files} files from the file system."
        )

    except Exception as e:
        await update.message.reply_text(f"Error deleting insect photos: {e}")

@authorized_only
async def get_timelapse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if len(context.args) != 4:
            raise ValueError("Wrong number of arguments")
        pot_id = context.args[0]
        from_date = context.args[1].split("-")
        to_date = context.args[2].split("-")
        fps = int(context.args[3])
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("ID doesn't exist")
        output_path = "data/timelapses/timelapse_" + pot_id + ".mp4"
        pot_service.timelapse(
            pot_id,
            datetime(int(from_date[0]), int(from_date[1]), int(from_date[2])),
            datetime(int(to_date[0]), int(to_date[1]), int(to_date[2])),
            fps,
            output_path,
        )
        await update.message.reply_text("🎬 Your timelapse is ready!")
        await update.message.reply_video(video=open(output_path, "rb"), caption="🌱 Plant growth in timelapse")
    except ValueError as ve:
        await update.message.reply_text(f"Error: {str(ve)}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

@authorized_only
async def get_configuration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if len(context.args) != 1:
            raise ValueError("Wrong number of arguments")
        pot_id = context.args[0]
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("ID doesn't exist")
        pot = PlantPot.from_orm(pot_orm)
        response = pot.configuration
        await update.message.reply_text(
            f"""🌿 Configuration for pot #{pot_id} 🌿

🔧 Watering mode: `{response.watering_mode}`
💧 Humidity threshold: `{response.threshold}%`
📸 Timelapse frequency: `{response.shot_freq} shots/day`
🐛 Insect detection frequency: `{response.insect_freq} shots/minute`
📍 Position: `{response.position}°`
🌱 Plant: `{response.plant}`
🌿 Size: `{response.size} L`
""",
            parse_mode="Markdown"
        )
    except ValueError as ve:
        await update.message.reply_text(f"Error: {str(ve)}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


@authorized_only
async def get_insect_diary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if len(context.args) != 1:
            raise ValueError("Wrong number of arguments")
        pot_id = context.args[0]
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("ID doesn't exist")
        path = pot_service.insect_diary(pot_id)
        await update.message.reply_text("🎬 Your insect diary is ready!")
        await update.message.reply_document(document=open(path, "rb"), caption="🌱 Insect diary")
    except ValueError as ve:
        await update.message.reply_text(f"Error: {str(ve)}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

@authorized_only
async def set_configuration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if len(context.args) != 8:
            raise ValueError("Wrong number of arguments")
        id_str, watering_mode_str, threshold_str, shot_freq_str, insect_freq_str, position_str, plant_str, size_str = context.args
        pot_id = int(id_str)
        threshold = float(threshold_str)
        watering_mode = watering_mode_str.lower() in ['true', '1', 'yes']
        shot_freq = int(shot_freq_str)
        insect_freq = int(insect_freq_str)
        position = int(position_str)
        size = float(size_str)
        plant = plant_str
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("ID doesn't exist")
        pot = PlantPot.from_orm(pot_orm)
        conf_id = pot.configuration.id
        configuration = Configuration(threshold, watering_mode, shot_freq, insect_freq, position, size, plant)
        conf_repository.update(conf_id, configuration.to_orm())
        conf_repository.session.commit()
        await update.message.reply_text(f"Configuration of pot #{pot_id} updated!")
    except ValueError as ve:
        await update.message.reply_text(f"Error: {str(ve)}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


@authorized_only
async def calibrate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    r.rpush("bot_to_rasp", 1)
    await update.message.reply_text("Calibration started!")

@authorized_only
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🤖 <b>Bot commands and parameters</b>\n\n"
        "/start - Authorize this chat and show quick command keyboard\n"
        "/help - Show this help (alias of /start)\n\n"

        "/settings &lt;pot_id&gt; - Show configuration for pot (example: /settings 1)\n\n"

        "/setsettings &lt;id&gt; &lt;watering_mode&gt; &lt;threshold&gt; "
        "&lt;shot_freq&gt; &lt;insect_freq&gt; &lt;position&gt; &lt;plant&gt; &lt;size&gt;\n"
        "  • id: pot id (integer)\n"
        "  • watering_mode: true/false (enable/disable automatic watering)\n"
        "  • threshold: humidity threshold in % (float)\n"
        "  • shot_freq: timelapse shots per day (int)\n"
        "  • insect_freq: insect detection frequency (shots per minute) (int)\n"
        "  • position: servo position in degrees (0–180) (int)\n"
        "  • plant: plant name (string)\n"
        "  • size: pot size in liters (float)\n\n"

        "/timelapse &lt;pot_id&gt; &lt;from YYYY-MM-DD&gt; &lt;to YYYY-MM-DD&gt; &lt;fps&gt;\n"
        "  • Example: /timelapse 1 2025-01-01 2025-01-31 24\n\n"

        "/calibrate - Start camera+servo calibration (you will receive a notification when finished)\n"
        "/diary &lt;pot_id&gt; - Get the insect diary for the pot\n\n"

        "Use the keyboard buttons for quick access to these commands."
    )

    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)




async def post_init(application: Application):
    # start background task
    asyncio.create_task(notify_manager(application))

    # Set the bot command list so Telegram clients show a nice commands UI
    commands = [
        BotCommand("start", "Authorize chat and show keyboard"),
        BotCommand("help", "Show help and quick info"),
        BotCommand("settings", "Show configuration for a pot"),
        BotCommand("setsettings", "Update configuration for a pot"),
        BotCommand("timelapse", "Create a timelapse video for a pot"),
        BotCommand("calibrate", "Start calibration procedure"),
        BotCommand("diary", "Get insect diary for a pot"),
        BotCommand("info", "Show commands and parameter meanings"),
    ]
    try:
        await application.bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"Failed to set bot commands: {e}")


def main():
    application = (
        Application.builder()
        .token(os.getenv("TELEGRAM_TOKEN"))
        .post_init(post_init)
        .connect_timeout(30)
        .read_timeout(60)
        .write_timeout(120)
        .pool_timeout(30)
        .get_updates_read_timeout(60)
        .build()
    )
    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler("settings", get_configuration))
    application.add_handler(CommandHandler("setsettings", set_configuration))
    application.add_handler(CommandHandler("timelapse", get_timelapse))
    application.add_handler(CommandHandler("calibrate", calibrate))
    application.add_handler(CommandHandler("diary", get_insect_diary))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("clean", clear_insect_photos))
    application.run_polling()

if __name__ == "__main__":
    main()