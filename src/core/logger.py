import sys

from loguru import logger

from src.core.config import settings


def setup_logging():
    """
    Enterprise Observability.
    Configure Loguru to replace standard logging. Outputs structured JSON in production,
    or pretty-formatted logs in development.
    """
    logger.remove()  # Remove default handler

    # Intercept standard logging messages toward Loguru
    import logging
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    if settings.ENVIRONMENT == "production":
        # Structured JSON logging for ELK / Splunk / Datadog
        logger.add(
            sys.stdout,
            format="{message}",
            serialize=True,
            level=settings.LOG_LEVEL,
            backtrace=True,
            diagnose=False,
        )
    else:
        # Human-readable colored output for development
        logger.add(
            sys.stdout,
            colorize=True,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=settings.LOG_LEVEL,
        )

    logger.info(f"Initialized Enterprise Logger in {settings.ENVIRONMENT} mode.")
    return logger

# Export the configured logger
system_logger = setup_logging()
