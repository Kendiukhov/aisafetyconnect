import logging
import sys
from lesswrong_extractor import LessWrongExtractor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Script principal de extracción"""
    try:
        # Extraer top usuarios de LessWrong
        extractor = LessWrongExtractor()

        # Extraer 20 usuarios más relevantes
        logger.info("=== EXTRACCIÓN: Top 20 usuarios de AI Safety ===")
        extractor.extract_and_save_all(limit=20)

        # Para test con menos usuarios:
        # extractor.extract_and_save_all(limit=3)

        # Para extracción completa:
        # extractor.extract_and_save_all(limit=100)

    except Exception as e:
        logger.error(f"Error en ejecución principal: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()