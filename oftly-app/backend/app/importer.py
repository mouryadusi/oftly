"""Product-URL import with SSRF protections: http(s) only, ports 80/443, public IPs only (re-checked on
every redirect), short timeouts, size caps. Reads Open Graph metadata only. Many shops block bots; failures
are reported honestly. Limitation: DNS rebinding between check and connect is not fully prevented."""
import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import httpx
from . import images

TIMEOUT, MAX_HTML, MAX_IMG = 6.0, 1_500_000, 5_000_000

class ImportFailure(Exception):
    pass

def check_url(url):
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ImportFailure("Only http:// and https:// product links are supported.")
    if p.port not in (None, 80, 443):
        raise ImportFailure("Unusual ports are blocked.")
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ImportFailure("Could not find that website.")
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ImportFailure("Blocked: that address is not on the public internet.")

def fetch(url, limit):
    headers = {"User-Agent": "OFTLYWardrobe/0.1 (personal local app)"}
    with httpx.Client(timeout=TIMEOUT, follow_redirects=False, headers=headers) as client:
        for _ in range(4):
            check_url(url)
            with client.stream("GET", url) as r:
                if r.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, r.headers.get("location", ""))
                    continue
                if r.status_code >= 400:
                    raise ImportFailure(f"The site returned HTTP {r.status_code}; it may block automated access.")
                buf = bytearray()
                for chunk in r.iter_bytes():
                    buf += chunk
                    if len(buf) > limit:
                        raise ImportFailure("The response was too large.")
                return bytes(buf), url
        raise ImportFailure("Too many redirects.")

class _Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta, self.title, self._in_title = {}, "", False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and (a.get("property") or a.get("name")) and a.get("content"):
            self.meta.setdefault((a.get("property") or a.get("name")).lower(), a["content"])
        self._in_title = tag == "title"
    def handle_endtag(self, tag):
        self._in_title = False
    def handle_data(self, data):
        if self._in_title:
            self.title += data

def import_product(url):
    result = {"ok": False, "fields": {"product_url": url}, "image": None, "image_url": None,
              "suggested_color": None, "warnings": []}
    try:
        html, final = fetch(url, MAX_HTML)
    except ImportFailure as e:
        result["error"] = str(e)
        return result
    except httpx.HTTPError:
        result["error"] = "Could not reach the website (network error or timeout)."
        return result
    p = _Meta()
    p.feed(html.decode("utf-8", "replace"))
    m = p.meta
    name = (m.get("og:title") or p.title).strip()[:120]
    if name:
        result["fields"]["name"] = name
    if m.get("og:description") or m.get("description"):
        result["fields"]["description"] = (m.get("og:description") or m.get("description"))[:2000]
    if m.get("og:site_name"):
        result["fields"]["brand"] = m["og:site_name"][:80]
    try:
        result["fields"]["price"] = float(m.get("product:price:amount", ""))
    except ValueError:
        pass
    img_url = m.get("og:image")
    if img_url:
        try:
            data, _ = fetch(urljoin(final, img_url), MAX_IMG)
            result["image"], result["suggested_color"] = images.save_upload(data)
            result["image_url"] = f"/media/{result['image']}"
        except (ImportFailure, httpx.HTTPError, images.UploadError) as e:
            result["warnings"].append(f"Could not import the product image ({e}). Please upload a photo.")
    else:
        result["warnings"].append("No product image was found. Please upload a photo.")
    result["ok"] = bool(name or result["image"])
    if not result["ok"]:
        result["error"] = "No product information could be read from that page. Enter the details manually."
    return result
