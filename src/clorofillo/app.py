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
PATCH_DIR = "data/photos/insect/patch/"

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
                        files = [f for f in os.listdir(CALIB_DIR) if f.lower().endswith(".jpg")]
                        files.sort(key=lambda x: int(x.split("_")[0]))
                        for file in files:
                            angle = file.split("_")[0]
                            path = os.path.join(CALIB_DIR, file)
                            with open(path, "rb") as f:
                                await application.bot.send_photo(chat_id=chat_id, photo=f, caption=f"Angle: {angle}°")

            elif value == 4:
                message_text = "⚠️ Possible insect detected!"
                for chat_id in AUTHORIZED_CHAT_IDS:
                    await send_telegram_message(application.bot, chat_id, message_text)
                    if os.path.exists(PATCH_DIR):
                        files = [f for f in os.listdir(PATCH_DIR) if f.lower().endswith(".jpg")]
                        for file in files:
                            pot_id = file.split("_")[1]
                            timestamp = file.split("_")[2]
                            path = os.path.join(PATCH_DIR, file)
                            with open(path, "rb") as f:
                                await application.bot.send_photo(
                                    chat_id=chat_id,
                                    photo=f,
                                    caption=f"Pot: {pot_id}, timestamp: {timestamp}"
                                )
                            os.remove(path)
  
                        
        await asyncio.sleep(0.1) 

# DEBUG
@authorized_only
async def kill_io_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ Stopping io_app.py...")
    os.system("/home/rosario/Documents/Projects/clorofillo/kill_io.sh &")

# DEBUG
@authorized_only
async def start_io_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ Starting io_app.py...")
    os.system("/home/rosario/Documents/Projects/clorofillo/start_io.sh &")

#DEBUG
@authorized_only
async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ Raspberry Pi is shutting down...")
    # esegue shutdown in background
    os.system("sudo shutdown now")


#DEBUG
@authorized_only
async def clean_insect_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

