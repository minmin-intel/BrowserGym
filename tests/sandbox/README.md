# Playwright Browser Sandbox

This is a containerized environment for running Playwright with Chrome browser and exposing browser actions through a RESTful API. The container is based on the official Microsoft Playwright Docker image that comes with pre-installed browsers.

## Features

- Launch browser instances with configurable options
- Create browser contexts with custom viewport sizes and user agents
- Navigate to URLs
- Click on elements
- Type text into form fields
- Wait for elements to appear
- Evaluate JavaScript in the page context
- Take screenshots of pages or specific elements
- Get accessibility tree snapshots for accessibility testing
- Health check endpoint

## Building the Container

```bash
docker build -t playwright-sandbox .
```

# Building with HTTP Proxy

If you're behind a corporate proxy, you can use build arguments to configure the proxy settings:

```bash
docker build --build-arg http_proxy=$http_proxy \
             --build-arg https_proxy=$https_proxy \
             -t playwright-sandbox .
```


## Running the Container

```bash
docker run --name pw-sandbox -v $WORKDIR/BrowserGym/tests/sandbox:/app -e http_proxy=$http_proxy -e https_proxy=$https_proxy -e no_proxy=$no_proxy -p 8000:8000 -d playwright-sandbox
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
python3 client.py

# Run with custom options
python3 client.py --url https://example.com --headless=false

# Specify custom output file for accessibility tree YAML
python3 client.py --url https://www.w3.org/WAI/ --a11y-output=w3c_accessibility.yaml
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

# Get accessibility tree snapshot
accessibility_response = requests.post(
    f"http://localhost:8000/page/{page_id}/accessibility_snapshot"
)
accessibility_data = accessibility_response.json()
snapshot = accessibility_data["snapshot"]

# Using the client's built-in YAML conversion
from client import PlaywrightClient

client = PlaywrightClient()
# ...setup and navigate to a page...

# Get accessibility tree as YAML string
yaml_string = client.accessibility_snapshot_as_yaml()

# Save YAML to file
with open("a11y_tree.yaml", "w") as f:
    f.write(yaml_string)
```

## Environment Variables

- `PLAYWRIGHT_HEADLESS`: Set to "false" to run browsers in non-headless mode (default: "true")

## Accessibility Testing

The sandbox includes features for accessibility testing:

1. **API Endpoint**: `/page/{page_id}/accessibility_snapshot` returns the complete accessibility tree
2. **YAML Conversion**: The client can convert the accessibility tree to YAML format
3. **Command Line Option**: `--a11y-output` specifies where to save the YAML file

### Sample YAML Output

```yaml
role: WebArea
name: Document
children:
  - role: heading
    name: Welcome to the Accessibility Test Page
    level: 1
  - role: link
    name: Skip to content
    description: Bypass navigation
  - role: navigation
    name: Main Navigation
    children:
      - role: button
        name: Menu
        expanded: false
```

This structured format makes it easier to:
- Analyze page structure from an accessibility perspective
- Identify missing ARIA attributes or labels
- Verify screen reader compatibility
- Export accessibility information for reporting

## Troubleshooting

### Screenshot Timeout Issues

If you encounter timeout issues when taking screenshots, especially in headless mode, try the following solutions:

1. **Increase the Screenshot Timeout**:
   ```python
   # When calling the screenshot method
   client.screenshot(path="screenshot.png", timeout=90000)  # 90 seconds timeout
   ```

2. **Add Explicit Waits**:
   ```python
   # Wait for the page to be fully loaded
   client.navigate(url, wait_until="networkidle")
   time.sleep(3)  # Add a short pause
   client.screenshot(path="screenshot.png")
   ```

3. **Additional Browser Launch Arguments**:
   If using the API directly, add these arguments when launching the browser:
   ```json
   {
     "headless": true,
     "args": ["--no-sandbox", "--disable-dev-shm-usage"]
   }
   ```

## License

See the LICENSE file in the root of the repository.
