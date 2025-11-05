"""
AWS Lambda Handler for Semantic Scholar Paper Extraction

Este handler es invocado por:
- EventBridge (trigger mensual automático)
- Manual invocation desde AWS Console
- Glue workflow (future)

Input Event:
{
    "extraction_date": "2024-11-01",  # YYYY-MM-DD o "auto"
    "year_from": 2005,
    "papers_per_query": 10000,
    "min_citations": 0,
    "include_secondary": true
}

Output:
{
    "statusCode": 200,
    "body": {
        "extraction_date": "2024-11-01",
        "total_areas": 15,
        "total_papers": 50000,
        "s3_prefix": "raw_data/snapshots/extraction_date=2024-11-01/"
    }
}
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Local imports
from src.extractor import SemanticScholarExtractor
from src.s3_writer import S3ParquetWriter
from src.secrets import get_secret_value
from src.utils import download_file_from_s3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function

    Args:
        event: Event dict with extraction parameters
        context: Lambda context object

    Returns:
        Response dict with extraction results
    """
    try:
        logger.info(f"Lambda invoked with event: {json.dumps(event)}")

        # 1. Parse event parameters
        extraction_date = event.get('extraction_date', 'auto')
        if extraction_date == 'auto':
            extraction_date = datetime.now().strftime('%Y-%m-01')

        year_from = event.get('year_from', 2005)
        papers_per_query = event.get('papers_per_query', 10000)
        min_citations = event.get('min_citations', 0)
        include_secondary = event.get('include_secondary', True)
        max_workers = event.get('max_workers', 10)

        logger.info(f"Extraction parameters:")
        logger.info(f"  extraction_date: {extraction_date}")
        logger.info(f"  year_from: {year_from}")
        logger.info(f"  papers_per_query: {papers_per_query}")
        logger.info(f"  min_citations: {min_citations}")
        logger.info(f"  include_secondary: {include_secondary}")
        logger.info(f"  max_workers: {max_workers}")

        # 2. Get configuration from environment
        secret_arn = os.environ['SECRET_ARN']
        s3_bucket = os.environ['S3_BUCKET']
        s3_prefix = os.environ.get('S3_PREFIX', 'raw_data/snapshots/')
        terms_json_s3_key = os.environ.get('TERMS_JSON_S3_KEY', 'config/terms.json')

        # 3. Get API key from Secrets Manager
        logger.info(f"Fetching API key from Secrets Manager: {secret_arn}")
        api_key = get_secret_value(secret_arn)

        # 4. Download terms.json from S3
        logger.info(f"Downloading terms.json from s3://{s3_bucket}/{terms_json_s3_key}")
        terms_json_path = '/tmp/terms.json'
        download_file_from_s3(s3_bucket, terms_json_s3_key, terms_json_path)

        # 5. Run extraction (async)
        logger.info("Starting extraction...")
        results = asyncio.run(run_extraction(
            api_key=api_key,
            terms_json_path=terms_json_path,
            year_from=year_from,
            papers_per_query=papers_per_query,
            min_citations=min_citations,
            include_secondary=include_secondary,
            max_workers=max_workers
        ))

        # 6. Upload results to S3 as Parquet
        logger.info(f"Uploading results to S3...")
        s3_writer = S3ParquetWriter(s3_bucket, s3_prefix, extraction_date)

        total_papers = 0
        for area_name, papers in results.items():
            s3_key = s3_writer.upload_area_papers(area_name, papers)
            logger.info(f"Uploaded {len(papers)} papers for {area_name} to {s3_key}")
            total_papers += len(papers)

        # 7. Return success response
        response = {
            'statusCode': 200,
            'body': {
                'extraction_date': extraction_date,
                'total_areas': len(results),
                'total_papers': total_papers,
                's3_prefix': f"{s3_prefix}extraction_date={extraction_date}/",
                'timestamp': datetime.now().isoformat()
            }
        }

        logger.info(f"Extraction completed successfully: {json.dumps(response['body'])}")
        return response

    except Exception as e:
        logger.error(f"Error in lambda handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        }


async def run_extraction(
    api_key: str,
    terms_json_path: str,
    year_from: int,
    papers_per_query: int,
    min_citations: int,
    include_secondary: bool,
    max_workers: int
) -> Dict[str, list]:
    """
    Run the async extraction process

    Returns:
        Dict mapping area_name -> list of papers
    """
    extractor = SemanticScholarExtractor(
        api_key=api_key,
        max_workers=max_workers
    )

    results = await extractor.extract_all_areas(
        terms_json_path=terms_json_path,
        year_from=year_from,
        papers_per_query=papers_per_query,
        min_citations=min_citations,
        include_secondary=include_secondary
    )

    return results
