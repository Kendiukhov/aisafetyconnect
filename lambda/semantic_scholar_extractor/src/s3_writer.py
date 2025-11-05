"""
S3 Parquet Writer - Upload papers to S3 in Parquet format
"""

import io
import logging
from typing import List, Dict
import pandas as pd
import boto3

logger = logging.getLogger(__name__)


class S3ParquetWriter:
    """
    Write papers to S3 in Parquet format

    S3 Structure:
        s3://bucket/prefix/extraction_date=YYYY-MM-DD/area=AREA_NAME/papers.parquet
    """

    def __init__(self, bucket: str, prefix: str, extraction_date: str):
        """
        Args:
            bucket: S3 bucket name (e.g., "aisafetyconnect-raw-dev")
            prefix: S3 prefix (e.g., "raw_data/snapshots/")
            extraction_date: Date string (e.g., "2024-11-01")
        """
        self.bucket = bucket
        self.prefix = prefix.rstrip('/') + '/'
        self.extraction_date = extraction_date
        self.s3_client = boto3.client('s3')

    def upload_area_papers(self, area_name: str, papers: List[Dict]) -> str:
        """
        Upload papers for one area to S3 as Parquet

        Args:
            area_name: Area name (e.g., "AI_Safety")
            papers: List of paper dicts

        Returns:
            S3 key where file was uploaded
        """
        if not papers:
            logger.warning(f"No papers to upload for area {area_name}")
            return None

        # Convert to DataFrame
        df = pd.DataFrame(papers)

        # Add extraction metadata
        df['_extraction_date'] = self.extraction_date
        df['_area'] = area_name

        # Build S3 key
        s3_key = f"{self.prefix}extraction_date={self.extraction_date}/area={area_name}/papers.parquet"

        # Convert to Parquet in memory
        parquet_buffer = io.BytesIO()
        df.to_parquet(
            parquet_buffer,
            engine='pyarrow',
            compression='snappy',
            index=False
        )

        # Upload to S3
        parquet_buffer.seek(0)
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=parquet_buffer.getvalue(),
            ContentType='application/octet-stream'
        )

        logger.info(f"Uploaded {len(papers)} papers to s3://{self.bucket}/{s3_key}")
        return s3_key
