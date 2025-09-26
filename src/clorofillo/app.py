import logging
import os

from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from clorofillo.persistence.configuration_repository import ConfigurationRepository
from clorofillo.persistence.plant_pot_repository import PlantPotRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clorofillo.model.configuration import Configuration
from clorofillo.model.plant_pot import PlantPot
from clorofillo.business.plant_pot_service import PlantPotService

load_dotenv()

engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
conf_repository = ConfigurationRepository(session)
pot_repository = PlantPotRepository(session)
pot_service = PlantPotService(pot_repository)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("TODO")


async def get_timelapse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return a timelapse"""
    try:
        if len(context.args) != 4:
            raise ValueError("Wrong arguments number")
        
        pot_id = context.args[0]
        from_date = context.args[1].split("-")
        to_date = context.args[2].split("-")
        fps = int(context.args[3])
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("Id doesn't exist")
        output_path = "data/timelapses/timelapse_" + pot_id + ".mp4"
        pot_service.timelapse(pot_id, datetime(int(from_date[0]), int(from_date[1]), int(from_date[2])), datetime(int(to_date[0]), int(to_date[1]), int(to_date[2])), fps, output_path)

        await update.message.reply_text("🎬 Your timelapse is ready!")
        await update.message.reply_video(
            video=open(output_path, "rb"),
            caption="🌱 Plant growth in timelapse"
        )

    except ValueError as ve:
        await update.message.reply_text(f"Error: {str(ve)}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def get_configuration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return a plant pot configuration"""
    try:
        if len(context.args) != 1:
            raise ValueError("Wrong arguments number")
        
        pot_id = context.args[0]
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("Id doesn't exist")
        pot = PlantPot.from_orm(pot_orm)
        response = pot.configuration
        await update.message.reply_text(
            f"""🌿 *Configurazione del vaso #{pot_id}* 🌿

        🔧 *Modalità irrigazione:* `{response.watering_mode}`
        💧 *Soglia umidità:* `{response.threshold}%`
        📸 *Frequenza timelapse:* `{response.shot_freq} scatti/giorno`
        🐛 *Frequenza rilevazione insetti:* `{response.insect_freq} scatti/minuto`
        📍 *Posizione:* `{response.position}°`
        """,
            parse_mode="Markdown"
        )

    except ValueError as ve:
        await update.message.reply_text(f"Error: {str(ve)}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    
async def set_configuration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update the plant pot configuration"""
    try:
        if len(context.args) != 6:
            raise ValueError("Wrong arguments number")
        id_str, threshold_str, watering_mode_str, shot_freq_str, insect_freq_str, position_str = context.args

        pot_id = int(id_str)
        threshold = float(threshold_str)
        watering_mode = watering_mode_str.lower() in ['true', '1', 'yes']
        shot_freq = int(shot_freq_str)
        insect_freq = int(insect_freq_str)
        position = int(position_str)

        # prendo il vaso con id pot_id (checkko se esiste), se eesiste prendo la sua configuratione e l aggiorno
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("Id doesn't exist")
        pot = PlantPot.from_orm(pot_orm)
        conf_id = pot.configuration.id

        # Domain object creation (and data validation)
        configuration = Configuration(threshold, watering_mode, shot_freq, insect_freq, position)
        conf_repository.update(conf_id, configuration.to_orm())
        conf_repository.session.commit()
        await update.message.reply_text(f"COnfiguration of pot #{pot_id} updated!")

    except ValueError as ve:
        await update.message.reply_text(f"Error: {str(ve)}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


def main() -> None:
    """Avvia il bot."""
    application = (
        Application.builder()
        .token(os.getenv("TELEGRAM_TOKEN"))
        .connect_timeout(30)         # tempo massimo per stabilire la connessione
        .read_timeout(60)            # tempo massimo per ricevere la risposta
        .write_timeout(120)          # tempo massimo per completare l'upload del file
        .pool_timeout(30)            # timeout per ottenere una connessione dalla pool
        .get_updates_read_timeout(60)  # utile solo con polling
        .build()
    )
    

    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler("settings", get_configuration))
    application.add_handler(CommandHandler("setsettings", set_configuration))
    application.add_handler(CommandHandler("timelapse", get_timelapse))

    application.run_polling()

if __name__ == "__main__":
    main()


# comando get diario insetti
# comando get misure umidità grafico
# notifica serbatoio vuoto
# notifica insetto rilevato