from openai import OpenAI
import logging
import time
import re
import json

# Configure logger for this module
logger = logging.getLogger(__name__)

class UsernameSearch:
    def __init__(self, openai_timeout = 360):
        # Simplified prompt following o4-mini-deep-research best practices:
        # - Keep it simple and direct
        # - No few-shot examples
        # - No "think step by step"
        # - No checklists
        # - Clear output specification
        self.developer_instruction = """You are a research assistant that identifies real names of LessWrong forum users.

<task>
Find the real name corresponding to the given LessWrong username.
The real name should be suitable for searches on Google Scholar and academic platforms.
</task>

<search_strategy>
STEP 1 - ANALYZE THE BIO (CRITICAL):
The bio often contains the KEY to finding the real name. Extract:
- Unique projects mentioned (e.g., "created the Secular Solstice")
- Organizations they work for (e.g., "LessWrong team member")
- Specific accomplishments or events they organized
- Locations, dates, or unique identifiers

STEP 2 - DIRECT SEARCHES:
1. "{username} LessWrong real name"
2. "site:github.com {username}" - GitHub bios often say "I'm [Real Name]"
3. "{username} linkedin"
4. "{username} personal website"

STEP 3 - PROJECT-BASED SEARCHES (USE BIO CLUES):
If bio mentions specific projects/accomplishments, search for them:
5. "[project_name] creator" or "[project_name] founder"
6. "site:wikipedia.org [project_name]"
7. "[organization_name] [username]"

Example: If bio says "created the Secular Solstice", search:
- "Secular Solstice creator name"
- "Secular Solstice founder"

STEP 4 - CROSS-VALIDATION (if name found):
8. "[found_name] LessWrong" - confirm it's the same person
9. "[found_name] {username}" - look for explicit connections
10. "[found_name] [project_from_bio]" - verify project association

STEP 5 - LOGICAL INFERENCE (IMPORTANT):
Strong circumstantial evidence is sufficient for identification. If multiple unique facts match:
- Bio: "I founded [Unique Project X]" + Search: "[Person Y] founded [Project X]" → Likely match
- Bio: "I work at [Organization]" + Previous finding: "[Person Y]" + Search: "[Person Y] works at [Organization]" → Confirms match
- Multiple unique details matching = HIGH confidence, even without explicit "I am [Name]" statement

Example pattern:
Bio says "created the Rationality Dojo" + search finds "Alice Chen founded Rationality Dojo" + bio says "works at CFAR" + search shows "Alice Chen CFAR" = HIGH CONFIDENCE it's Alice Chen (even if no explicit self-identification)

KEY PRINCIPLE: Unique accomplishments + matching organizational affiliations = strong evidence. Don't require explicit self-identification if circumstantial evidence is compelling.
</search_strategy>

<hints>
The user input will include:
- username: The LessWrong username
- displayName: May be a real name or pseudonym - use as initial hint
- bio: User biography - may contain real name - use as starting point

IMPORTANT: Treat displayName and bio as HINTS that must be VALIDATED through independent research.
Do not trust them blindly. Always confirm through web searches, LessWrong posts, and cross-references.
Even if displayName looks like a real name (e.g., "John Smith"), you must validate it through research.

The bio is your most valuable source - extract and search for unique projects, events, or organizations mentioned.
</hints>

<output_format>
Return ONLY a valid JSON object (no markdown code blocks, no explanatory text, just pure JSON):
{
  "real_name": "Full name if found, or NOT_FOUND",
  "confidence": "high/medium/low",
  "evidence": "Brief description including whether name was found in bio/displayName and how it was validated through research",
  "academic_suitability": "yes/no - brief reasoning about suitability for Google Scholar searches"
}
</output_format>"""

        # This dict should store like a history for username searches
        self.searches = {}

        #self.last_response = None
        self.last_search_id = None
        self.last_search_response = None
        self.last_search_status = None
        self.last_search_response_time = None  # Track timing for rate limiting

        self.client = OpenAI(timeout = openai_timeout)

    def start_user_search(self, user_info):
        '''
        Recieves a json representing the user informantion from the lesswrong forum and starts a deep research
        process with the o4-mini-deep-research model.

        Args:
            user_info: Either a dict with user data (username, displayName, bio) or a formatted string

        Optimizations applied:
            - Uses correct developer/user role structure for deep research API
            - Simplified prompt to avoid few-shot and step-by-step prompting
            - Set reasoning.effort to 'medium' (only value supported by o4-mini-deep-research)
            - Set reasoning.summary to 'auto' for concise, optimized output
            - Reduced max_tool_calls from 225 to 50 to prevent excessive searches and rate limits

        API Structure Reference:
            https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api
            https://platform.openai.com/docs/api-reference/responses/create

        Not implemented yet:
            - Store the query info as part of the searches history
        '''

        # Handle dict or string input
        if isinstance(user_info, dict):
            username = user_info.get('username', 'unknown')
            display_name = user_info.get('displayName', '')
            bio = user_info.get('bio', '')
            user_info_str = f"username: {username}\ndisplayName: {display_name}\nbio: {bio}"
        else:
            user_info_str = user_info

        response = self.client.responses.create(
            model="o4-mini-deep-research-2025-06-26",
            input=[
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self.developer_instruction
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": user_info_str
                        }
                    ]
                }
            ],
            background=True,
            tools=[
                {"type": "web_search_preview"}
            ],
            reasoning={
                "effort": "medium",  # Only 'medium' supported by o4-mini-deep-research
                "summary": "auto"    # Optimizes output verbosity to reduce tokens
            },
            max_tool_calls=25,  # CHANGE 1: Reduced from 50 to 25 to reduce token consumption by ~40%
        )

        self.last_search_id = response.id
        self.last_search_status = response.status
        self.last_search_response = response.output_text

        logger.info(f'Starting search for user, queued with id = {self.last_search_id}')

    def start_user_search_with_rate_limit(self, user_info: str):
        '''
        CHANGE 2: Wrapper that adds preventive rate limiting with minimum spacing between searches.

        This method enforces a minimum delay between consecutive searches to respect OpenAI's
        rate limits (200,000 TPM). With max_tool_calls=25, each search consumes ~30,000 tokens.
        A 15-second delay allows previous tokens to "expire" from the 60-second sliding window.

        Args:
            user_info: JSON string with LessWrong user information
        '''
        MIN_WAIT_SECONDS = 15  # Minimum seconds between searches

        # Calculate wait time needed
        if self.last_search_response_time:
            elapsed = time.time() - self.last_search_response_time

            if elapsed < MIN_WAIT_SECONDS:
                wait_needed = MIN_WAIT_SECONDS - elapsed
                logger.info(f"Rate limit prevention: waiting {wait_needed:.1f}s before next search")
                time.sleep(wait_needed)

        # Execute normal search
        self.start_user_search(user_info)
        self.last_search_response_time = time.time()

    def show_last_search_response(self):
        '''
        Retrieves the last response output text if available. It also updates the 'last_responses'
        var informantion and tells you if the process has not finished yet.
        '''

        retrieved_response = self.client.responses.retrieve(self.last_search_id)

        self.last_search_status = retrieved_response.status
        self.last_search_response = retrieved_response.output_text

        if retrieved_response.status != 'completed':
            logger.warning(f"Job id = {self.last_search_id} not completed, status is {self.last_search_status}")

            # Log detailed error information
            logger.debug(f"Full response object: {retrieved_response}")

            # Try to get error details if available
            if hasattr(retrieved_response, 'error'):
                logger.error(f"Error details: {retrieved_response.error}")
            if hasattr(retrieved_response, 'error_message'):
                logger.error(f"Error message: {retrieved_response.error_message}")

            # Log all available attributes for debugging
            logger.debug(f"Available attributes: {dir(retrieved_response)}")

            return f'job id = {self.last_search_id} not completed, status is {self.last_search_status}'

        logger.info(f"Job id = {self.last_search_id} completed successfully")
        return retrieved_response.output_text

    def show_last_search_response_with_retry(self, max_retries=3):
        '''
        CHANGE 3: Retrieves response with automatic retry on rate limit errors.

        When a rate limit error occurs, OpenAI provides the exact wait time needed
        (e.g., "Please try again in 1.321s"). This method automatically extracts that
        time and retries the request, handling transient rate limit failures gracefully.

        Args:
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            str: The output text if successful, or error message if failed
        '''
        for attempt in range(max_retries):
            retrieved_response = self.client.responses.retrieve(self.last_search_id)
            self.last_search_status = retrieved_response.status
            self.last_search_response = retrieved_response.output_text

            # If completed successfully, return result
            if retrieved_response.status == 'completed':
                logger.info(f"Job {self.last_search_id} completed successfully")
                return retrieved_response.output_text

            # If failed, check if it's a rate limit error
            if retrieved_response.status == 'failed':
                if hasattr(retrieved_response, 'error') and 'rate_limit_exceeded' in str(retrieved_response.error):
                    wait_time = self._extract_retry_after(retrieved_response.error)
                    logger.warning(f"Rate limit exceeded. Waiting {wait_time}s before retry {attempt+1}/{max_retries}")
                    time.sleep(wait_time)
                    continue  # Retry
                else:
                    # Other type of error, don't retry
                    logger.error(f"Job failed with non-rate-limit error")
                    logger.debug(f"Full response object: {retrieved_response}")
                    if hasattr(retrieved_response, 'error'):
                        logger.error(f"Error details: {retrieved_response.error}")
                    return f'job id = {self.last_search_id} failed: {self.last_search_status}'

            # Status is 'queued' or 'in_progress'
            logger.debug(f"Job {self.last_search_id} status: {self.last_search_status}")
            return f'job id = {self.last_search_id} not completed, status is {self.last_search_status}'

        # Exhausted all retries
        logger.error(f"Job {self.last_search_id} failed after {max_retries} retries")
        return f'job id = {self.last_search_id} failed after {max_retries} retries'

    def _extract_retry_after(self, error):
        '''
        Extracts the wait time from OpenAI's rate limit error message.

        Args:
            error: ResponseError object with message like "Please try again in 1.321s"

        Returns:
            float: Number of seconds to wait (with 0.5s buffer), or 2.0 if parsing fails
        '''
        try:
            match = re.search(r'try again in ([\d.]+)s', str(error.message))
            if match:
                wait_time = float(match.group(1)) + 0.5  # Add 0.5s buffer
                logger.debug(f"Extracted wait time: {wait_time}s from error message")
                return wait_time
        except Exception as e:
            logger.warning(f"Failed to extract wait time from error: {e}")

        # Default fallback
        return 2.0

    def wait_for_completion(self, timeout_seconds=600, poll_interval=10):
        '''
        Waits for the last search to complete by polling the API.

        Args:
            timeout_seconds: Maximum time to wait (default: 600s = 10 minutes)
            poll_interval: Seconds between polling attempts (default: 10s)

        Returns:
            bool: True if completed successfully, False if timeout or failed
        '''
        if not self.last_search_id:
            logger.error("No search ID available to wait for")
            return False

        start_time = time.time()
        logger.info(f"Waiting for search {self.last_search_id} to complete (timeout: {timeout_seconds}s)")

        while (time.time() - start_time) < timeout_seconds:
            result = self.show_last_search_response_with_retry()

            # Check if completed
            if self.last_search_status == 'completed':
                logger.info(f"Search {self.last_search_id} completed successfully")
                return True

            # Check if failed
            if self.last_search_status == 'failed':
                logger.error(f"Search {self.last_search_id} failed")
                return False

            # Still in progress, wait before next poll
            elapsed = time.time() - start_time
            logger.debug(f"Search in progress... elapsed: {elapsed:.1f}s, status: {self.last_search_status}")
            time.sleep(poll_interval)

        # Timeout reached
        logger.error(f"Search {self.last_search_id} timed out after {timeout_seconds}s")
        return False

    def validate_json_result(self, result_text: str) -> dict:
        '''
        Validates and parses the JSON result from deep research.

        This method handles common formatting issues:
        - Removes markdown code block wrappers (```json ... ```)
        - Extracts JSON object from surrounding text
        - Validates required fields are present
        - Normalizes confidence field to lowercase

        Args:
            result_text: Raw text output from the model

        Returns:
            dict: Validated JSON object with keys: real_name, confidence, evidence, academic_suitability

        Raises:
            json.JSONDecodeError: If the text cannot be parsed as JSON
            ValueError: If required fields are missing
        '''
        original_text = result_text
        result_text = result_text.strip()

        # Remove markdown code blocks
        if result_text.startswith('```'):
            logger.debug("Removing markdown code block wrapper")
            lines = result_text.split('\n')
            if len(lines) > 2:
                result_text = '\n'.join(lines[1:-1])
            else:
                result_text = result_text.replace('```json', '').replace('```', '')

        # Extract JSON object if wrapped in text
        if '{' in result_text and '}' in result_text:
            start = result_text.index('{')
            end = result_text.rindex('}') + 1
            json_str = result_text[start:end]
        else:
            json_str = result_text

        # Parse and validate
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON. Original text: {original_text[:200]}")
            raise

        required_fields = ['real_name', 'confidence', 'evidence', 'academic_suitability']
        missing_fields = [f for f in required_fields if f not in result]
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            raise ValueError(f"Missing required fields: {missing_fields}")

        # Normalize confidence to lowercase
        result['confidence'] = result['confidence'].lower()

        logger.debug(f"Successfully validated JSON result: {result['real_name']}")
        return result

    def list_search_history(self):
        '''
        This should use the dict from self.searches to list all queued, started, and finished searches
        '''
        pass

    def get_response(self, id:str):
        '''
        Recieves the response id of a backgrounded task and returns the response. If it has not finished,
        it tells the user the current status.
        '''
        try:
            retrieved_response = self.client.responses.retrieve(id)

            if retrieved_response.status != 'completed':
                logger.warning(f"Job id = {retrieved_response.id} not completed, status is {retrieved_response.status}")
                return f'job id = {retrieved_response.id} not completed, status is {retrieved_response.status}'

            logger.info(f"Job id = {retrieved_response.id} completed successfully")
            return retrieved_response.output_text

        except Exception as e:
            logger.error(f'Error retrieving response for id {id}: {e}', exc_info=True)
            return f'error: {e}'
    
    def get_status(self, id:str):
        '''
        Retrieves the current response status given the response id
        '''

        try:
            retrieved_response = self.client.responses.retrieve(id)
            logger.debug(f"Status for job id {id}: {retrieved_response.status}")
            return retrieved_response.status

        except Exception as e:
            logger.error(f'Error getting status for id {id}: {e}', exc_info=True)
            return 'error'

    def set_instruction(self, instruction:str):
        pass

    def show_instruction(self):
        pass