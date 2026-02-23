# DefectDojo MCP Server

[![PyPI version](https://badge.fury.io/py/defectdojo.svg)](https://badge.fury.io/py/defectdojo) <!-- Add this badge if/when published to PyPI -->

This project provides a [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/specification) server implementation for [DefectDojo](https://github.com/DefectDojo/django-DefectDojo), a popular open-source vulnerability management tool. It allows AI agents and other MCP clients to interact with the DefectDojo API programmatically.

## Features

This MCP server exposes tools for managing key DefectDojo entities:

*   **Findings:** Fetch, search, get by ID, create, update status, and add notes.
*   **Products:** List, get by ID, and count products.
*   **Product Types:** List product type categories.
*   **Engagements:** List, retrieve details, create, update, and close engagements.
*   **Tests:** List and retrieve test (scan run) details.
*   **Users & Groups:** List users, get user profiles, list groups and group members.

## Installation & Running

There are a couple of ways to run this server:

### Using `uvx` (Recommended)

`uvx` executes Python applications in temporary virtual environments, installing dependencies automatically.

```bash
uvx defectdojo-mcp
```

### Using `pip`

You can install the package into your Python environment using `pip`.

```bash
# Install directly from the cloned source code directory
pip install .

# Or, if the package is published on PyPI
pip install defectdojo-mcp
```

Once installed via pip, run the server using:

```bash
defectdojo-mcp
```

## Configuration

The server requires the following environment variables to connect to your DefectDojo instance:

*   `DEFECTDOJO_API_TOKEN` (**required**): Your DefectDojo API token for authentication.
*   `DEFECTDOJO_API_BASE` (**required**): The base URL of your DefectDojo instance (e.g., `https://your-defectdojo-instance.com`).

You can configure these in your MCP client's settings file. Here's an example using the `uvx` command:

```json
{
  "mcpServers": {
    "defectdojo": {
      "command": "uvx",
      "args": ["defectdojo-mcp"],
      "env": {
        "DEFECTDOJO_API_TOKEN": "YOUR_API_TOKEN_HERE",
        "DEFECTDOJO_API_BASE": "https://your-defectdojo-instance.com"
      }
    }
  }
}
```

If you installed the package using `pip`, the configuration would look like this:

```json
{
  "mcpServers": {
    "defectdojo": {
      "command": "defectdojo-mcp",
      "args": [],
      "env": {
        "DEFECTDOJO_API_TOKEN": "YOUR_API_TOKEN_HERE",
        "DEFECTDOJO_API_BASE": "https://your-defectdojo-instance.com"
      }
    }
  }
}
```

## Available Tools

The following tools are available via the MCP interface:

*   `get_findings`: Retrieve findings with filtering (product_name, severity, active, is_mitigated, duplicate, engagement_id) and pagination (limit, offset).
*   `search_findings`: Search findings using a text query, with filtering (active, is_mitigated, duplicate, engagement_id) and pagination.
*   `count_findings`: Return total number of findings matching the given filters (lightweight, no full payload). Supports engagement_id for per-engagement counts.
*   `get_finding`: Get a specific finding by its ID with full details.
*   `update_finding_status`: Change the status of a specific finding (e.g., Active, Verified, False Positive).
*   `add_finding_note`: Add a textual note to a finding.
*   `create_finding`: Create a new finding associated with a test.
*   `list_products`: List products with filtering (name, prod_type, tags, external_audience, internet_accessible) and pagination.
*   `count_products`: Return total number of products matching the given filters (lightweight, no full payload).
*   `get_product`: Get a specific product by its ID.
*   `list_product_types`: List all product type categories with optional name filtering and pagination.
*   `list_engagements`: List engagements with filtering (product_id, status, name) and pagination.
*   `get_engagement`: Get details for a specific engagement by its ID.
*   `create_engagement`: Create a new engagement for a product.
*   `update_engagement`: Modify details of an existing engagement.
*   `close_engagement`: Mark an engagement as completed.
*   `list_tests`: List tests (scan runs) with filtering by engagement, test type, and tags.
*   `get_test`: Get a specific test by its ID.
*   `list_users`: List DefectDojo users with filtering by username, name, and active status.
*   `get_user`: Get a specific user by their ID with full profile details.
*   `list_dojo_groups`: List DefectDojo groups (teams) with optional name filtering.
*   `list_dojo_group_members`: List members of DefectDojo groups with optional group/user filtering.

## Usage Examples

*(Note: These examples assume an MCP client environment capable of calling `use_mcp_tool`)*

### Get Findings

```python
# Get active (open) high-severity findings (limit 10)
result = await use_mcp_tool("defectdojo", "get_findings", {
    "active": True,
    "severity": "High",
    "limit": 10
})

# Get inactive (closed) findings
result = await use_mcp_tool("defectdojo", "get_findings", {
    "active": False
})

# Get mitigated findings
result = await use_mcp_tool("defectdojo", "get_findings", {
    "is_mitigated": True
})

# Get only unique (non-duplicate) findings
result = await use_mcp_tool("defectdojo", "get_findings", {
    "duplicate": False
})

# Combine filters: active critical non-duplicate findings
result = await use_mcp_tool("defectdojo", "get_findings", {
    "severity": "Critical",
    "active": True,
    "duplicate": False,
    "limit": 50
})

# Get findings scoped to a specific engagement
result = await use_mcp_tool("defectdojo", "get_findings", {
    "engagement_id": 17002,
    "active": True,
    "severity": "High"
})
```

### Search Findings

```python
# Search for findings containing 'SQL Injection'
result = await use_mcp_tool("defectdojo", "search_findings", {
    "query": "SQL Injection"
})

# Search only active, non-duplicate findings
result = await use_mcp_tool("defectdojo", "search_findings", {
    "query": "SQL Injection",
    "active": True,
    "duplicate": False
})

# Search findings within a specific engagement
result = await use_mcp_tool("defectdojo", "search_findings", {
    "query": "SQL Injection",
    "engagement_id": 17002
})
```

### Count Findings

```python
# Count all findings
result = await use_mcp_tool("defectdojo", "count_findings", {})

# Count active (open) findings only
result = await use_mcp_tool("defectdojo", "count_findings", {
    "active": True
})

# Count unique (non-duplicate) findings only
result = await use_mcp_tool("defectdojo", "count_findings", {
    "duplicate": False
})

# Count active critical non-duplicate findings
result = await use_mcp_tool("defectdojo", "count_findings", {
    "severity": "Critical",
    "active": True,
    "duplicate": False
})

# Count findings in a specific engagement
result = await use_mcp_tool("defectdojo", "count_findings", {
    "engagement_id": 17002,
    "active": True
})

# Count critical findings in a specific engagement
result = await use_mcp_tool("defectdojo", "count_findings", {
    "engagement_id": 17002,
    "severity": "Critical",
    "active": True
})
```

### Update Finding Status

```python
# Mark finding 123 as Verified
result = await use_mcp_tool("defectdojo", "update_finding_status", {
    "finding_id": 123,
    "status": "Verified"
})
```

### Add Note to Finding

```python
result = await use_mcp_tool("defectdojo", "add_finding_note", {
    "finding_id": 123,
    "note": "Confirmed vulnerability on staging server."
})
```

### Create Finding

```python
result = await use_mcp_tool("defectdojo", "create_finding", {
    "title": "Reflected XSS in Search Results",
    "test_id": 55, # ID of the associated test
    "severity": "Medium",
    "description": "User input in search is not properly sanitized, leading to XSS.",
    "cwe": 79
})
```

### List Products

```python
# List products containing 'Web App' in their name
result = await use_mcp_tool("defectdojo", "list_products", {
    "name": "Web App",
    "limit": 10
})

# Filter products by tag
result = await use_mcp_tool("defectdojo", "list_products", {
    "tags": "full_sdlc"
})

# Filter by multiple tags (AND mode — products must have all tags)
result = await use_mcp_tool("defectdojo", "list_products", {
    "tags": ["full_sdlc", "cloud"],
    "tags_mode": "all"
})

# Filter by multiple tags (OR mode — products with any of the tags)
result = await use_mcp_tool("defectdojo", "list_products", {
    "tags": ["full_sdlc", "cloud"],
    "tags_mode": "any"
})

# Filter by external_audience and internet_accessible
result = await use_mcp_tool("defectdojo", "list_products", {
    "external_audience": True,
    "internet_accessible": True
})

# Combine multiple filters
result = await use_mcp_tool("defectdojo", "list_products", {
    "tags": "full_sdlc",
    "external_audience": True,
    "prod_type": 7,
    "limit": 20
})
```

### Get Finding

```python
# Get a specific finding by ID
result = await use_mcp_tool("defectdojo", "get_finding", {
    "finding_id": 702704
})
```

### Get Product

```python
# Get a specific product by ID
result = await use_mcp_tool("defectdojo", "get_product", {
    "product_id": 15
})
```

### List Product Types

```python
# List all product types
result = await use_mcp_tool("defectdojo", "list_product_types", {})

# Filter product types by name
result = await use_mcp_tool("defectdojo", "list_product_types", {
    "name": "Docker"
})
```

### Count Products

```python
# Count all products
result = await use_mcp_tool("defectdojo", "count_products", {})

# Count products with a specific tag
result = await use_mcp_tool("defectdojo", "count_products", {
    "tags": "full_sdlc"
})

# Count with combined filters
result = await use_mcp_tool("defectdojo", "count_products", {
    "tags": "full_sdlc",
    "external_audience": True
})
```

### List Engagements

```python
# List 'In Progress' engagements for product ID 42
result = await use_mcp_tool("defectdojo", "list_engagements", {
    "product_id": 42,
    "status": "In Progress"
})
```

### Get Engagement

```python
result = await use_mcp_tool("defectdojo", "get_engagement", {
    "engagement_id": 101
})
```

### Create Engagement

```python
result = await use_mcp_tool("defectdojo", "create_engagement", {
    "product_id": 42,
    "name": "Q2 Security Scan",
    "target_start": "2025-04-01",
    "target_end": "2025-04-15",
    "status": "Not Started"
})
```

### Update Engagement

```python
result = await use_mcp_tool("defectdojo", "update_engagement", {
    "engagement_id": 101,
    "status": "In Progress",
    "description": "Scan initiated."
})
```

### Close Engagement

```python
result = await use_mcp_tool("defectdojo", "close_engagement", {
    "engagement_id": 101
})
```

### List Tests

```python
# List tests for a specific engagement
result = await use_mcp_tool("defectdojo", "list_tests", {
    "engagement_id": 101
})

# List tests with a specific test type
result = await use_mcp_tool("defectdojo", "list_tests", {
    "test_type": 156,
    "limit": 10
})
```

### Get Test

```python
# Get a specific test by ID
result = await use_mcp_tool("defectdojo", "get_test", {
    "test_id": 18550
})
```

### List Users

```python
# List all active users
result = await use_mcp_tool("defectdojo", "list_users", {
    "is_active": True
})

# Find a user by username
result = await use_mcp_tool("defectdojo", "list_users", {
    "username": "admin"
})

# Find users by name
result = await use_mcp_tool("defectdojo", "list_users", {
    "first_name": "John",
    "is_active": True
})
```

### Get User

```python
# Get a specific user profile by ID
result = await use_mcp_tool("defectdojo", "get_user", {
    "user_id": 1
})
```

### List Groups

```python
# List all DefectDojo groups
result = await use_mcp_tool("defectdojo", "list_dojo_groups", {})

# Filter groups by name
result = await use_mcp_tool("defectdojo", "list_dojo_groups", {
    "name": "AppSec"
})
```

### List Group Members

```python
# List all members of a specific group
result = await use_mcp_tool("defectdojo", "list_dojo_group_members", {
    "group_id": 3
})

# Find which groups a user belongs to
result = await use_mcp_tool("defectdojo", "list_dojo_group_members", {
    "user_id": 42
})
```

## Development

### Setup

1.  Clone the repository.
2.  It's recommended to use a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
    ```
3.  Install dependencies, including development dependencies:
    ```bash
    pip install -e ".[dev]"
    ```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to open an issue for bugs, feature requests, or questions. If you'd like to contribute code, please open an issue first to discuss the proposed changes.
