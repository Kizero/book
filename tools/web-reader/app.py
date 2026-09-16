#!/usr/bin/env python3
"""A tiny local web-content reader with a remote-reader fallback."""

from __future__ import annotations

import argparse
import errno
import html
import http.client
import http.cookiejar
import ipaddress
import json
import re
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable


APP_DIR = Path(__file__).resolve().parent
INDEX_FILE = APP_DIR / "index.html"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DIRECT_TIMEOUT_SECONDS = 8
READER_TIMEOUT_SECONDS = 30
ARCHIVE_TIMEOUT_SECONDS = 12
REDDIT_SEARCH_PAGE_SIZE = 10
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
READER_USER_AGENT = "web-reader/0.1"
DOH_RESOLVER_URL = "https://dns.google/resolve"
REDDIT_ARCHIVE_BASE = "https://arctic-shift.photon-reddit.com"
SCRIPTBIN_HOSTS = {"scriptbin.works", "www.scriptbin.works"}
REDDIT_HOSTS = {
    "reddit.com", "www.reddit.com", "old.reddit.com", "new.reddit.com",
    "np.reddit.com", "sh.reddit.com", "redd.it",
}
_DOH_CACHE: dict[str, tuple[float, list[str]]] = {}


class ReaderError(Exception):
    """An expected error that can be shown to the user."""


@dataclass
class Attempt:
    route: str
    ok: bool
    detail: str
    elapsed_ms: int


@dataclass
class ContentLink:
    title: str
    url: str
    kind: str = "content"


@dataclass
class FetchResult:
    ok: bool
    source_url: str
    route: str
    content: str
    title: str
    content_type: str
    elapsed_ms: int
    links: list[ContentLink]
    attempts: list[Attempt]
    requires_confirmation: bool = False

    def to_dict(self) -> dict:
        value = asdict(self)
        value["links"] = [asdict(item) for item in self.links]
        value["attempts"] = [asdict(item) for item in self.attempts]
        return value


def normalize_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        raise ReaderError("请输入网址")
    if "://" not in value:
        value = "https://" + value

    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ReaderError("只支持 http:// 或 https:// 网址")
    if not parsed.hostname:
        raise ReaderError("网址缺少域名")
    if parsed.username or parsed.password:
        raise ReaderError("网址不能包含用户名或密码")
    if parsed.hostname.lower() == "localhost" or parsed.hostname.lower().endswith(".local"):
        raise ReaderError("不读取本机或局域网地址")
    try:
        literal = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        if not literal.is_global:
            raise ReaderError("不读取本机、局域网或保留地址")
    return urllib.parse.urlunsplit(parsed)


def ensure_public_host(url: str) -> None:
    """Reject local/private targets before a server-side request."""
    host = urllib.parse.urlsplit(url).hostname
    if not host:
        raise ReaderError("网址缺少域名")

    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
            }
        except socket.gaierror as exc:
            raise ReaderError(f"域名解析失败：{exc}") from exc

    if not addresses or any(not address.is_global for address in addresses):
        raise ReaderError("不读取本机、局域网或保留地址")


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
        normalized = normalize_url(newurl)
        ensure_public_host(normalized)
        return super().redirect_request(req, fp, code, msg, headers, normalized)


def read_limited(response, limit: int = MAX_RESPONSE_BYTES) -> bytes:
    length_header = response.headers.get("Content-Length")
    if length_header and int(length_header) > limit:
        raise ReaderError(f"页面超过 {limit // (1024 * 1024)} MB 限制")
    body = response.read(limit + 1)
    if len(body) > limit:
        raise ReaderError(f"页面超过 {limit // (1024 * 1024)} MB 限制")
    return body


def decode_body(body: bytes, content_type: str) -> str:
    charset_match = re.search(r"charset=([\w.-]+)", content_type, re.I)
    encodings = [charset_match.group(1)] if charset_match else []
    encodings.extend(["utf-8", "gb18030", "latin-1"])
    for encoding in encodings:
        try:
            return body.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


