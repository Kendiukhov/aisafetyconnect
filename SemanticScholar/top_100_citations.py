#!/usr/bin/env python3
"""
Script para extraer los top 100 papers por citas del archivo CSV de Semantic Scholar
"""

import pandas as pd
import sys
from pathlib import Path

def get_top_100_citations(csv_file_path, output_file=None):
    """
    Extrae los top 100 papers por número de citas
    
    Args:
        csv_file_path (str): Ruta al archivo CSV
        output_file (str, optional): Archivo de salida. Si no se especifica, usa el nombre por defecto
    
    Returns:
        pd.DataFrame: DataFrame con los top 100 papers
    """
    
    try:
        # Leer el archivo CSV
        print(f" Leyendo archivo: {csv_file_path}")
        df = pd.read_csv(csv_file_path)
        
        print(f" Total de papers en el dataset: {len(df):,}")
        print(f" Rango de citas: {df['citations'].min():,} - {df['citations'].max():,}")
        
        # Ordenar por citas (descendente) y tomar los top 100
        top_100 = df.nlargest(100, 'citations')
        
        # Mostrar estadísticas
        print(f"\n TOP 100 PAPERS POR CITAS:")
        print(f"   • Papers con 0 citas: {(df['citations'] == 0).sum():,}")
        print(f"   • Papers con 1+ citas: {(df['citations'] > 0).sum():,}")
        print(f"   • Papers con 10+ citas: {(df['citations'] >= 10).sum():,}")
        print(f"   • Papers con 100+ citas: {(df['citations'] >= 100).sum():,}")
        print(f"   • Papers con 1000+ citas: {(df['citations'] >= 1000).sum():,}")
        
        # Estadísticas del top 100
        print(f"\n ESTADÍSTICAS TOP 100:")
        print(f"   • Citas mínimas en top 100: {top_100['citations'].min():,}")
        print(f"   • Citas máximas en top 100: {top_100['citations'].max():,}")
        print(f"   • Promedio de citas top 100: {top_100['citations'].mean():.1f}")
        print(f"   • Mediana de citas top 100: {top_100['citations'].median():.1f}")
        
        # Mostrar los top 10
        print(f"\nTOP 10 PAPERS:")
        for i, (_, paper) in enumerate(top_100.head(10).iterrows(), 1):
            print(f"   {i:2d}. [{paper['citations']:4,} citas] {paper['title'][:80]}...")
            if paper['venue'] and str(paper['venue']) != 'nan':
                print(f"        {paper['venue']}")
            if paper['year'] and str(paper['year']) != 'nan':
                print(f"       {int(paper['year'])}")
            print()
        
        # Guardar archivo de salida
        if output_file is None:
            output_file = "top_100_citations_semantic_scholar.csv"
        
        top_100.to_csv(output_file, index=False)
        print(f" Top 100 papers guardados en: {output_file}")
        
        # Crear archivo de resumen
        summary_file = output_file.replace('.csv', '_summary.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("TOP 100 PAPERS POR CITAS - SEMANTIC SCHOLAR\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total papers en dataset: {len(df):,}\n")
            f.write(f"Rango de citas: {df['citations'].min():,} - {df['citations'].max():,}\n")
            f.write(f"Papers con 0 citas: {(df['citations'] == 0).sum():,}\n")
            f.write(f"Papers con 1+ citas: {(df['citations'] > 0).sum():,}\n")
            f.write(f"Papers con 10+ citas: {(df['citations'] >= 10).sum():,}\n")
            f.write(f"Papers con 100+ citas: {(df['citations'] >= 100).sum():,}\n")
            f.write(f"Papers con 1000+ citas: {(df['citations'] >= 1000).sum():,}\n\n")
            
            f.write("ESTADÍSTICAS TOP 100:\n")
            f.write(f"Citas mínimas: {top_100['citations'].min():,}\n")
            f.write(f"Citas máximas: {top_100['citations'].max():,}\n")
            f.write(f"Promedio: {top_100['citations'].mean():.1f}\n")
            f.write(f"Mediana: {top_100['citations'].median():.1f}\n\n")
            
            f.write("TOP 10 PAPERS:\n")
            for i, (_, paper) in enumerate(top_100.head(10).iterrows(), 1):
                f.write(f"{i:2d}. [{paper['citations']:4,} citas] {paper['title']}\n")
                if paper['venue'] and str(paper['venue']) != 'nan':
                    f.write(f"     {paper['venue']}\n")
                if paper['year'] and str(paper['year']) != 'nan':
                    f.write(f"     {int(paper['year'])}\n")
                f.write("\n")
        
        print(f" Resumen guardado en: {summary_file}")
        
        return top_100
        
    except FileNotFoundError:
        print(f" Error: No se encontró el archivo {csv_file_path}")
        return None
    except Exception as e:
        print(f" Error procesando el archivo: {e}")
        return None

def main():
    """Función principal"""
    
    # Ruta por defecto al archivo CSV
    default_csv = "ai_safety_papers_ultra_optimized.csv"
    
    # Verificar si el archivo existe
    if not Path(default_csv).exists():
        print(f" No se encontró el archivo {default_csv}")
        print(" Asegúrate de ejecutar el script desde el directorio SemanticScholar/")
        print(" O proporciona la ruta completa al archivo CSV")
        sys.exit(1)
    
    # Procesar el archivo
    print("Extrayendo top 100 papers por citas...")
    top_100 = get_top_100_citations(default_csv)
    
    if top_100 is not None:
        print("\nProceso completado exitosamente!")
        print(f" Archivos generados:")
        print(f"   • top_100_citations_semantic_scholar.csv")
        print(f"   • top_100_citations_semantic_scholar_summary.txt")
    else:
        print("\n Error en el proceso")
        sys.exit(1)

if __name__ == "__main__":
    main()
