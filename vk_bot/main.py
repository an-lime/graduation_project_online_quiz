import logging
import os
import sys
from pathlib import Path

# ==========================================
# ИНИЦИАЛИЗАЦИЯ DJANGO
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Online_Quiz_Core.settings')

import django

django.setup()

# ==========================================

from vkbottle import Bot

from config_data.config import VkBotConfig, load_config
from handlers import main_labeler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Bot started...")

    config: VkBotConfig = load_config()

    bot = Bot(token=config.vkBot.token)
    bot.labeler.load(main_labeler)

    bot.run_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
