#!/usr/bin/env python
# pylint: disable=unused-argument

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from clorofillo.persistence.configuration_repository import ConfigurationRepository
from clorofillo.persistence.plant_pot_repository import PlantPotRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clorofillo.model.configuration import Configuration
from clorofillo.model.plant_pot import PlantPot

load_dotenv()

engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
conf_repository = ConfigurationRepository(session)
pot_repository = PlantPotRepository(session)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Informa l'utente su come usare il bot."""
    await update.message.reply_text("TODO")

async def get_configuration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Restituisce la configurazione di un vaso specifico."""
    try:
        if len(context.args) != 1:
            raise ValueError("Numero errato di argomenti")
        
        pot_id = context.args[0]
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("Id non esistente")
        pot = PlantPot.from_orm(pot_orm)
        response = pot.configuration

        await update.message.reply_text(
            f"""🌿 *Configurazione del vaso #{id}* 🌿

🔧 *Modalità irrigazione:* `{response.watering_mode}`
💧 *Soglia umidità:* `{response.threshold}%`
📸 *Frequenza timelapse:* `{response.shot_freq} scatti/giorno`
🐛 *Frequenza rilevazione insetti:* `{response.insect_freq} scatti/minuto`
""",
            parse_mode="Markdown"
        )

    except (IndexError, ValueError):
        await update.message.reply_text("Uso corretto: /settings <ID del vaso>\nEsempio: `/settings 123`", parse_mode="Markdown")

async def set_configuration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Aggiorna la configurazione di un vaso specifico."""
    try:
        if len(context.args) != 5:
            raise ValueError("Numero errato di argomenti")
        id_str, threshold_str, watering_mode_str, shot_freq_str, insect_freq_str = context.args

        pot_id = int(id_str)
        threshold = float(threshold_str)
        watering_mode = watering_mode_str.lower() in ['true', '1', 'yes']
        shot_freq = int(shot_freq_str)
        insect_freq = int(insect_freq_str)

        # prendo il vaso con id pot_id (checkko se esiste), se eesiste prendo la sua configuratione e l aggiorno
        pot_orm = pot_repository.get_by_id(pot_id)
        if pot_orm is None:
            raise ValueError("Id non esistente")
        pot = PlantPot.from_orm(pot_orm)
        conf_id = pot.configuration.id

        # Domain object creation (and data validation)
        configuration = Configuration(threshold, watering_mode, shot_freq, insect_freq)
        conf_repository.update(conf_id, configuration.to_orm())
        await update.message.reply_text(f"Configurazione del vaso #{pot_id} aggiornata con successo!")

    except ValueError as ve:
        await update.message.reply_text(f"Errore di validazione: {ve}\nUso corretto: /set_configuration <ID> <threshold> <watering_mode> <shot_freq> <insect_freq>\nEsempio: /set_configuration 1 30.5 true 3 10")
    except Exception as e:
        await update.message.reply_text(f"Errore imprevisto: {e}")


def main() -> None:
    """Avvia il bot."""
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler("settings", get_configuration))
    application.add_handler(CommandHandler("setsettings", set_configuration))

    application.run_polling()

if __name__ == "__main__":
    main()


# migliroare messaggi errore get e set configuration


# comnando get timelapse
# comando get diario insetti
# comando get misure umidità
# notifica serbatoio vuoto
# notifica insetto rilevato