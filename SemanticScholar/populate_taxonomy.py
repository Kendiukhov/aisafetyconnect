#!/usr/bin/env python3
"""
Script para poblar la base de datos con la taxonomía desde terms.json
"""

import json
import psycopg2
import sys
from pathlib import Path

def get_db_connection():
    """Obtener conexión a la base de datos"""
    return psycopg2.connect(
        host="localhost",
        port=6543,
        database="ai_safety",
        user="scholar_user",
        password="scholar_pass_2024"
    )

def populate_taxonomy():
    """Poblar la base de datos con la taxonomía"""
    
    # Leer el archivo terms.json
    terms_path = Path("/Users/janeth/Extractors Notebook/terms.json")
    if not terms_path.exists():
        print(f"Error: No se encontró el archivo {terms_path}")
        return False
    
    with open(terms_path, 'r', encoding='utf-8') as f:
        taxonomy = json.load(f)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("Poblando taxonomía en la base de datos...")
        
        # Limpiar tablas existentes
        cursor.execute("DELETE FROM paper_taxonomy")
        cursor.execute("DELETE FROM paper_concept")
        cursor.execute("DELETE FROM paper")
        cursor.execute("DELETE FROM subfield")
        cursor.execute("DELETE FROM field")
        cursor.execute("DELETE FROM area")
        
        # Insertar áreas (navegar por la estructura anidada)
        for main_key, main_data in taxonomy.items():
            for area_id, area_data in main_data.items():
                # Convertir area_id a nombre legible
                area_name = area_id.replace('_', ' ')
                cursor.execute(
                    "INSERT INTO area (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                    (area_id, area_name)
                )
                print(f"Área insertada: {area_name}")
                
                # Insertar fields (primary y secondary)
                for field_type in ['Primary_Fields', 'Secondary_Fields']:
                    if field_type in area_data:
                        for field_dict in area_data[field_type]:
                            for field_name, subfields in field_dict.items():
                                is_primary = (field_type == 'Primary_Fields')
                                cursor.execute(
                                    "INSERT INTO field (area_id, name, is_primary) VALUES (%s, %s, %s) ON CONFLICT (area_id, name) DO NOTHING",
                                    (area_id, field_name, is_primary)
                                )
                                print(f"  Field insertado: {field_name} ({'Primary' if is_primary else 'Secondary'})")
                                
                                # Obtener el field_id para insertar subfields
                                cursor.execute("SELECT id FROM field WHERE area_id = %s AND name = %s", (area_id, field_name))
                                field_result = cursor.fetchone()
                                if field_result:
                                    field_id = field_result[0]
                                    
                                    # Insertar subfields
                                    for subfield_name in subfields:
                                        cursor.execute(
                                            "INSERT INTO subfield (alias, field_id, weight) VALUES (%s, %s, %s) ON CONFLICT (alias, field_id) DO NOTHING",
                                            (subfield_name, field_id, 1.0)
                                        )
                                        print(f"    Subfield insertado: {subfield_name}")
        
        conn.commit()
        print("✅ Taxonomía poblada exitosamente!")
        
        # Mostrar estadísticas
        cursor.execute("SELECT COUNT(*) FROM area")
        areas_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM field")
        fields_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM subfield")
        subfields_count = cursor.fetchone()[0]
        
        print(f"\n📊 Estadísticas:")
        print(f"  Áreas: {areas_count}")
        print(f"  Fields: {fields_count}")
        print(f"  Subfields: {subfields_count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error poblando taxonomía: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = populate_taxonomy()
    sys.exit(0 if success else 1)
