import logging
import sys

def setup_logging() -> None:
    """
    Configures the root logger with a standardized format and levels.
    """
    # Define standard format
    log_format = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Override default basicConfig
    )
    
    # Set third-party library logging levels
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configuration successfully initialized.")
