import logging
from server import mcp
from utils.file_reader import read_csv_summary

logger = logging.getLogger(__name__)


@mcp.tool()
def summarize_csv_file(filename: str) -> str:
    """
    Summarize a CSV file by reporting its number of rows and columns.
    Args:
        filename: Name of the CSV file in the /data directory (e.g., 'sample.csv')
    Returns:
        A string describing the file's dimensions.
    """
    logger.info(f"Processing CSV file: {filename}")
    try:
        result = read_csv_summary(filename)
        logger.info(f"Successfully processed CSV file: {filename}")
        return result
    except Exception as e:
        logger.error(f"Error processing CSV file {filename}: {e}")
        raise