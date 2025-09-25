import logging
from server import mcp
from utils.s3_csv_processor import read_s3_csv_chunk, get_basic_info, format_basic_report

logger = logging.getLogger(__name__)


@mcp.tool()
def analyze_s3_csv(bucket_name: str, file_key: str) -> str:
    """
    Get basic information from a CSV file stored in AWS S3.

    Args:
        bucket_name: Name of the S3 bucket containing the CSV file
        file_key: S3 object key (path) to the CSV file

    Returns:
        Basic info: count, columns, and sample 50 records.
    """
    logger.info(f"Getting basic info from S3 CSV: s3://{bucket_name}/{file_key}")

    try:
        df_chunk = read_s3_csv_chunk(bucket_name, file_key, chunk_size=1000)
        info = get_basic_info(df_chunk)
        sample_data = df_chunk.head(50).to_dict("records")
        
        file_path = f"s3://{bucket_name}/{file_key}"
        report = format_basic_report(file_path, info, sample_data)
        
        logger.info(f"Successfully processed S3 CSV chunk: {info['total_rows']} rows, {info['total_columns']} columns")
        return report

    except Exception as e:
        logger.exception("Failed to process S3 CSV")
        return f"❌ Error processing S3 CSV s3://{bucket_name}/{file_key}: {e}"
