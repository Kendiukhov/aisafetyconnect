# LessWrong Extractor - Code Documentation

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│                  main.py                     │
│         (Entry point & orchestration)        │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│          LessWrongExtractor                  │
│    (Platform-specific implementation)        │
└────────────────────┬────────────────────────┘
                     │ inherits
┌────────────────────▼────────────────────────┐
│         BasePlatformExtractor                │
│    (Abstract base class & framework)         │
└──────────────────────────────────────────────┘
```

## File Structure

```
aisafetyconnect/
├── base_extractor.py       # Abstract base class
├── lesswrong_extractor.py  # LessWrong implementation
├── main.py                 # Entry point
├── pyproject.toml          # Dependencies
└── documentation/          # Documentation files
```

## Core Classes and Methods

### 1. BasePlatformExtractor (base_extractor.py)

**Purpose**: Abstract base class providing common functionality for all platform extractors.

```python
class BasePlatformExtractor(ABC):
    """
    Framework for platform-specific extractors.
    Handles directory setup, data saving, and orchestration.
    """
```

**Key Methods**:

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `__init__()` | Initialize extractor, setup logging | `base_output_dir` | None |
| `setup_directories()` | Create output folder structure | None | None |
| `save_to_json()` | Save data with proper formatting | `data`, `filepath` | None |
| `extract_and_save_all()` | Main orchestration pipeline | `limit` | None |
| `extract_top_users()` | *Abstract* - Get top users | `limit` | List[User] |
| `extract_user_posts()` | *Abstract* - Get user posts | `user_id` | List[Post] |
| `extract_user_comments()` | *Abstract* - Get comments | `user_id` | List[Comment] |

### 2. LessWrongExtractor (lesswrong_extractor.py)

**Purpose**: Concrete implementation for LessWrong platform using GraphQL API.

```python
class LessWrongExtractor(BasePlatformExtractor):
    """
    LessWrong-specific extractor using GraphQL API.
    Implements AI Safety tag discovery and enrichment.
    """
```

**Configuration**:
```python
self.graphql_endpoint = "https://www.lesswrong.com/graphql"
self.rate_limit_delay = 0.5  # seconds between requests
self.max_retries = 3         # retry attempts for failed requests
```

**Core Methods**:

| Method | Purpose | Complexity |
|--------|---------|------------|
| `setup_ai_safety_tags()` | Define AI Safety tag mappings | Simple |
| `make_graphql_request()` | Execute GraphQL with retry logic | Medium |
| `extract_top_users()` | Find users via tag search | Complex |
| `get_user_full_info()` | Fetch complete user profile | Simple |
| `extract_user_posts()` | Download all user posts | Medium |
| `extract_user_comments()` | Download all comments | Medium |
| `enrich_post_with_ai_safety_tags()` | Add AI Safety metadata | Complex |
| `map_tag_to_research_agenda()` | Categorize tags | Simple |

**Method Details**:

#### `extract_top_users(limit: int) -> List[Dict]`
```python
# Algorithm:
1. For each AI Safety tag:
   - Query posts with that tag
   - Extract unique authors
   - Track which posts came from which tags
2. Aggregate all discovered users
3. Sort by karma (reputation)
4. Enrich top N users with full profiles
5. Return enriched user list
```

#### `enrich_post_with_ai_safety_tags(post: Dict)`
```python
# Algorithm:
1. Initialize empty AI Safety fields
2. Check post tags against AI Safety tag list
3. If match found:
   - Add to ai_safety_tags array
   - Map to research agenda
   - Set extraction_source
4. Preserve original tag discovery info if available
```

### 3. Main Entry Point (main.py)

**Purpose**: Configure logging and execute extraction pipeline.

```python
def main():
    """
    Entry point for extraction.
    Configures logging and runs extractor.
    """
