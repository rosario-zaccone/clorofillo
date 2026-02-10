#!/usr/bin/env python3
import logging
import os, re, io
import base64
from PIL import Image
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
from clorofillo.service.plant_pot_service import PlantPotService
from clorofillo.service.plant_photo_service import PlantPhotoService
from clorofillo.persistence.orm_models import *
from telegram.ext import MessageHandler, filters


load_dotenv()

# SQLite session, repository and service objects
engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
conf_repository = ConfigurationRepository(session)
pot_repository = PlantPotRepository(session)
photo_repository = PlantPhotoRepository(session)
pot_service = PlantPotService(pot_repository)
photo_service = PlantPhotoService(photo_repository, None)

CALIB_DIR = os.getenv("CALIB_DIR", "data/calibration")
PATCH_DIR = os.getenv("PATCH_DIR", "data/photos/sighting/patch/")
TIMELAPSE_DIR = os.getenv("TIMELAPSE_DIR", "data/timelapses/")

r = redis.Redis(host='localhost', port=6379, db=0)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

AUTHORIZED_CHAT_IDS = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    AUTHORIZED_CHAT_IDS.add(chat_id)
    await update.message.reply_text(
        "Hi! You are authorized. Use the keyboard below or type a command.\n\n"
        "Tip: use /info to see command details and parameter meanings."
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
    loop = asyncio.get_running_loop()

    while True:
        try:
            _, message = await loop.run_in_executor(
                None, lambda: r.blpop("rasp_to_bot", 0)
            )
            message = message.decode("utf-8").strip()
            error_msg = None
            if "|" in message:
                code_str, error_msg = message.split("|", 1)
                code = int(code_str)
            else:
                code = int(message)
            if code == 1:
                message_text = "⚠️ Empty tank!"
                for chat_id in AUTHORIZED_CHAT_IDS:
                    await send_telegram_message(application.bot, chat_id, message_text)
            elif code in (2, 3):
                message_text = (
                    "👌 Calibration completed!"
                    if code == 2
                    else f"⚠️ {error_msg or 'Calibration error'}"
                )

                for chat_id in AUTHORIZED_CHAT_IDS:
                    await send_telegram_message(application.bot, chat_id, message_text)

                    if os.path.exists(CALIB_DIR):
                        files = [
                            f for f in os.listdir(CALIB_DIR)
                            if f.lower().endswith(".jpg")
                        ]
                        files.sort(key=lambda x: int(x.split("_")[0]))

                        for file in files:
                            angle = file.split("_")[0]
                            path = os.path.join(CALIB_DIR, file)
                            with open(path, "rb") as f:
                                await application.bot.send_photo(
                                    chat_id=chat_id,
                                    photo=f,
                                    caption=f"Angle: {angle}°"
                                )
            elif code == 4:
                message_text = "⚠️ Possible sighting detected!"
                for chat_id in AUTHORIZED_CHAT_IDS:
                    await send_telegram_message(application.bot, chat_id, message_text)

                    if os.path.exists(PATCH_DIR):
                        files = [
                            f for f in os.listdir(PATCH_DIR)
                            if f.lower().endswith(".jpg")
                        ]

                        for file in files:
                            try:
                                pot_id = file.split("_")[1]
                                timestamp = file.split("_")[2].replace(".jpg", "")
                                path = os.path.join(PATCH_DIR, file)

                                with open(path, "rb") as f:
                                    await application.bot.send_photo(
                                        chat_id=chat_id,
                                        photo=f,
                                        caption=f"Pot: {pot_id}, timestamp: {timestamp}"
                                    )

                                os.remove(path)

                            except Exception as e:
                                logger.warning(f"Failed to send/remove patch {file}: {e}")
        except Exception:
            logger.exception("notify_manager error")
            await asyncio.sleep(1)

@authorized_only
async def set_apikey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 1:
            raise ValueError("Usage: /set_apikey <new_api_key>")
        new_api_key = context.args[0].strip()

        env_path = ".env"
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()

        found = False
        for i, line in enumerate(lines):
            if line.startswith("API_KEY="):
                lines[i] = f"API_KEY={new_api_key}\n"
                found = True
                break

        if not found:
            lines.append(f"API_KEY={new_api_key}\n")

        with open(env_path, "w") as f:
            f.writelines(lines)
        os.environ["API_KEY"] = new_api_key
        await update.message.reply_text(f"✅ API KEY updated!")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")


@authorized_only
async def kill_io_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ Stopping io_app.py...")
    os.system("/home/rosario/Documents/Projects/clorofillo/kill_io.sh &")

@authorized_only
async def start_io_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ Starting io_app.py...")
    os.system("/home/rosario/Documents/Projects/clorofillo/start_io.sh &")

#DEBUG
@authorized_only
async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ Raspberry Pi is shutting down...")
    os.system("sudo shutdown now")


#DEBUG
@authorized_only
async def clean_sighting_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Remove from database
        count = photo_repository.remove_sighting_photos()

        # Remove files from disk
        folders = ["data/photos/sighting", "data/photos/test/patch"]
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
            f"✅ Deleted {count} sighting photos from the database.\n"
            f"🗑️ Removed {removed_files} files from the file system."
        )

    except Exception as e:
        await update.message.reply_text(f"Error deleting sighting photos: {e}")

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
    # Available filters: none, bw, saturation, contrast, white_balance
    try:
        if len(context.args) != 5:
            raise ValueError("Wrong number of arguments")
        pot_id = context.args[0]
        from_date = context.args[1].split("-")
        to_date = context.args[2].split("-")
        fps = int(context.args[3])
        filter_type = context.args[4]
        
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("ID doesn't exist")
        
        output_path = os.path.join(TIMELAPSE_DIR, f"timelapse_{pot_id}.mp4")
        pot_service.timelapse(
            pot_id,
            datetime(int(from_date[0]), int(from_date[1]), int(from_date[2])),
            datetime(int(to_date[0]), int(to_date[1]), int(to_date[2])),
            fps,
            output_path,
            filter_type,
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
🐛 Sighting detection frequency: `{response.sighting_freq} shots/minute`
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
async def get_sighting_diary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if len(context.args) != 1:
            raise ValueError("Wrong number of arguments")
        pot_id = context.args[0]
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("ID doesn't exist")
        path = pot_service.sighting_diary(pot_id)
        await update.message.reply_text("🎬 Your sighting diary is ready!")
        await update.message.reply_document(document=open(path, "rb"), caption="🌱 Sighting diary")
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
async def set_sighting_freq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 2:
            raise ValueError("Usage: /set_sighting_freq <pot_id> <frequency>")
        pot_id = int(context.args[0])
        sighting_freq = int(context.args[1])
        pot_orm = pot_repository.get_by_id(pot_id)
        if not pot_orm:
            raise ValueError("Pot ID not found")
        conf = Configuration.from_orm(pot_orm.configuration)
        conf.sighting_freq = sighting_freq
        conf_repository.update(conf.id, conf.to_orm())
        await update.message.reply_text(f"✅ Sighting detection frequency of pot #{pot_id} set to {sighting_freq} shots/min")
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
        id_str, watering_mode_str, threshold_str, shot_freq_str, sighting_freq_str, position_str, plant_str, size_str = context.args
        pot_id = int(id_str)
        threshold = float(threshold_str)
        watering_mode = watering_mode_str.lower() in ['true', '1', 'yes']
        shot_freq = [x.strip() for x in shot_freq_str.split(",")] if shot_freq_str else []
        sighting_freq = int(sighting_freq_str)
        position = int(position_str)
        size = float(size_str)
        plant = plant_str
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("ID doesn't exist")
        pot = PlantPot.from_orm(pot_orm)
        conf_id = pot.configuration.id
        configuration = Configuration(threshold, watering_mode, shot_freq, sighting_freq, position, size, plant)
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
        "🤖 <b>Clorofillo Bot – Command Reference</b>\n\n"

        "<b>Authorization</b>\n"
        "/start – Authorize this chat\n"
        "/help – Alias of /start\n\n"

        "<b>Configuration</b>\n"
        "/settings &lt;pot_id&gt;\n"
        "  • Show current configuration for a pot\n"
        "  • Example: <code>/settings 1</code>\n\n"

        "/set_settings &lt;pot_id&gt; &lt;watering_mode&gt; &lt;threshold&gt; "
        "&lt;shot_freq&gt; &lt;sighting_freq&gt; &lt;position&gt; &lt;plant&gt; &lt;size&gt;\n"
        "  • watering_mode: <code>true | false</code>\n"
        "  • threshold: humidity % (float)\n"
        "  • shot_freq: <code>HH:MM,HH:MM,...</code>\n"
        "  • sighting_freq: shots per minute (int)\n"
        "  • position: servo angle 0–180 (int)\n"
        "  • plant: plant name\n"
        "  • size: pot size in liters (float)\n\n"

        "<b>Quick setters</b>\n"
        "/set_threshold &lt;pot_id&gt; &lt;threshold&gt;\n"
        "/set_watering_mode &lt;pot_id&gt; &lt;true|false&gt;\n"
        "/set_shot_freq &lt;pot_id&gt; &lt;HH:MM,HH:MM,...&gt;\n"
        "/set_sighting_freq &lt;pot_id&gt; &lt;shots_per_min&gt;\n"
        "/set_position &lt;pot_id&gt; &lt;degrees&gt;\n"
        "/set_size &lt;pot_id&gt; &lt;liters&gt;\n"
        "/set_plant &lt;pot_id&gt; &lt;plant_name&gt;\n\n"

        "<b>Media</b>\n"
        "/timelapse &lt;pot_id&gt; &lt;from YYYY-MM-DD&gt; "
        "&lt;to YYYY-MM-DD&gt; &lt;fps&gt; &lt;filter&gt;\n"
        "  • filter: none | bw | saturation | contrast | white_balance\n"
        "  • Example:\n"
        "    <code>/timelapse 1 2025-01-01 2025-01-31 24 none</code>\n\n"

        "/diary &lt;pot_id&gt; – Get sighting diary PDF\n\n"

        "<b>System</b>\n"
        "/calibrate – Start camera/servo calibration\n"
        "/startio – Start io_app.py\n"
        "/killio – Stop io_app.py\n\n"

        "<b>Maintenance (DEBUG)</b>\n"
        "/cleantimelapse – Delete all timelapse photos\n"
        "/cleansighting – Delete all sighting photos\n"
        "/shutdown – Shutdown Raspberry Pi\n\n"

        "<b>Sightings</b>\n"
        "Reply to a detected photo with:\n"
        "<code>/savesighting &lt;description&gt;</code>\n"
        "  • Example: <code>/savesighting aphids</code>\n"
    )

    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def handle_photo_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    if msg.text.startswith("/savesighting") and msg.reply_to_message and msg.reply_to_message.photo:
        await save_sighting(update, context)
    elif msg.text.startswith("/identifyinvertebrate") and msg.reply_to_message and msg.reply_to_message.photo:
        await identify_invertebrate(update, context)



