#!/usr/bin/env python3
"""
Generador de rankings de top papers por citas
Extrae los papers mas citados de la base de datos PostgreSQL
"""

import psycopg2
import pandas as pd
import argparse
from contextlib import contextmanager

@contextmanager
def get_db_connection(host="localhost", port=6543, database="ai_safety", 
                     user="scholar_user", password="scholar_pass_2024"):
    """Context manager para conexiones a la base de datos"""
    conn = None
    try:
        conn = psycopg2.connect(
            host=host, port=port, database=database, 
            user=user, password=password
        )
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error de conexion a DB: {e}")
        raise
    finally:
        if conn:
            conn.close()

def generate_top_papers_ranking(limit=100, output_file="top_papers_by_citations.csv"):
    """Generar ranking de top papers por citas"""
    
    with get_db_connection() as conn:
        # Query para obtener top papers por citas
        query = """
        SELECT 
            paper_id,
            title,
            authors,
            year,
            venue,
            citations,
            url,
            pdf_url,
            keywords,
            created_at
        FROM papers 
        WHERE citations IS NOT NULL AND citations > 0
        ORDER BY citations DESC, year DESC
        LIMIT %s;
        """
        
        df = pd.read_sql_query(query, conn, params=[limit])
        
        if df.empty:
            print("No se encontraron papers con citas")
            return None
        
        # Agregar ranking
        df['ranking'] = range(1, len(df) + 1)
        
        # Reordenar columnas
        columns_order = ['ranking', 'title', 'authors', 'year', 'venue', 'citations', 'url', 'pdf_url', 'keywords', 'created_at', 'paper_id']
        df = df[columns_order]
        
        # Guardar CSV
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"Ranking generado: {output_file}")
        print(f"Total papers: {len(df)}")
        print(f"Top 5 papers:")
        for i, row in df.head().iterrows():
            print(f"  {row['ranking']}. {row['title'][:80]}... ({row['citations']} citas)")
        
        return df

def generate_top_papers_by_year(limit=50, output_file="top_papers_by_year.csv"):
    """Generar ranking de top papers por ano"""
    
    with get_db_connection() as conn:
        # Query para obtener top papers por ano
        query = """
        WITH ranked_papers AS (
            SELECT 
                paper_id,
                title,
                authors,
                year,
                venue,
                citations,
                url,
                pdf_url,
                keywords,
                ROW_NUMBER() OVER (PARTITION BY year ORDER BY citations DESC) as year_rank
            FROM papers 
            WHERE citations IS NOT NULL AND citations > 0 AND year IS NOT NULL
        )
        SELECT 
            year,
            year_rank as ranking,
            title,
            authors,
            venue,
            citations,
            url,
            pdf_url,
            keywords
        FROM ranked_papers 
        WHERE year_rank <= %s
        ORDER BY year DESC, citations DESC;
        """
        
        df = pd.read_sql_query(query, conn, params=[limit])
        
        if df.empty:
            print("No se encontraron papers por ano")
            return None
        
        # Guardar CSV
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"Ranking por ano generado: {output_file}")
        print(f"Total papers: {len(df)}")
        print(f"Anos cubiertos: {sorted(df['year'].unique(), reverse=True)}")
        
        return df

def generate_top_papers_by_venue(limit=20, output_file="top_papers_by_venue.csv"):
    """Generar ranking de top papers por venue"""
    
    with get_db_connection() as conn:
        # Query para obtener top papers por venue
        query = """
        WITH ranked_papers AS (
            SELECT 
                paper_id,
                title,
                authors,
                year,
                venue,
                citations,
                url,
                pdf_url,
                keywords,
                ROW_NUMBER() OVER (PARTITION BY venue ORDER BY citations DESC) as venue_rank
            FROM papers 
            WHERE citations IS NOT NULL AND citations > 0 AND venue IS NOT NULL AND venue != ''
        )
        SELECT 
            venue,
            venue_rank as ranking,
            title,
            authors,
            year,
            citations,
            url,
            pdf_url,
            keywords
        FROM ranked_papers 
        WHERE venue_rank <= %s
        ORDER BY venue, citations DESC;
        """
        
        df = pd.read_sql_query(query, conn, params=[limit])
        
        if df.empty:
            print("No se encontraron papers por venue")
            return None
        
        # Guardar CSV
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"Ranking por venue generado: {output_file}")
        print(f"Total papers: {len(df)}")
        print(f"Venues unicos: {df['venue'].nunique()}")
        
        return df

def generate_statistics():
    """Generar estadisticas generales"""
    
    with get_db_connection() as conn:
        # Estadisticas generales
        stats_query = """
        SELECT 
            COUNT(*) as total_papers,
            COUNT(CASE WHEN citations > 0 THEN 1 END) as papers_with_citations,
            AVG(citations) as avg_citations,
            MAX(citations) as max_citations,
            MIN(year) as min_year,
            MAX(year) as max_year,
            COUNT(DISTINCT venue) as unique_venues,
            COUNT(DISTINCT year) as unique_years
        FROM papers;
        """
        
        stats_df = pd.read_sql_query(stats_query, conn)
        stats = stats_df.iloc[0]
        
        print("\nESTADISTICAS GENERALES:")
        print(f"  Total papers: {stats['total_papers']:,}")
        print(f"  Papers con citas: {stats['papers_with_citations']:,}")
        print(f"  Citas promedio: {stats['avg_citations']:.1f}")
        print(f"  Maximo de citas: {stats['max_citations']:,}")
        print(f"  Rango de anos: {stats['min_year']}-{stats['max_year']}")
        print(f"  Venues unicos: {stats['unique_venues']:,}")
        print(f"  Anos unicos: {stats['unique_years']}")
        
        return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generar rankings de top papers por citas")
    parser.add_argument("--limit", type=int, default=100, help="Numero de papers en el ranking")
    parser.add_argument("--type", choices=["all", "year", "venue", "stats"], default="all", 
                       help="Tipo de ranking a generar")
    parser.add_argument("--output", default="top_papers_by_citations.csv", help="Archivo de salida")
    
    # DB connection args
    parser.add_argument("--db-host", default="localhost", help="Host de PostgreSQL")
    parser.add_argument("--db-port", type=int, default=6543, help="Puerto de PostgreSQL")
    parser.add_argument("--db-name", default="ai_safety", help="Nombre de la base de datos")
    parser.add_argument("--db-user", default="scholar_user", help="Usuario de la base de datos")
    parser.add_argument("--db-password", default="scholar_pass_2024", help="Password de la base de datos")
    
    args = parser.parse_args()
    
    print("GENERADOR DE RANKINGS DE TOP PAPERS")
    print("=" * 50)
    
    if args.type == "all":
        generate_top_papers_ranking(args.limit, args.output)
        generate_top_papers_by_year(50, "top_papers_by_year.csv")
        generate_top_papers_by_venue(20, "top_papers_by_venue.csv")
        generate_statistics()
    elif args.type == "year":
        generate_top_papers_by_year(args.limit, args.output)
    elif args.type == "venue":
        generate_top_papers_by_venue(args.limit, args.output)
    elif args.type == "stats":
        generate_statistics()
    
    print("\nProceso completado!")