```

**Configuration Options**:
- `limit=3`: Test mode (3 users)
- `limit=100`: Production mode (100 users)
- `logging.DEBUG`: Verbose output
- `logging.INFO`: Standard output

## Data Structures

### User Object
```python
{
    "userId": "string",
    "username": "string",
    "displayName": "string",
    "karma": float,
    "afKarma": float,
    "bio": "string",
    "jobTitle": "string",
    "organization": "string",
    "website": "string",
    "linkedinProfileURL": "string",
    "githubProfileURL": "string",
    "twitterProfileURL": "string",
    "postCount": int,
    "commentCount": int,
    "ai_safety_tags": ["MIRI", "AI Governance"],
    "post_count_in_ai_safety": int
}
```

### Post Object (Enriched)
```python
{
    "_id": "string",
    "title": "string",
    "baseScore": float,
    "contents": {
        "markdown": "string",
        "wordCount": int
    },
    "tags": [{
        "_id": "string",
        "name": "string"
    }],
    # AI Safety enrichment fields:
    "ai_safety_tags": [{
        "id": "string",
        "name": "string",
        "source": "post_tag"
    }],
    "research_agendas": ["Alignment Theory"],
    "extraction_source": {
        "tag_id": "string",
        "tag_name": "string",
        "research_agenda": "string"
    }
}
```

## GraphQL Queries

### 1. Search Posts by Tag
```graphql
query GetPostsByTag($tagId: String!, $limit: Int!) {
  posts(input: {
    terms: {
      filterSettings: {
        tags: [{tagId: $tagId, filterMode: "Required"}]
      }
      limit: $limit
    }
  }) {
    results { _id, userId, user { ... } }
  }
}
```

### 2. Get User Profile
```graphql
query GetUserFullInfo {
  user(selector: {_id: "USER_ID"}) {
    result { _id, username, karma, ... }
  }
}
```

### 3. Get User Posts
```graphql
query GetUserPosts {
  posts(selector: {userPosts: {userId: "USER_ID"}}, limit: 50) {
    results { _id, title, tags, ... }
  }
}
```

### 4. Get User Comments
```graphql
query GetUserComments {
  comments(selector: {profileComments: {userId: "USER_ID"}}, limit: 100) {
    results { _id, postId, contents, ... }
  }
}
```

## Error Handling

### Retry Strategy
```python
for attempt in range(self.max_retries):
    try:
        # Make request
        return response
    except Exception:
        if attempt == self.max_retries - 1:
            raise
        time.sleep(2 ** attempt)  # Exponential backoff
```

### Rate Limiting
```python
time.sleep(self.rate_limit_delay)  # 0.5s between requests
```

### Error Recovery
- Automatic retry with exponential backoff
- Checkpoint saves every 10 users
- Graceful failure with partial data preservation

## Configuration & Extension

### Adding New AI Safety Tags
```python
self.DEFINITE_AI_SAFETY_TAGS = {
    "TAG_ID": {"name": "Tag Name", "posts": count},
    # Add more tags here
}
```

### Extending to New Platform
```python
class NewPlatformExtractor(BasePlatformExtractor):
    def get_platform_name(self) -> str:
        return "new_platform"

    def extract_top_users(self, limit: int):
        # Implement platform-specific logic
        pass

    # Implement other abstract methods
```

## Performance Metrics

| Operation | Time | Rate |
|-----------|------|------|
| GraphQL Request | ~0.5s | 2 req/s |
| User Extraction | ~10s | 6 users/min |
| Post Extraction | ~3s | 20 posts/min |
| Comment Extraction | ~1s | 60 comments/min |
| Full Pipeline (3 users) | ~30s | - |
| Full Pipeline (100 users) | ~20 min | - |

## Dependencies

- **requests**: HTTP/GraphQL communication
- **pathlib**: Cross-platform file operations
- **logging**: Comprehensive audit trail
- **json**: Data serialization
- **time**: Rate limiting
- **abc**: Abstract base classes
- **datetime**: Timestamp generation

## Testing

### Test Extraction (3 users)
```bash
uv run python main.py
```

### Verify Output
```bash
ls -la raw-data/lesswrong/2024-*/
cat raw-data/lesswrong/2024-*/users_top3.json | jq '.[] | .username'
```

### Check Enrichment
```bash
cat raw-data/lesswrong/2024-*/posts/*.json | jq '.[] | select(.ai_safety_tags | length > 0)'
```

## Maintenance

### Log Files
- `extraction.log`: Complete operation history
- Check for WARNING/ERROR messages
- Monitor extraction times

### Common Issues
1. **Empty ai_safety_tags**: Post doesn't contain AI Safety topics
2. **Rate limit errors**: Increase `rate_limit_delay`
3. **Timeout errors**: Increase timeout in `make_graphql_request()`
4. **Missing data**: Check GraphQL query structure

## Future Improvements

1. **Pagination**: Handle >50 posts per user
2. **Incremental Updates**: Track last extraction date
3. **Parallel Processing**: Multi-threaded extraction
4. **Data Validation**: Schema enforcement
5. **Monitoring Dashboard**: Real-time extraction status