@authorized_only
async def save_sighting(update, context):
    msg = update.message
    if (
        msg and
        msg.text and
        msg.text.startswith("/savesighting") and
        msg.reply_to_message and
        msg.reply_to_message.photo
    ):
        parts = msg.text.split(" ", 1)
        description = parts[1] if len(parts) > 1 else "sighting"

        description = description.lower().strip()
        description = re.sub(r"\s+", "_", description)
        description = re.sub(r"[^a-z0-9_]", "", description)

        original_caption = str(msg.reply_to_message.caption or "")

        photo_file = await msg.reply_to_message.photo[-1].get_file()

        folder = "data/photos/sighting"
        os.makedirs(folder, exist_ok=True)

        timestamp_str = original_caption.split(",")[1].split(" timestamp: ")[1]
        pot_id = original_caption.split(",")[0].split("Pot: ")[1]

        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        safe_timestamp = dt.strftime("%Y-%m-%d_%H-%M-%S")

        filename = f"{pot_id}_{description}_{safe_timestamp}.jpg"
        file_path = os.path.join(folder, filename)

        await photo_service.add_sighting(photo_file, pot_id, dt, file_path)

        await update.message.reply_text(f"Sighting saved: {filename}")

@authorized_only
async def identify_invertebrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not (msg and msg.text and msg.text.strip().startswith("/identifyinvertebrate") and 
            msg.reply_to_message and msg.reply_to_message.photo):
        await update.message.reply_text("⚠️ Use /identifyinvertebrate only as a reply to a photo.")
        return

    try:
        photo_file = await msg.reply_to_message.photo[-1].get_file()
        bytes_io = io.BytesIO()
        await photo_file.download_to_memory(out=bytes_io)
        bytes_io.seek(0)
        img = Image.open(bytes_io)
        out_buf = io.BytesIO()
        img.save(out_buf, format="JPEG")
        patch_base64 = base64.b64encode(out_buf.getvalue()).decode("utf-8")
        invertebrates = photo_service.detect_invertebrate([patch_base64])
        if invertebrates:
            invertebrate_list = ""
            for invertebrate in invertebrates:
                invertebrate_list += invertebrate
                invertebrate_list += "\n"
            await update.message.reply_text(f"🔍 Possible animals:\n{invertebrate_list}")
        else:
            await update.message.reply_text("❓ No animals identified with sufficient confidence.")

    except Exception as ex:
        await update.message.reply_text(f"⚠️ Error identifying animals: {ex}")


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
        BotCommand("diary", "Get sighting diary for a pot"),
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
    application.add_handler(CommandHandler("diary", get_sighting_diary))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("cleantimelapse", clean_timelapse_photos))
    application.add_handler(CommandHandler("cleansighting", clean_sighting_photos))
    application.add_handler(CommandHandler("shutdown", shutdown))
    application.add_handler(CommandHandler("set_threshold", set_threshold))
    application.add_handler(CommandHandler("set_watering_mode", set_watering_mode))
    application.add_handler(CommandHandler("set_shot_freq", set_shot_freq))
    application.add_handler(CommandHandler("set_sighting_freq", set_sighting_freq))
    application.add_handler(CommandHandler("set_position", set_position))
    application.add_handler(CommandHandler("set_size", set_size))
    application.add_handler(CommandHandler("set_plant", set_plant))
    application.add_handler(CommandHandler("killio", kill_io_app))
    application.add_handler(CommandHandler("startio", start_io_app))


    application.add_handler(MessageHandler(filters.TEXT, handle_photo_commands))
    application.add_handler(CommandHandler("set_apikey", set_apikey))
    #application.add_handler(MessageHandler(filters.TEXT, save_sighting))
    #application.add_handler(MessageHandler(filters.TEXT, identify_invertebrate))


    application.run_polling()


if __name__ == "__main__":
    main()