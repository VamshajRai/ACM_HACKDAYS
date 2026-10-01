import re
import httpx
from bs4 import BeautifulSoup

URL_RE = re.compile(r"^https?://\S+$", re.I)


def is_url(text: str) -> bool:
    return bool(URL_RE.match(text.strip()))


async def fetch_page_text(url: str, limit: int = 6000) -> str:
    """Download a web page and return readable text (free, no API needed)."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=10,
                                 headers={"User-Agent": "TrustScanBot/0.1"}) as http:
        r = await http.get(url)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    body = " ".join(soup.get_text(separator=" ").split())
    return f"URL: {url}\nTITLE: {title}\nCONTENT: {body[:limit]}"
