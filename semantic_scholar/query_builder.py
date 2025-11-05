"""
Query Builder - Genera queries desde terms.json
"""

import json
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def load_terms_json(json_path: str) -> Dict:
    """Cargar terms.json"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_queries_by_area(
    terms_data: Dict,
    limit_areas: Optional[int] = None,
    include_secondary: bool = False
) -> Dict[str, List[str]]:
    """
    Genera queries organizadas por área

    Returns:
        {
            "Mechanistic_Interpretability": [
                "Mechanistic Interpretability",
                "Mechanistic Interpretability Neuroscience",
                ...
            ],
            "Scalable_Oversight": [...],
            ...
        }
    """
    mappings = terms_data.get("AI_Safety_Research_Mappings", {})

    # Limitar áreas si se especifica
    areas_to_process = list(mappings.items())
    if limit_areas:
        areas_to_process = areas_to_process[:limit_areas]

    queries_by_area = {}

    for area_key, payload in areas_to_process:
        area_name = area_key.replace("_", " ")
        queries = []

        # Query nivel 1: Solo área
        queries.append(area_name)

        # Query nivel 2 y 3: Área + Primary Fields + Subfields
        for field_dict in payload.get("Primary_Fields", []):
            for field_name, subfields in field_dict.items():
                # Nivel 2: Área + Field
                query_level2 = f"{area_name} {field_name}"
                queries.append(query_level2)

                # Nivel 3: Área + Field + Subfield
                if subfields and isinstance(subfields, list):
                    for subfield in subfields:
                        query_level3 = f"{area_name} {field_name} {subfield}"
                        queries.append(query_level3)

        # Query nivel 2 y 3: Área + Secondary Fields + Subfields (opcional)
        if include_secondary:
            for field_dict in payload.get("Secondary_Fields", []):
                for field_name, subfields in field_dict.items():
                    # Nivel 2: Área + Field
                    query_level2 = f"{area_name} {field_name}"
                    queries.append(query_level2)

                    # Nivel 3: Área + Field + Subfield
                    if subfields and isinstance(subfields, list):
                        for subfield in subfields:
                            query_level3 = f"{area_name} {field_name} {subfield}"
                            queries.append(query_level3)

        queries_by_area[area_key] = queries
        logger.info(f"Área '{area_key}': {len(queries)} queries generadas")

    return queries_by_area


def build_flat_queries(
    terms_data: Dict,
    limit_areas: Optional[int] = None,
    include_secondary: bool = False
) -> List[str]:
    """
    Genera lista plana de queries (sin organizar por área)

    Returns:
        ["Mechanistic Interpretability", "Mechanistic Interpretability Neuroscience", ...]
    """
    queries_by_area = build_queries_by_area(terms_data, limit_areas, include_secondary)

    flat_queries = []
    for area_queries in queries_by_area.values():
        flat_queries.extend(area_queries)

    return flat_queries