#DEBUG
@authorized_only
async def clean_timelapse_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        photo_repository.remove_timelapse_photos()
        folders = ["data/photos/timelapse", "data/photos/timelapse/test"]
        removed_files = 0

        for folder in folders:
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder):
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        if os.path.isfile(file_path):
                            try:
                                os.remove(file_path)
                                removed_files += 1
                            except Exception as e:
                                print(f"Failed to remove {file_path}: {e}")

        await update.message.reply_text(
            f"✅ Removed {removed_files} timelapse photos from the file system."
        )

    except Exception as e:
        await update.message.reply_text(f"Error deleting timelapse photos: {e}")


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
        freqs = [str(elem) for elem in response.shot_freq]
        await update.message.reply_text(
            f"""🌿 Configuration for pot #{pot_id} 🌿

🔧 Watering mode: `{response.watering_mode}`
💧 Humidity threshold: `{response.threshold}%`
📸 Timelapse times: `{', '.join(freqs)}`
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
async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 2:
            raise ValueError("Usage: /set_threshold <pot_id> <threshold>")
        pot_id = int(context.args[0])
        threshold = float(context.args[1])
        pot_orm = pot_repository.get_by_id(pot_id)
        if not pot_orm:
            raise ValueError("Pot ID not found")
        conf = Configuration.from_orm(pot_orm.configuration)
        conf.threshold = threshold
        conf_repository.update(conf.id, conf.to_orm())
        await update.message.reply_text(f"✅ Threshold of pot #{pot_id} set to {threshold}%")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


@authorized_only
async def set_watering_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 2:
            raise ValueError("Usage: /set_watering_mode <pot_id> <true|false>")
        pot_id = int(context.args[0])
        watering_mode = context.args[1].lower() in ['true','1','yes']
        pot_orm = pot_repository.get_by_id(pot_id)
        if not pot_orm:
            raise ValueError("Pot ID not found")
        conf = Configuration.from_orm(pot_orm.configuration)
        conf.watering_mode = watering_mode
        conf_repository.update(conf.id, conf.to_orm())
        await update.message.reply_text(f"✅ Watering mode of pot #{pot_id} set to {watering_mode}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


@authorized_only
async def set_shot_freq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 2:
            raise ValueError("Usage: /set_shot_freq <pot_id> <HH:MM,HH:MM,...>")
        pot_id = int(context.args[0])
        shot_freq = [x.strip() for x in context.args[1].split(",")]
        pot_orm = pot_repository.get_by_id(pot_id)
        if not pot_orm:
            raise ValueError("Pot ID not found")
        conf = Configuration.from_orm(pot_orm.configuration)
        conf.shot_freq = shot_freq
        conf_repository.update(conf.id, conf.to_orm())
        await update.message.reply_text(f"✅ Shot frequency of pot #{pot_id} updated: {', '.join(shot_freq)}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


@authorized_only
async def set_insect_freq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 2:
            raise ValueError("Usage: /set_insect_freq <pot_id> <frequency>")
        pot_id = int(context.args[0])
        insect_freq = int(context.args[1])
        pot_orm = pot_repository.get_by_id(pot_id)
        if not pot_orm:
            raise ValueError("Pot ID not found")
        conf = Configuration.from_orm(pot_orm.configuration)
        conf.insect_freq = insect_freq
        conf_repository.update(conf.id, conf.to_orm())
        await update.message.reply_text(f"✅ Insect detection frequency of pot #{pot_id} set to {insect_freq} shots/min")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


@authorized_only
async def set_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 2:
            raise ValueError("Usage: /set_position <pot_id> <position>")
        pot_id = int(context.args[0])
        position = int(context.args[1])
        pot_orm = pot_repository.get_by_id(pot_id)
        if not pot_orm:
            raise ValueError("Pot ID not found")
        conf = Configuration.from_orm(pot_orm.configuration)
        conf.position = position
        conf_repository.update(conf.id, conf.to_orm())
        await update.message.reply_text(f"✅ Position of pot #{pot_id} set to {position}°")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


@authorized_only
async def set_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 2:
            raise ValueError("Usage: /set_size <pot_id> <size>")
        pot_id = int(context.args[0])
        size = float(context.args[1])
        pot_orm = pot_repository.get_by_id(pot_id)
        if not pot_orm:
            raise ValueError("Pot ID not found")
        conf = Configuration.from_orm(pot_orm.configuration)
        conf.size = size
        conf_repository.update(conf.id, conf.to_orm())
        await update.message.reply_text(f"✅ Size of pot #{pot_id} set to {size} L")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


@authorized_only
async def set_plant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 2:
            raise ValueError("Usage: /set_plant <pot_id> <plant_name>")
        pot_id = int(context.args[0])
        plant = context.args[1]
        pot_orm = pot_repository.get_by_id(pot_id)
        if not pot_orm:
            raise ValueError("Pot ID not found")
        conf = Configuration.from_orm(pot_orm.configuration)
        conf.plant = plant
        conf_repository.update(conf.id, conf.to_orm())
        await update.message.reply_text(f"✅ Plant of pot #{pot_id} set to {plant}")
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
        shot_freq = [x.strip() for x in shot_freq_str.split(",")] if shot_freq_str else []
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
        "  • shot_freq: timelapse shots per day (HH:MM,HH:MM,...)\n"
        "  • insect_freq: insect detection frequency (shots per minute) (int)\n"
        "  • position: servo position in degrees (0–180) (int)\n"
        "  • plant: plant name (string)\n"
        "  • size: pot size in liters (float)\n\n"

        "# Individual setters for convenience:\n"
        "/set_threshold &lt;pot_id&gt; &lt;threshold&gt; - Set humidity threshold\n"
        "/set_watering_mode &lt;pot_id&gt; &lt;true|false&gt; - Enable/disable watering\n"
        "/set_shot_freq &lt;pot_id&gt; &lt;HH:MM,HH:MM,...&gt; - Set timelapse shot times\n"
        "/set_insect_freq &lt;pot_id&gt; &lt;frequency&gt; - Set insect detection frequency (shots/min)\n"
        "/set_position &lt;pot_id&gt; &lt;position&gt; - Set servo position (0–180°)\n"
        "/set_size &lt;pot_id&gt; &lt;size&gt; - Set pot size in liters\n"
        "/set_plant &lt;pot_id&gt; &lt;plant_name&gt; - Set plant name\n\n"

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
    application.add_handler(CommandHandler("set_settings", set_configuration))
    application.add_handler(CommandHandler("timelapse", get_timelapse))
    application.add_handler(CommandHandler("calibrate", calibrate))
    application.add_handler(CommandHandler("diary", get_insect_diary))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("cleantimelapse", clean_timelapse_photos))
    application.add_handler(CommandHandler("cleaninsect", clean_insect_photos))
    application.add_handler(CommandHandler("shutdown", shutdown))
    application.add_handler(CommandHandler("set_threshold", set_threshold))
    application.add_handler(CommandHandler("set_watering_mode", set_watering_mode))
    application.add_handler(CommandHandler("set_shot_freq", set_shot_freq))
    application.add_handler(CommandHandler("set_insect_freq", set_insect_freq))
    application.add_handler(CommandHandler("set_position", set_position))
    application.add_handler(CommandHandler("set_size", set_size))
    application.add_handler(CommandHandler("set_plant", set_plant))
    application.add_handler(CommandHandler("killio", kill_io_app))
    application.add_handler(CommandHandler("startio", start_io_app))

    application.run_polling()


if __name__ == "__main__":
    main()