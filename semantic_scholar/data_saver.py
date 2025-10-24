"""
Data Saver - Guarda papers en archivos JSON
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)


class DataSaver:
    """Maneja guardado de papers en archivos JSON"""

    def __init__(self, output_dir: str = "../raw_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def save_query_results(
        self,
        query: str,
        papers: List[Dict],
        metadata: Dict = None
    ) -> Path:
        """
        Guardar papers de una query en archivo JSON

        Args:
            query: La query ejecutada
            papers: Lista de papers
            metadata: Metadatos adicionales (duración, filtros, etc)

        Returns:
            Path al archivo guardado
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = self._sanitize_filename(query)
        filename = f"papers_{safe_query}_{timestamp}.json"
        filepath = self.output_dir / filename

        output_data = {
            "query": query,
            "timestamp": timestamp,
            "total_papers": len(papers),
            "papers": papers
        }

        # Agregar metadata si existe
        if metadata:
            output_data.update(metadata)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Guardado: {filepath.name} ({len(papers)} papers)")
        return filepath

    def save_summary(self, summary: Dict) -> Path:
        """Guardar resumen de extracción"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"extraction_summary_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"📊 Resumen guardado: {filepath.name}")
        return filepath

    def save_area_results(
        self,
        area_name: str,
        all_papers: List[Dict],
        queries_processed: List[str]
    ) -> Path:
        """
        Guardar todos los papers de un área en un solo archivo

        Args:
            area_name: Nombre del área
            all_papers: Todos los papers del área
            queries_processed: Lista de queries ejecutadas

        Returns:
            Path al archivo guardado
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_area = self._sanitize_filename(area_name)
        filename = f"area_{safe_area}_{timestamp}.json"
        filepath = self.output_dir / filename

        output_data = {
            "area": area_name,
            "timestamp": timestamp,
            "total_papers": len(all_papers),
            "queries_count": len(queries_processed),
            "queries": queries_processed,
            "papers": all_papers
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"📁 Área guardada: {filepath.name} ({len(all_papers)} papers)")
        return filepath

    @staticmethod
    def _sanitize_filename(text: str) -> str:
        """Convertir texto a nombre de archivo seguro"""
        return text.replace(" ", "_").replace("/", "_")[:50]
