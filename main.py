#!/usr/bin/env python3
"""
YouTube New Video Bot - Refactored

A clean, maintainable YouTube video notification bot following SOLID principles.
"""

import sys
from src.config.settings import BotConfig
from src.services.bot_service import YouTubeBotService


def validate_python_version() -> None:
    """Ensure correct Python version."""
    if not (3, 12) <= sys.version_info < (3, 13):
        sys.exit("Python >=3.12 and <3.13 is required to run this bot.")


def main() -> None:
    """Main entry point."""
    validate_python_version()
    
    try:
        # Load and validate configuration
        config = BotConfig.from_env()
        config.validate()
        
        # Create and start the bot service
        bot_service = YouTubeBotService(config)
        bot_service.start()
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Bot stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()