class TextExtractor:
    """Conservative HTML-to-text extraction using only the Python standard library."""

    SKIP_TAGS = {"script", "style", "svg", "canvas", "template", "noscript"}
    BREAK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "dd", "div", "dl",
        "dt", "figcaption", "figure", "footer", "h1", "h2", "h3", "h4", "h5",
        "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section",
        "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
    }

    def __init__(self) -> None:
        from html.parser import HTMLParser

        outer = self

        class Parser(HTMLParser):
            def __init__(self) -> None:
                super().__init__(convert_charrefs=True)
                self.skip_depth = 0
                self.in_title = False
                self.parts: list[str] = []
                self.title_parts: list[str] = []

            def handle_starttag(self, tag, attrs):
                tag = tag.lower()
                if tag in outer.SKIP_TAGS:
                    self.skip_depth += 1
                if self.skip_depth:
                    return
                if tag == "title":
                    self.in_title = True
                if tag in outer.BREAK_TAGS:
                    self.parts.append("\n")

            def handle_endtag(self, tag):
                tag = tag.lower()
                if tag in outer.SKIP_TAGS:
                    self.skip_depth = max(0, self.skip_depth - 1)
                    return
                if self.skip_depth:
                    return
                if tag == "title":
                    self.in_title = False
                if tag in outer.BREAK_TAGS:
                    self.parts.append("\n")

            def handle_data(self, data):
                if self.skip_depth:
                    return
                value = re.sub(r"\s+", " ", data).strip()
                if not value:
                    return
                self.parts.append(value + " ")
                if self.in_title:
                    self.title_parts.append(value)

        self.parser = Parser()

    def extract(self, source: str) -> tuple[str, str]:
        self.parser.feed(source)
        raw = "".join(self.parser.parts)
        raw = re.sub(r"[ \t]+\n", "\n", raw)
        raw = re.sub(r"\n[ \t]+", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        raw = re.sub(r" {2,}", " ", raw).strip()
        title = " ".join(self.parser.title_parts).strip()
        return html.unescape(raw), html.unescape(title)


def extract_content_links(content: str, source_url: str, limit: int = 50) -> list[ContentLink]:
    """Extract a small, deduplicated navigation list from Markdown content."""
    links: list[ContentLink] = []
    seen: set[str] = set()
    pattern = re.compile(r"(?<!!)\[([^\]\n]{1,240})\]\((https?://[^)\s]+)\)")
    for match in pattern.finditer(content):
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        raw_url = html.unescape(match.group(2)).strip()
        try:
            link_url = normalize_url(urllib.parse.urljoin(source_url, raw_url))
        except ReaderError:
            continue
        if not title or link_url in seen or link_url == source_url:
            continue
        seen.add(link_url)
        kind = "navigation" if "上一页" in title or "下一页" in title else "content"
        links.append(ContentLink(title=title, url=link_url, kind=kind))
        if len(links) >= limit:
            break
    return links


def markdown_link_label(value: str) -> str:
    """Keep untrusted titles from breaking the small Markdown link extractor."""
    return value.replace("[", "［").replace("]", "］")


def fetch_url(
    url: str,
    timeout: int,
    validate_target: bool = True,
    user_agent: str = USER_AGENT,
    accept: str = "text/html,text/plain,application/xhtml+xml;q=0.9,*/*;q=0.5",
) -> tuple[str, str, int]:
    if validate_target:
        ensure_public_host(url)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": accept,
            "Accept-Encoding": "identity",
        },
    )
    opener = urllib.request.build_opener(SafeRedirectHandler())
    with opener.open(request, timeout=timeout) as response:
        status = response.status
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        body = read_limited(response)
    return decode_body(body, content_type), content_type, status


def resolve_public_ipv4_via_doh(host: str) -> list[str]:
    """Resolve a host through DNS-over-HTTPS and reject non-public answers."""
    cached = _DOH_CACHE.get(host)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    query = urllib.parse.urlencode({"name": host, "type": "A"})
    source, _content_type, status = fetch_url(
        f"{DOH_RESOLVER_URL}?{query}",
        timeout=8,
        user_agent=READER_USER_AGENT,
        accept="application/dns-json",
    )
    if status != 200:
        raise ReaderError(f"可信 DNS 返回 HTTP {status}")
    try:
        payload = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ReaderError("可信 DNS 返回了无效数据") from exc

    addresses: list[str] = []
    for answer in payload.get("Answer", []):
        if answer.get("type") != 1:
            continue
        try:
            address = ipaddress.ip_address(answer.get("data", ""))
        except ValueError:
            continue
        if address.version == 4 and address.is_global:
            addresses.append(str(address))
    if not addresses:
        raise ReaderError(f"可信 DNS 没有返回 {host} 的公共 IPv4 地址")

    unique_addresses = list(dict.fromkeys(addresses))
    _DOH_CACHE[host] = (time.monotonic() + 300, unique_addresses)
    return unique_addresses


class ResolvedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a chosen IP while verifying TLS against the original host."""

    def __init__(self, hostname: str, resolved_ip: str, timeout: int) -> None:
        super().__init__(hostname, timeout=timeout, context=ssl.create_default_context())
        self.resolved_ip = resolved_ip

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self.resolved_ip, self.port), self.timeout, self.source_address
        )
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def fetch_https_via_addresses(
    url: str,
    addresses: list[str],
    timeout: int,
    user_agent: str,
    accept: str,
) -> tuple[str, str, int]:
    """Fetch one HTTPS URL through trusted addresses without disabling TLS checks."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ReaderError("固定地址读取只支持 HTTPS")
    request_path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    errors: list[str] = []

    for address in addresses:
        connection = ResolvedHTTPSConnection(parsed.hostname, address, timeout)
        try:
            connection.request(
                "GET",
                request_path,
                headers={
                    "Host": parsed.netloc,
                    "User-Agent": user_agent,
                    "Accept": accept,
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            content_type = response.headers.get(
                "Content-Type", "application/octet-stream"
            )
            body = read_limited(response)
            if response.status >= 400:
                raise ReaderError(f"HTTP {response.status} {response.reason}")
            return decode_body(body, content_type), content_type, response.status
        except (OSError, http.client.HTTPException, ReaderError) as exc:
            errors.append(f"{address}: {exc}")
        finally:
            connection.close()

    raise ReaderError("可信 DNS 地址均连接失败：" + "；".join(errors))


def direct_read(url: str) -> tuple[str, str, str, int]:
    source, content_type, status = fetch_url(url, DIRECT_TIMEOUT_SECONDS)
    if "html" in content_type.lower() or "<html" in source[:1000].lower():
        content, title = TextExtractor().extract(source)
    elif content_type.lower().startswith("text/"):
        content, title = source.strip(), ""
    else:
        raise ReaderError(f"直连返回了不支持的内容类型：{content_type}")
    if len(content) < 200:
        raise ReaderError(f"直连只提取到 {len(content)} 个字符，可能是脚本页或拦截页")
    return content, title, content_type, status


def is_scriptbin_script(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    return (
        (parsed.hostname or "").lower() in SCRIPTBIN_HOSTS
        and bool(re.fullmatch(r"/u/[^/]+/[^/]+/?", parsed.path))
    )


def hidden_input_value(source: str, name: str) -> str | None:
    from html.parser import HTMLParser

    class Parser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.value: str | None = None

        def handle_starttag(self, tag, attrs):
            if tag.lower() != "input" or self.value is not None:
                return
            values = dict(attrs)
            if values.get("name") == name:
                self.value = values.get("value")

    parser = Parser()
    parser.feed(source)
    return parser.value


def extract_scriptbin_main(source: str) -> tuple[str, str]:
    _full_content, title = TextExtractor().extract(source)
    main_match = re.search(r"<main\b[^>]*>(.*?)</main>", source, re.I | re.S)
    if not main_match:
        raise ReaderError("Scriptbin 页面中没有找到正文区域")
    content, _main_title = TextExtractor().extract(main_match.group(1))
    title = re.sub(r"\s+-\s+scriptbin\s*$", "", title, flags=re.I).strip()
    if not content or len(content) < 100:
        raise ReaderError(f"Scriptbin 正文只提取到 {len(content)} 个字符")
    return content, title


def scriptbin_confirmed_read(url: str) -> tuple[str, str, str, int]:
    """Read a public Scriptbin script after the user explicitly confirms the gate."""
    if not is_scriptbin_script(url):
        raise ReaderError("不是可识别的 Scriptbin 脚本链接")
    ensure_public_host(url)
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        SafeRedirectHandler(), urllib.request.HTTPCookieProcessor(cookie_jar)
    )
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
        "Accept-Encoding": "identity",
    }

    with opener.open(urllib.request.Request(url, headers=headers), timeout=DIRECT_TIMEOUT_SECONDS) as response:
        gate_url = normalize_url(response.geturl())
        ensure_public_host(gate_url)
        content_type = response.headers.get("Content-Type", "text/html")
        gate_source = decode_body(read_limited(response), content_type)
        status = response.status

    if "Agree to terms of access" not in gate_source:
        content, title = extract_scriptbin_main(gate_source)
        return content, title, content_type, status

    gate_host = (urllib.parse.urlsplit(gate_url).hostname or "").lower()
    if gate_host not in SCRIPTBIN_HOSTS:
        raise ReaderError("Scriptbin 年龄确认跳转到了意外域名")
    token = hidden_input_value(gate_source, "__RequestVerificationToken")
    if not token:
        raise ReaderError("Scriptbin 年龄确认页缺少防伪令牌")

    form_data = urllib.parse.urlencode({
        "agree": "Agree",
        "__RequestVerificationToken": token,
    }).encode("utf-8")
    post_headers = {
        **headers,
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://scriptbin.works",
        "Referer": gate_url,
    }
    request = urllib.request.Request(
        gate_url, data=form_data, headers=post_headers, method="POST"
    )
    with opener.open(request, timeout=DIRECT_TIMEOUT_SECONDS) as response:
        final_url = normalize_url(response.geturl())
        ensure_public_host(final_url)
        content_type = response.headers.get("Content-Type", "text/html")
        source = decode_body(read_limited(response), content_type)
        status = response.status

    if "Agree to terms of access" in source:
        raise ReaderError("Scriptbin 没有接受年龄确认，仍返回确认页")
    content, title = extract_scriptbin_main(source)
    return content, title, content_type, status


def reddit_post_id(url: str) -> str | None:
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host not in REDDIT_HOSTS:
        return None
    match = re.search(r"/comments/([a-z0-9]+)/", parsed.path, re.I)
    if match:
        return match.group(1).lower()
    if host == "redd.it":
        candidate = parsed.path.strip("/").split("/", 1)[0]
        if re.fullmatch(r"[a-z0-9]+", candidate, re.I):
            return candidate.lower()
    return None


def reddit_subreddit_name(url: str) -> str | None:
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host not in REDDIT_HOSTS or host == "redd.it":
        return None
    match = re.fullmatch(r"/r/([A-Za-z0-9_]+)/?", parsed.path)
    return match.group(1) if match else None


def reddit_is_home(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    return (
        (parsed.hostname or "").lower() in REDDIT_HOSTS - {"redd.it"}
        and parsed.path in {"", "/"}
    )


def reddit_search_params(url: str) -> tuple[str, str | None, int] | None:
    """Return query, optional subreddit and zero-based search page."""
    parsed = urllib.parse.urlsplit(url)
    if (parsed.hostname or "").lower() not in REDDIT_HOSTS - {"redd.it"}:
        return None

    subreddit: str | None = None
    if re.fullmatch(r"/search/?", parsed.path):
        pass
    else:
        match = re.fullmatch(r"/r/([A-Za-z0-9_]+)/search/?", parsed.path)
        if not match:
            return None
        subreddit = match.group(1)

    values = urllib.parse.parse_qs(parsed.query)
    query = str(values.get("q", [""])[0]).strip()
    try:
        page = int(values.get("wr_offset", ["0"])[0])
    except (TypeError, ValueError):
        page = 0
    return query, subreddit, min(max(page, 0), 100)


def _positive_int(value: str | None, default: int) -> int:
    try:
        parsed = int(value or "")
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def reddit_listing_url(
    subreddit: str,
    page: int,
    *,
    before: int | None = None,
    after: int | None = None,
) -> str:
    values: dict[str, str | int] = {"wr_page": page}
    if before is not None:
        values.update({"wr_direction": "next", "wr_before": before})
    if after is not None:
        values.update({"wr_direction": "prev", "wr_after": after})
    return (
        f"https://www.reddit.com/r/{subreddit}/?"
        + urllib.parse.urlencode(values)
    )


def reddit_search_url(query: str, subreddit: str | None, page: int) -> str:
    values = {"q": query, "wr_offset": max(page, 0)}
    if subreddit:
        values["restrict_sr"] = "1"
        path = f"/r/{subreddit}/search/"
    else:
        path = "/search/"
    return "https://www.reddit.com" + path + "?" + urllib.parse.urlencode(values)


def reddit_archive_search_url(
    query: str,
    subreddit: str,
    page: int,
    *,
    before: int | None = None,
    after: int | None = None,
) -> str:
    values: dict[str, str | int] = {
        "q": query,
        "restrict_sr": "1",
        "wr_page": page,
    }
    if before is not None:
        values.update({"wr_direction": "next", "wr_before": before})
    if after is not None:
        values.update({"wr_direction": "prev", "wr_after": after})
    return (
        f"https://www.reddit.com/r/{subreddit}/search/?"
        + urllib.parse.urlencode(values)
    )


class BraveRedditResultExtractor:
    """Extract direct Reddit result anchors from Brave's server-rendered HTML."""

    def __init__(self) -> None:
        from html.parser import HTMLParser

        outer = self

        class Parser(HTMLParser):
            def __init__(self) -> None:
                super().__init__(convert_charrefs=True)
                self.active_url: str | None = None
                self.parts: list[str] = []
                self.results: list[ContentLink] = []
                self.seen: set[str] = set()

            def handle_starttag(self, tag, attrs):
                if tag.lower() != "a" or self.active_url:
                    return
                href = dict(attrs).get("href", "")
                try:
                    candidate = normalize_url(html.unescape(href))
                except ReaderError:
                    return
                parsed = urllib.parse.urlsplit(candidate)
                if (parsed.hostname or "").lower() not in REDDIT_HOSTS:
                    return
                if not reddit_post_id(candidate):
                    return
                self.active_url = urllib.parse.urlunsplit(
                    ("https", "www.reddit.com", parsed.path, "", "")
                )
                self.parts = []

            def handle_data(self, data):
                if self.active_url:
                    value = re.sub(r"\s+", " ", data).strip()
                    if value:
                        self.parts.append(value)

            def handle_endtag(self, tag):
                if tag.lower() != "a" or not self.active_url:
                    return
                title = re.sub(r"\s+", " ", " ".join(self.parts)).strip()
                url = self.active_url
                self.active_url = None
                self.parts = []
                if not title or url in self.seen:
                    return
                title = clean_reddit_search_title(title)
                if len(title) > 240:
                    title = title[:237].rstrip() + "…"
                self.seen.add(url)
                self.results.append(ContentLink(title=title, url=url))

        self.parser = Parser()
        self.outer = outer

    def extract(self, source: str, limit: int = 20) -> list[ContentLink]:
        self.parser.feed(source)
        return self.parser.results[:limit]


def clean_reddit_search_title(title: str) -> str:
    value = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", title)
    value = re.sub(r"\s+", " ", value).strip(" []")
    reddit_title = re.search(
        r"r/[A-Za-z0-9_]+\s+on Reddit:\s*(.+)$", value, re.I
    )
    if reddit_title:
        return reddit_title.group(1).strip()
    breadcrumb_title = re.search(
        r"^Reddit\s+reddit\.com\s+›\s+r\s+›\s+[A-Za-z0-9_]+\s+›\s+"
        r"comments\s+›\s+[A-Za-z0-9]+\s+›\s+\S+\s+(.+)$",
        value,
        re.I,
    )
    return breadcrumb_title.group(1).strip() if breadcrumb_title else value


def extract_reddit_markdown_results(
    content: str, limit: int = 20
) -> list[ContentLink]:
    """Extract Reddit post links from a remote-reader rendering of search results."""
    pattern = re.compile(
        r"\[([^\n]{1,2400}?)\]\((https://www\.reddit\.com/r/"
        r"[A-Za-z0-9_]+/comments/[A-Za-z0-9]+/[^)\s]*)\)",
        re.I,
    )
    results: list[ContentLink] = []
    seen: set[str] = set()
    for match in pattern.finditer(content):
        parsed = urllib.parse.urlsplit(html.unescape(match.group(2)))
        url = urllib.parse.urlunsplit(("https", "www.reddit.com", parsed.path, "", ""))
        if url in seen:
            continue
        title = clean_reddit_search_title(html.unescape(match.group(1)))
        if not title:
            continue
        if len(title) > 240:
            title = title[:237].rstrip() + "…"
        seen.add(url)
        results.append(ContentLink(title=title, url=url))
        if len(results) >= limit:
            break
    return results


def reddit_archive_search_read(
    url: str,
    query: str,
    subreddit: str,
    *,
    inferred_from: str | None = None,
) -> tuple[str, str, str, int]:
    """Search title and selftext inside one subreddit through Arctic Shift."""
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    page = _positive_int(values.get("wr_page", ["1"])[0], 1)
    direction = values.get("wr_direction", [""])[0]
    api_values: dict[str, str | int] = {
        "subreddit": subreddit,
        "query": query,
        "limit": REDDIT_SEARCH_PAGE_SIZE,
        "sort": "desc",
        "fields": (
            "id,title,author,score,num_comments,over_18,created_utc,subreddit"
        ),
    }
    if direction == "next":
        before = _positive_int(values.get("wr_before", [""])[0], 0)
        if before:
            api_values["before"] = before
    elif direction == "prev":
        after = _positive_int(values.get("wr_after", [""])[0], 0)
        if after:
            api_values["after"] = after
            api_values["sort"] = "asc"

    archive_url = (
        f"{REDDIT_ARCHIVE_BASE}/api/posts/search?"
        + urllib.parse.urlencode(api_values)
    )
    for attempt in range(2):
        try:
            source, _content_type, status = fetch_url(
                archive_url,
                ARCHIVE_TIMEOUT_SECONDS,
                user_agent=READER_USER_AGENT,
                accept="application/json",
            )
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 422 and attempt == 0:
                time.sleep(1)
                continue
            raise
    try:
        posts = json.loads(source).get("data", [])
    except (AttributeError, json.JSONDecodeError) as exc:
        raise ReaderError("Reddit 公开归档返回了无效搜索数据") from exc
    if not posts:
        raise ReaderError(f"公开归档在 r/{subreddit} 中没有找到“{query}”")
    if api_values["sort"] == "asc":
        posts.reverse()

    title = f"r/{subreddit} 搜索：{query} · 第 {page} 页"
    lines = [f"# {title}", "", f"搜索入口：{url}", ""]
    if inferred_from:
        lines.extend([
            "全站搜索通道当前不可用。",
            f"工具把“{inferred_from}”自动解释为：在 r/{subreddit} 中搜索“{query}”。",
            "以下不是 Reddit 全站结果。若推断不对，请在“社区”框中明确填写社区名。",
            "",
        ])
    lines.extend([
        "以下结果来自 Arctic Shift 公开归档中的标题与正文检索。",
        "",
        "## 搜索结果",
        "",
    ])

    item_number = 0
    for post in posts:
        if not isinstance(post, dict):
            continue
        post_title = re.sub(r"\s+", " ", str(post.get("title") or "")).strip()
        post_id = str(post.get("id") or "").strip()
        post_subreddit = str(post.get("subreddit") or subreddit).strip()
        if not post_title or not re.fullmatch(r"[A-Za-z0-9]+", post_id):
            continue
        item_number += 1
        post_url = f"https://www.reddit.com/r/{post_subreddit}/comments/{post_id}/"
        author = str(post.get("author") or "[unknown]").strip()
        score = post.get("score") if isinstance(post.get("score"), int) else "?"
        comments = (
            post.get("num_comments")
            if isinstance(post.get("num_comments"), int)
            else "?"
        )
        nsfw = " · NSFW" if post.get("over_18") else ""
        lines.extend([
            f"{item_number}. [{markdown_link_label(post_title)}]({post_url})",
            f"   u/{author} · {score} 分 · {comments} 条评论{nsfw}",
            "",
        ])
    if item_number == 0:
        raise ReaderError(f"公开归档在 r/{subreddit} 中没有找到可读结果")

    timestamps = [
        post.get("created_utc")
        for post in posts
        if isinstance(post, dict) and isinstance(post.get("created_utc"), int)
    ]
    lines.extend(["---", ""])
    if page > 1 and timestamps:
        lines.append(
            f"[← 上一页]({reddit_archive_search_url(query, subreddit, page - 1, after=max(timestamps) + 1)})"
        )
    if item_number >= REDDIT_SEARCH_PAGE_SIZE and timestamps:
        lines.append(
            f"[下一页 →]({reddit_archive_search_url(query, subreddit, page + 1, before=min(timestamps) - 1)})"
        )
    lines.extend(["", "数据来源：Arctic Shift 公开归档；结果可能不完整或有延迟。"])
    return "\n".join(lines).strip(), title, "text/markdown; charset=utf-8", status


def inferred_subreddit_search(query: str) -> tuple[str, str] | None:
    """Interpret `subreddit terms` only as a last-resort, explicitly labeled fallback."""
    match = re.fullmatch(r"(?:r/)?([A-Za-z0-9_]{2,21})\s+(.+)", query.strip())
    if not match or not match.group(2).strip():
        return None
    return match.group(1), match.group(2).strip()


def reddit_browser_read(url: str) -> tuple[str, str, str, int]:
    """Serve a small Reddit home/search experience without loading reddit.com."""
    if reddit_is_home(url):
        title = "Reddit 只读首页"
        content = "\n".join([
            f"# {title}",
            "",
            "在上方的 Reddit 搜索框输入关键词，可搜索整个 Reddit；也可以指定一个社区。",
            "",
            "你还可以在网址框中直接输入社区地址，例如：",
            "",
            "- [r/DeepSeek](https://www.reddit.com/r/DeepSeek/)",
            "- [r/programming](https://www.reddit.com/r/programming/)",
            "",
            "这是只读入口：列表、搜索、翻页和帖子正文会留在当前工具中，不加载 Reddit 前端。",
        ])
        return content, title, "text/markdown; charset=utf-8", 200

    params = reddit_search_params(url)
    if not params:
        raise ReaderError("不是可识别的 Reddit 首页或搜索链接")
    query, subreddit, page = params
    if not query:
        raise ReaderError("请输入 Reddit 搜索关键词")

    archive_search_error: Exception | None = None
    if subreddit:
        try:
            return reddit_archive_search_read(url, query, subreddit)
        except Exception as exc:
            archive_search_error = exc

    site = "reddit.com" + (f"/r/{subreddit}" if subreddit else "")
    brave_query = f"site:{site} {query}"
    brave_url = "https://search.brave.com/search?" + urllib.parse.urlencode({
        "q": brave_query,
        "offset": page,
        "spellcheck": "0",
        "source": "web",
    })
    direct_search_error: Exception | None = None
    try:
        brave_addresses = resolve_public_ipv4_via_doh("search.brave.com")
        source, _content_type, status = fetch_https_via_addresses(
            brave_url,
            brave_addresses,
            ARCHIVE_TIMEOUT_SECONDS,
            USER_AGENT,
            "text/html",
        )
    except Exception as trusted_dns_error:
        try:
            source, _content_type, status = fetch_url(
                brave_url,
                ARCHIVE_TIMEOUT_SECONDS,
                user_agent=USER_AGENT,
                accept="text/html",
            )
        except Exception as system_dns_error:
            direct_search_error = ReaderError(
                "直连搜索失败（可信 DNS："
                f"{trusted_dns_error}；系统 DNS：{system_dns_error}）"
            )

    if direct_search_error is None:
        results = BraveRedditResultExtractor().extract(source)
        search_channel = "Brave 公开网页检索"
    else:
        try:
            source, _reader_title, _content_type, status = remote_reader_read(brave_url)
            results = extract_reddit_markdown_results(source)
            search_channel = "Brave 公开网页检索（远程备用通道）"
        except Exception as remote_search_error:
            inferred = inferred_subreddit_search(query) if not subreddit else None
            if inferred:
                inferred_subreddit, inferred_query = inferred
                inferred_url = reddit_archive_search_url(
                    inferred_query, inferred_subreddit, 1
                )
                try:
                    return reddit_archive_search_read(
                        inferred_url,
                        inferred_query,
                        inferred_subreddit,
                        inferred_from=query,
                    )
                except Exception as inferred_error:
                    archive_search_error = inferred_error
            archive_detail = (
                f"；社区归档检索：{describe_error(archive_search_error)}"
                if archive_search_error
                else ""
            )
            raise ReaderError(
                f"Reddit 搜索失败：{direct_search_error}；"
                f"远程备用通道：{describe_error(remote_search_error)}"
                f"{archive_detail}"
            ) from remote_search_error
    if not results:
        inferred = inferred_subreddit_search(query) if not subreddit else None
        if inferred:
            inferred_subreddit, inferred_query = inferred
            try:
                return reddit_archive_search_read(
                    reddit_archive_search_url(inferred_query, inferred_subreddit, 1),
                    inferred_query,
                    inferred_subreddit,
                    inferred_from=query,
                )
            except Exception as exc:
                archive_search_error = exc
        scope = f"r/{subreddit}" if subreddit else "Reddit"
        detail = (
            f"；社区归档检索：{describe_error(archive_search_error)}"
            if archive_search_error
            else ""
        )
        raise ReaderError(f"没有找到 {scope} 中与“{query}”相关的公开帖子{detail}")

    scope = f"r/{subreddit}" if subreddit else "Reddit 全站"
    title = f"{scope} 搜索：{query} · 第 {page + 1} 页"
    lines = [
        f"# {title}",
        "",
        f"搜索入口：{url}",
        "",
        f"以下结果来自{search_channel}；点开后由本工具读取帖子归档。",
        "",
        "## 搜索结果",
        "",
    ]
    for number, result in enumerate(results, 1):
        lines.extend([
            f"{number}. [{markdown_link_label(result.title)}]({result.url})",
            "",
        ])

    lines.extend(["---", ""])
    if page > 0:
        lines.append(f"[← 上一页]({reddit_search_url(query, subreddit, page - 1)})")
    if len(results) >= 10:
        lines.append(f"[下一页 →]({reddit_search_url(query, subreddit, page + 1)})")
    return "\n".join(lines).strip(), title, "text/markdown; charset=utf-8", status


def reddit_archive_listing_read(
    url: str, subreddit: str
) -> tuple[str, str, str, int]:
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    page = _positive_int(values.get("wr_page", ["1"])[0], 1)
    direction = values.get("wr_direction", [""])[0]
    api_values: dict[str, str | int] = {
        "subreddit": subreddit,
        "limit": 25,
        "sort": "desc",
    }
    if direction == "next":
        before = _positive_int(values.get("wr_before", [""])[0], 0)
        if before:
            api_values["before"] = before
    elif direction == "prev":
        after = _positive_int(values.get("wr_after", [""])[0], 0)
        if after:
            api_values["after"] = after
            api_values["sort"] = "asc"
    query = urllib.parse.urlencode(api_values)
    source, _content_type, status = fetch_url(
        f"{REDDIT_ARCHIVE_BASE}/api/posts/search?{query}",
        ARCHIVE_TIMEOUT_SECONDS,
        user_agent=READER_USER_AGENT,
        accept="application/json",
    )
    try:
        posts = json.loads(source).get("data", [])
    except (AttributeError, json.JSONDecodeError) as exc:
        raise ReaderError("Reddit 公开归档返回了无效列表数据") from exc
    if not posts:
        raise ReaderError(f"Reddit 公开归档没有找到 r/{subreddit} 的帖子")
    if api_values["sort"] == "asc":
        posts.reverse()

    title = f"r/{subreddit} 帖子 · 第 {page} 页"
    lines = [
        f"# {title}",
        "",
        f"原始社区：{url}",
        "",
        "以下是公开归档中按时间倒序排列的帖子；不等同于 Reddit 的 Hot/Best 排序。",
        "",
        "## 帖子列表",
        "",
    ]
    item_number = 0
    for post in posts:
        if not isinstance(post, dict):
            continue
        post_title = re.sub(r"\s+", " ", str(post.get("title") or "")).strip()
        permalink = str(post.get("permalink") or "").strip()
        if not post_title or not permalink.startswith("/r/"):
            continue
        item_number += 1
        post_url = urllib.parse.urljoin("https://www.reddit.com", permalink)
        author = str(post.get("author") or "[unknown]").strip()
        score = post.get("score") if isinstance(post.get("score"), int) else "?"
        comments = (
            post.get("num_comments")
            if isinstance(post.get("num_comments"), int)
            else "?"
        )
        nsfw = " · NSFW" if post.get("over_18") else ""
        lines.extend([
            f"{item_number}. [{markdown_link_label(post_title)}]({post_url})",
            f"   u/{author} · {score} 分 · {comments} 条评论{nsfw}",
            "",
        ])

    if item_number == 0:
        raise ReaderError(f"Reddit 公开归档没有找到 r/{subreddit} 的可读帖子")

    timestamps = [
        post.get("created_utc")
        for post in posts
        if isinstance(post, dict) and isinstance(post.get("created_utc"), int)
    ]
    lines.extend(["---", ""])
    if page > 1 and timestamps:
        previous_url = reddit_listing_url(
            subreddit, page - 1, after=max(timestamps) + 1
        )
        lines.append(f"[← 上一页]({previous_url})")
    if item_number >= 25 and timestamps:
        next_url = reddit_listing_url(
            subreddit, page + 1, before=min(timestamps) - 1
        )
        lines.append(f"[下一页 →]({next_url})")
    lines.extend([
        "",
        "数据来源：Arctic Shift 公开归档；列表可能比 Reddit 当前页面稍有延迟。",
    ])
    return "\n".join(lines).strip(), title, "text/markdown; charset=utf-8", status


def reddit_archive_read(url: str) -> tuple[str, str, str, int]:
    """Read a Reddit post and available comments from the public Arctic Shift archive."""
    post_id = reddit_post_id(url)
    if not post_id:
        subreddit = reddit_subreddit_name(url)
        if subreddit:
            return reddit_archive_listing_read(url, subreddit)
        raise ReaderError("不是可识别的 Reddit 帖子或社区链接")

    post_query = urllib.parse.urlencode({"ids": post_id})
    source, _content_type, status = fetch_url(
        f"{REDDIT_ARCHIVE_BASE}/api/posts/ids?{post_query}",
        ARCHIVE_TIMEOUT_SECONDS,
        user_agent=READER_USER_AGENT,
        accept="application/json",
    )
    try:
        posts = json.loads(source).get("data", [])
    except (AttributeError, json.JSONDecodeError) as exc:
        raise ReaderError("Reddit 公开归档返回了无效数据") from exc
    if not posts:
        raise ReaderError("Reddit 公开归档尚未收录这篇帖子")

    post = posts[0]
    title = str(post.get("title") or f"Reddit 帖子 {post_id}").strip()
    subreddit = str(post.get("subreddit") or "").strip()
    author = str(post.get("author") or "[unknown]").strip()
    selftext = str(post.get("selftext") or "").strip()
    lines = [f"# {title}", ""]
    metadata = [f"作者：u/{author}"]
    if subreddit:
        metadata.append(f"社区：r/{subreddit}")
    if isinstance(post.get("score"), int):
        metadata.append(f"归档分数：{post['score']}")
    lines.extend([" · ".join(metadata), f"原始链接：{url}", ""])
    if selftext:
        lines.extend([selftext, ""])
    media_url = str(post.get("url_overridden_by_dest") or post.get("url") or "").strip()
    if media_url and media_url != url:
        lines.extend([f"媒体：{media_url}", ""])

    comment_query = urllib.parse.urlencode(
        {"link_id": post_id, "limit": 100, "sort": "asc"}
    )
    try:
        comment_source, _comment_type, _comment_status = fetch_url(
            f"{REDDIT_ARCHIVE_BASE}/api/comments/search?{comment_query}",
            ARCHIVE_TIMEOUT_SECONDS,
            user_agent=READER_USER_AGENT,
            accept="application/json",
        )
        comments = json.loads(comment_source).get("data", [])
    except Exception as exc:
        comments = []
        lines.extend(["## 评论", "", f"评论归档读取失败：{describe_error(exc)}", ""])

    readable_comments = [
        comment for comment in comments
        if isinstance(comment, dict) and str(comment.get("body") or "").strip()
    ]
    readable_comments.sort(key=lambda item: item.get("created_utc") or 0)
    if readable_comments:
        lines.extend([f"## 评论（公开归档，共 {len(readable_comments)} 条）", ""])
        for comment in readable_comments:
            comment_author = str(comment.get("author") or "[unknown]").strip()
            score = comment.get("score")
            score_text = f" · {score} 分" if isinstance(score, int) else ""
            body = str(comment.get("body") or "").strip()
            lines.extend([f"### u/{comment_author}{score_text}", "", body, ""])
    elif "## 评论" not in lines:
        lines.extend(["## 评论", "", "公开归档暂未收录评论。", ""])

    lines.extend([
        "---",
        "数据来源：Arctic Shift 公开归档；内容和分数可能比 Reddit 当前页面稍有延迟。",
    ])
    return "\n".join(lines).strip(), title, "text/markdown; charset=utf-8", status


def remote_reader_returned_block_page(content: str) -> bool:
    return bool(
        re.search(r"^Warning: Target URL returned error", content, re.MULTILINE)
        or "You've been blocked by network security" in content
        or "## whoa there, pardner!" in content
    )


def remote_reader_read(url: str) -> tuple[str, str, str, int]:
    # Jina Reader performs the remote fetch and returns readable Markdown.
    reader_url = "https://r.jina.ai/" + url
    try:
        addresses = resolve_public_ipv4_via_doh("r.jina.ai")
        source, content_type, status = fetch_https_via_addresses(
            reader_url,
            addresses,
            READER_TIMEOUT_SECONDS,
            READER_USER_AGENT,
            "text/plain",
        )
    except Exception as trusted_dns_error:
        try:
            source, content_type, status = fetch_url(
                reader_url,
                READER_TIMEOUT_SECONDS,
                validate_target=True,
                user_agent=READER_USER_AGENT,
                accept="text/plain",
            )
        except Exception as system_dns_error:
            raise ReaderError(
                "远程服务连接失败（可信 DNS："
                f"{trusted_dns_error}；系统 DNS：{system_dns_error}）"
            ) from system_dns_error
    content = source.strip()
    if len(content) < 100:
        raise ReaderError(f"备用通道只返回了 {len(content)} 个字符")
    if remote_reader_returned_block_page(content):
        raise ReaderError("目标网站拒绝了远程读取，返回了拦截页")
    title_match = re.search(r"^Title:\s*(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else ""
    return content, title, content_type, status


def describe_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code} {exc.reason}"
    if isinstance(exc, urllib.error.URLError):
        return f"连接失败：{exc.reason}"
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "连接超时"
    return str(exc) or exc.__class__.__name__


def read_web_content(
    raw_url: str,
    reddit_archive: Callable[[str], tuple[str, str, str, int]] = reddit_archive_read,
    reddit_browser: Callable[[str], tuple[str, str, str, int]] = reddit_browser_read,
    scriptbin: Callable[[str], tuple[str, str, str, int]] = scriptbin_confirmed_read,
    remote: Callable[[str], tuple[str, str, str, int]] = remote_reader_read,
    direct: Callable[[str], tuple[str, str, str, int]] = direct_read,
    adult_confirmed: bool = False,
) -> FetchResult:
    url = normalize_url(raw_url)
    attempts: list[Attempt] = []
    started = time.monotonic()

    readers: list[tuple[str, str, Callable]] = []
    if is_scriptbin_script(url):
        if not adult_confirmed:
            confirmation_content = "\n".join([
                "# Scriptbin 需要年龄确认",
                "",
                "该网站要求读者本人确认：",
                "",
                "- 已达到所在地阅读成人内容的法定年龄；",
                "- 内容是所有参与者均为成年人的虚构作品；",
                "- 不会向未达到法定年龄的人展示或传播这些内容。",
                "",
                "工具不会替你自动作出这项声明。若你符合条件并接受，请点击页面中的确认按钮。",
            ])
            return FetchResult(
                ok=True,
                source_url=url,
                route="scriptbin-confirmation",
                content=confirmation_content,
                title="Scriptbin 需要年龄确认",
                content_type="text/markdown; charset=utf-8",
                elapsed_ms=round((time.monotonic() - started) * 1000),
                links=[],
                attempts=[Attempt("Scriptbin 年龄确认", True, "等待本人确认", 0)],
                requires_confirmation=True,
            )
        readers.append(("scriptbin-direct", "Scriptbin 临时确认会话", scriptbin))
    elif reddit_post_id(url) or reddit_subreddit_name(url):
        readers.append(("reddit-archive", "Reddit 公开归档", reddit_archive))
    elif reddit_is_home(url) or reddit_search_params(url):
        readers.append(("reddit-browser", "Reddit 只读浏览", reddit_browser))
    if not is_scriptbin_script(url):
        readers.extend([
            ("remote-reader", "远程正文通道", remote),
            ("direct", "本机直连", direct),
        ])

    for route, label, reader in readers:
        attempt_started = time.monotonic()
        try:
            content, title, content_type, status = reader(url)
            attempt_ms = round((time.monotonic() - attempt_started) * 1000)
            attempts.append(Attempt(label, True, f"HTTP {status}，{len(content)} 字符", attempt_ms))
            return FetchResult(
                ok=True,
                source_url=url,
                route=route,
                content=content,
                title=title,
                content_type=content_type,
                elapsed_ms=round((time.monotonic() - started) * 1000),
                links=extract_content_links(content, url),
                attempts=attempts,
            )
        except Exception as exc:  # Each failure is reported before the next route.
            attempt_ms = round((time.monotonic() - attempt_started) * 1000)
            attempts.append(Attempt(label, False, describe_error(exc), attempt_ms))

    details = "；".join(f"{item.route}：{item.detail}" for item in attempts)
    raise ReaderError(f"所有读取链路都失败了。{details}")


class AppHandler(BaseHTTPRequestHandler):
    server_version = "WebReader/0.1"

    def log_message(self, format, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

    def send_bytes(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_bytes(status, "application/json; charset=utf-8", body)

    def do_GET(self):  # noqa: N802
        path = urllib.parse.urlsplit(self.path).path
        if path == "/":
            try:
                body = INDEX_FILE.read_bytes()
            except OSError as exc:
                self.send_json(500, {"ok": False, "error": str(exc)})
                return
            self.send_bytes(200, "text/html; charset=utf-8", body)
            return
        if path == "/health":
            self.send_json(200, {"ok": True})
            return
        self.send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self):  # noqa: N802
        if urllib.parse.urlsplit(self.path).path != "/api/read":
            self.send_json(404, {"ok": False, "error": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 16 * 1024:
                raise ReaderError("请求大小不合法")
            payload = json.loads(self.rfile.read(size))
            result = read_web_content(
                str(payload.get("url", "")),
                adult_confirmed=payload.get("adult_confirmed") is True,
            )
            self.send_json(200, result.to_dict())
        except (ReaderError, json.JSONDecodeError) as exc:
            self.send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": f"读取失败：{describe_error(exc)}"})


def existing_reader_is_healthy(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=1) as response:
            payload = json.loads(response.read(1024))
        return response.status == 200 and payload == {"ok": True}
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def run_server(host: str, port: int, open_browser: bool) -> None:
    url = f"http://{host}:{port}"
    try:
        server = ThreadingHTTPServer((host, port), AppHandler)
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
        if existing_reader_is_healthy(url):
            print(f"网页正文读取器已经在运行：{url}")
            if open_browser:
                webbrowser.open(url)
            return
        raise ReaderError(
            f"端口 {port} 已被其他程序占用。可改用：python3 app.py --port {port + 1}"
        ) from exc

    print(f"网页正文读取器已启动：{url}")
    print("按 Ctrl+C 停止。")
    if open_browser:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="本地网页正文读取器")
    parser.add_argument("--url", help="命令行读取一个网址，并把正文输出到 stdout")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true", help="启动服务时不自动打开浏览器")
    args = parser.parse_args()

    if args.url:
        try:
            result = read_web_content(args.url)
        except ReaderError as exc:
            print(f"错误：{exc}", file=sys.stderr)
            return 1
        print(result.content)
        print(
            f"\n[读取链路: {result.route}; 耗时: {result.elapsed_ms} ms]",
            file=sys.stderr,
        )
        return 0

    try:
        run_server(args.host, args.port, not args.no_browser)
    except (ReaderError, OSError) as exc:
        print(f"启动失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
