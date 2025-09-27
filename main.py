import logging
import sys
from lesswrong_extractor import LessWrongExtractor

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
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
        # MVP: Extraer top 100 usuarios de LessWrong
        extractor = LessWrongExtractor()

        # Test con 3 usuarios primero
        logger.info("=== TEST: Extrayendo 3 usuarios ===")
        extractor.extract_and_save_all(limit=3)

        # Si funciona, ejecutar completo
        # logger.info("=== COMPLETO: Extrayendo 100 usuarios ===")
        # extractor.extract_and_save_all(limit=100)

    except Exception as e:
        logger.error(f"Error en ejecución principal: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()