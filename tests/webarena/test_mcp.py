from fastmcp import Client
import asyncio
import playwright
import os

# first make the browser ready
# go to the URL
# log in
ENV_VARS = ("SHOPPING", "SHOPPING_ADMIN", "REDDIT", "GITLAB", "WIKIPEDIA", "MAP", "HOMEPAGE")
def setup_browser(site: str, page: playwright.sync_api.Page):
    # setup webarena environment variables (webarena will read those on import)
    append_wa = lambda x: f"WA_{x}"
    for key in ENV_VARS:
        assert append_wa(key) in os.environ, (
            f"Environment variable {append_wa(key)} missing.\n"
            + "Please set the following environment variables to use WebArena through BrowserGym:\n"
            + "\n".join([append_wa(x) for x in ENV_VARS])
        )
        os.environ[key] = os.environ[append_wa(key)]

    # import webarena on instanciation
    from webarena.browser_env.env_config import (
        ACCOUNTS,
        GITLAB,
        HOMEPAGE,
        MAP,
        REDDIT,
        SHOPPING,
        SHOPPING_ADMIN,
        WIKIPEDIA,
    )

    urls = {
            "reddit": REDDIT,
            "gitlab": GITLAB,
            "shopping": SHOPPING,
            "shopping_admin": SHOPPING_ADMIN,
            "wikipedia": WIKIPEDIA,
            "map": MAP,
        }

    username = ACCOUNTS[site]["username"]
    password = ACCOUNTS[site]["password"]
    url = urls[site]
    page.goto(url)
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()

async def main():
    # Connect via SSE
    async with Client("http://localhost:8931/mcp") as client:
        # list tools
        # tools = await client.list_tools()
        # print(tools)
        # navigate to a URL
        result = await client.call_tool("browser_navigate", {"url":"http://10.7.4.57:9083/admin"})
        print(result)
        result = await client.call_tool("browser_type", {"url":"http://

        # capture a snapshot

if __name__ == "__main__":
    asyncio.run(main())