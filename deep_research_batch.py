"""
Batch processor for deep research username searches.

This script processes multiple LessWrong users from a JSON file and performs
deep research to identify their real names using OpenAI's o4-mini-deep-research model.

Features:
- Rate limiting to respect 200k TPM limit (15s spacing between searches)
- Incremental saving for crash recovery
- Resume support for interrupted batches
- Comprehensive error handling (4 scenarios)
- JSON output with lowercase keys

Usage:
    python deep_research_batch.py --input raw-data/lesswrong/2025-09-27/users_top20.json
    python deep_research_batch.py --input users.json --output-dir custom/path
"""

import json
import logging
import time
import argparse
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from username_searcher import UsernameSearch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deep_research_batch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_users(input_path: Path) -> List[Dict]:
    """
    Load users from JSON file.

    Args:
        input_path: Path to JSON file containing user data

    Returns:
        List of user dicts with keys: _id, username, displayName, bio, etc.

    Raises:
        FileNotFoundError: If input file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    logger.info(f"Loading users from {input_path}")

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        users = json.load(f)

    logger.info(f"Loaded {len(users)} users")
    return users


def get_output_path(output_dir: Path) -> Path:
    """
    Generate output path with today's date.

    Args:
        output_dir: Base output directory

    Returns:
        Path to output JSON file (e.g., results/username_searches/2025-01-15/search_results.json)
    """
    today = datetime.now().strftime('%Y-%m-%d')
    output_path = output_dir / today / 'search_results.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Output will be saved to: {output_path}")
    return output_path


def load_existing_results(output_path: Path) -> Dict:
    """
    Load existing results file if it exists (for resuming).

    Args:
        output_path: Path to results JSON file

    Returns:
        Dict with structure:
        {
            "timestamp_start": "ISO format",
            "timestamp_last_update": "ISO format",
            "total_users": int,
            "successful_searches": int,
            "failed_searches": int,
            "results": [...]
        }
    """
    if output_path.exists():
        logger.info(f"Found existing results file, loading for resume: {output_path}")
        with open(output_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    logger.info("No existing results file, starting fresh")
    return {
        "timestamp_start": datetime.now().isoformat(),
        "timestamp_last_update": datetime.now().isoformat(),
        "total_users": 0,
        "successful_searches": 0,
        "failed_searches": 0,
        "results": []
    }


def get_processed_user_ids(results_data: Dict) -> set:
    """
    Extract set of already processed user IDs from results.

    FIX APPLIED: Filters out 'unknown' user_ids to prevent false positives.

    Args:
        results_data: Results dict from load_existing_results()

    Returns:
        Set of user_id strings that have been processed
    """
    processed = set()
    for result in results_data["results"]:
        user_id = result.get("user_id")
        # Only add valid IDs (not 'unknown')
        if user_id and user_id != "unknown":
            processed.add(user_id)

    logger.info(f"Found {len(processed)} already processed users")
    return processed


def save_results(output_path: Path, results_data: Dict):
    """
    Save results to JSON file with atomic write.

    Args:
        output_path: Path to output JSON file
        results_data: Results dict to save
    """
    # Update timestamp
    results_data["timestamp_last_update"] = datetime.now().isoformat()

    # Write to temporary file first (atomic operation)
    temp_path = output_path.with_suffix('.json.tmp')
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)

    # Rename (atomic on most filesystems)
    temp_path.rename(output_path)

    logger.info(f"Saved results: {results_data['successful_searches']} successful, {results_data['failed_searches']} failed")


def process_single_user(searcher: UsernameSearch, user: Dict) -> Dict:
    """
    Process a single user with comprehensive error handling.

    This function handles all 4 error scenarios:
    1. failed_to_start: Exception during start_user_search_with_rate_limit()
    2. failed_during_processing: API returns status='failed'
    3. timeout: wait_for_completion() times out
    4. unparseable: validate_json_result() raises exception

    Args:
        searcher: UsernameSearch instance
        user: User dict with _id, username, displayName, bio

    Returns:
        Dict with structure:
        {
            "user_id": str,
            "username": str,
            "search_status": "completed" | "failed_to_start" | "failed_during_processing" | "timeout" | "unparseable",
            "timestamp": ISO format,
            "result": {
                "real_name": str,
                "confidence": str,
                "evidence": str,
                "academic_suitability": str
            } or None if failed,
            "error_message": str (only if failed)
        }
    """
    user_id = user.get('_id', 'unknown')
    username = user.get('username', 'unknown')

    result_entry = {
        "user_id": user_id,
        "username": username,
        "search_status": "unknown",
        "timestamp": datetime.now().isoformat(),
        "result": None,
        "error_message": None
    }

    logger.info(f"Processing user: {username} (ID: {user_id})")

    # SCENARIO 1: Try to start search
    try:
        searcher.start_user_search_with_rate_limit(user)
    except Exception as e:
        logger.error(f"Failed to start search for {username}: {e}", exc_info=True)
        result_entry["search_status"] = "failed_to_start"
        result_entry["error_message"] = str(e)
        return result_entry

    # SCENARIO 2 & 3: Wait for completion (handles both timeout and API failure)
    try:
        completed = searcher.wait_for_completion(timeout_seconds=600, poll_interval=10)

        if not completed:
            # Check if it failed or timed out
            if searcher.last_search_status == 'failed':
                logger.error(f"Search failed during processing for {username}")
                result_entry["search_status"] = "failed_during_processing"
                result_entry["error_message"] = "API returned status='failed'"
            else:
                logger.error(f"Search timed out for {username}")
                result_entry["search_status"] = "timeout"
                result_entry["error_message"] = "Search did not complete within 600 seconds"
            return result_entry
    except Exception as e:
        logger.error(f"Unexpected error waiting for {username}: {e}", exc_info=True)
        result_entry["search_status"] = "failed_during_processing"
        result_entry["error_message"] = str(e)
        return result_entry

    # SCENARIO 4: Try to parse JSON result
    try:
        raw_output = searcher.last_search_response
        parsed_result = searcher.validate_json_result(raw_output)

        result_entry["search_status"] = "completed"
        result_entry["result"] = parsed_result

        logger.info(f"Successfully processed {username}: {parsed_result['real_name']}")
        return result_entry

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse JSON for {username}: {e}", exc_info=True)
        result_entry["search_status"] = "unparseable"
        result_entry["error_message"] = f"JSON parsing failed: {str(e)}"
        result_entry["raw_output"] = raw_output[:500] if raw_output else None  # Save first 500 chars for debugging
        return result_entry
    except Exception as e:
        logger.error(f"Unexpected error parsing result for {username}: {e}", exc_info=True)
        result_entry["search_status"] = "unparseable"
        result_entry["error_message"] = str(e)
        return result_entry


def process_batch(input_path: Path, output_dir: Path, limit: int = None):
    """
    Main batch processing function.

    Args:
        input_path: Path to input JSON file with users
        output_dir: Base directory for output (date subfolder will be created)
        limit: Optional maximum number of users to process (useful for testing)
    """
    logger.info("="*80)
    logger.info("Starting deep research batch processing")
    logger.info("="*80)

    # Load users
    users = load_users(input_path)

    # Setup output
    output_path = get_output_path(output_dir)
    results_data = load_existing_results(output_path)

    # Get already processed user IDs (for resuming)
    processed_ids = get_processed_user_ids(results_data)

    # Update total users count
    results_data["total_users"] = len(users)

    # Initialize searcher
    logger.info("Initializing UsernameSearch with 360s timeout")
    searcher = UsernameSearch(openai_timeout=360)

    # Process each user
    users_to_process = [u for u in users if u.get('_id') not in processed_ids]

    # Apply limit if specified
    if limit is not None and limit > 0:
        users_to_process = users_to_process[:limit]
        logger.info(f"Limit applied: processing only first {limit} users")

    logger.info(f"Processing {len(users_to_process)} users (skipping {len(processed_ids)} already processed)")

    for i, user in enumerate(users_to_process, start=1):
        logger.info(f"\n{'='*80}")
        logger.info(f"User {i}/{len(users_to_process)}")
        logger.info(f"{'='*80}")

        # Process user
        result_entry = process_single_user(searcher, user)

        # Add to results
        results_data["results"].append(result_entry)

        # FIX APPLIED: Recalculate counters from scratch instead of incrementing
        # This prevents duplication when resuming
        results_data["successful_searches"] = sum(
            1 for r in results_data["results"] if r["search_status"] == "completed"
        )
        results_data["failed_searches"] = len(results_data["results"]) - results_data["successful_searches"]

        # Save after each user (incremental saving for crash recovery)
        save_results(output_path, results_data)

        logger.info(f"Progress: {i}/{len(users_to_process)} users processed")

    # Final summary
    logger.info("\n" + "="*80)
    logger.info("BATCH PROCESSING COMPLETE")
    logger.info("="*80)
    logger.info(f"Total users: {results_data['total_users']}")
    logger.info(f"Successful searches: {results_data['successful_searches']}")
    logger.info(f"Failed searches: {results_data['failed_searches']}")
    logger.info(f"Results saved to: {output_path}")
    logger.info("="*80)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Batch process LessWrong users for deep research username searches',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input raw-data/lesswrong/2025-09-27/users_top20.json --limit 3
  %(prog)s --input raw-data/lesswrong/2025-09-27/users_top20.json
  %(prog)s --input users.json --output-dir custom/path
        """
    )

    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Path to input JSON file containing user data'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('results/username_searches'),
        help='Base directory for output (default: results/username_searches)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of users to process (useful for testing, e.g., --limit 3)'
    )

    args = parser.parse_args()

    try:
        process_batch(args.input, args.output_dir, limit=args.limit)
    except KeyboardInterrupt:
        logger.warning("\n\nInterrupted by user (Ctrl+C)")
        logger.info("Progress has been saved. You can resume by running the same command again.")
        return 1
    except Exception as e:
        logger.error(f"\n\nFATAL ERROR: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
