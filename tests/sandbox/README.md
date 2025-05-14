# Playwright Browser Sandbox

This is a containerized environment for running Playwright with Chrome browser and exposing browser actions through a RESTful API.

## Features

- Launch browser instances with configurable options
- Create browser contexts with custom viewport sizes and user agents
- Navigate to URLs
- Click on elements
- Type text into form fields
- Wait for elements to appear
- Evaluate JavaScript in the page context
- Take screenshots of pages or specific elements
- Health check endpoint

## Building the Container

```bash
docker build -t playwright-sandbox .
```

## Running the Container

```bash
docker run -p 8000:8000 playwright-sandbox
```

This will start the server on port 8000.

## API Endpoints

### Browser Management

- `POST /browser/launch` - Launch a new browser instance
- `POST /browser/{browser_id}/context` - Create a new browser context
- `POST /context/{context_id}/page` - Create a new page in a browser context
- `POST /browser/{browser_id}/close` - Close a browser instance
- `POST /context/{context_id}/close` - Close a browser context
- `POST /page/{page_id}/close` - Close a page

### Page Actions

- `POST /page/{page_id}/navigate` - Navigate to a URL
- `POST /page/{page_id}/click` - Click on an element matching the selector
- `POST /page/{page_id}/type` - Type text into an element matching the selector
- `POST /page/{page_id}/wait_for_selector` - Wait for an element matching the selector
- `POST /page/{page_id}/evaluate` - Evaluate JavaScript in the page context
- `POST /page/{page_id}/screenshot` - Take a screenshot of the page

### Other

- `GET /health` - Health check endpoint

## Example Usage

You can use the included `client.py` script to interact with the API:

```bash
# Run with default options (navigates to google.com in headless mode)
python client.py

# Run with custom options
python client.py --url https://example.com --headless=false
```

## API Examples

### Launch a Browser and Create a Page

```python
import requests

# Launch browser
browser_response = requests.post(
    "http://localhost:8000/browser/launch",
    json={"headless": True}
)
browser_data = browser_response.json()
browser_id = browser_data["browser_id"]

# Create context
context_response = requests.post(
    f"http://localhost:8000/browser/{browser_id}/context",
    json={"width": 1280, "height": 720}
)
context_data = context_response.json()
context_id = context_data["context_id"]

# Create page
page_response = requests.post(
    f"http://localhost:8000/context/{context_id}/page"
)
page_data = page_response.json()
page_id = page_data["page_id"]

# Navigate to a URL
navigate_response = requests.post(
    f"http://localhost:8000/page/{page_id}/navigate",
    json={"url": "https://www.example.com", "wait_until": "networkidle"}
)
```

### Perform Actions on a Page

```python
# Click on an element
click_response = requests.post(
    f"http://localhost:8000/page/{page_id}/click",
    json={"selector": "button#submit"}
)

# Type text
type_response = requests.post(
    f"http://localhost:8000/page/{page_id}/type",
    json={"selector": "input#search", "text": "Hello world"}
)

# Take a screenshot
screenshot_response = requests.post(
    f"http://localhost:8000/page/{page_id}/screenshot",
    json={"full_page": True}
)
screenshot_data = screenshot_response.json()
screenshot_base64 = screenshot_data["screenshot"]
```

## Environment Variables

- `PLAYWRIGHT_HEADLESS`: Set to "false" to run browsers in non-headless mode (default: "true")

## License

See the LICENSE file in the root of the repository.
