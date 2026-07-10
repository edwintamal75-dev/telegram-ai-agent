from __future__ import annotations

from .config import load_settings
from .database import Database
from .llm import AIWriter
from .telegram_bot import TelegramAgentBot


def main() -> None:
    settings = load_settings()
    database = Database(settings.database_path)
    database.migrate()

    ai_writer = AIWriter(settings)
    bot = TelegramAgentBot(settings, database, ai_writer)
    bot.run()


if __name__ == "__main__":
    main()

