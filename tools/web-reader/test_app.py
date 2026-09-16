import unittest
from unittest.mock import patch

from app import (
    BraveRedditResultExtractor,
    ReaderError,
    TextExtractor,
    extract_content_links,
    extract_reddit_markdown_results,
    extract_scriptbin_main,
    clean_reddit_search_title,
    inferred_subreddit_search,
    hidden_input_value,
    is_scriptbin_script,
    normalize_url,
    read_web_content,
    reddit_archive_listing_read,
    reddit_archive_search_read,
    reddit_browser_read,
    reddit_is_home,
    reddit_post_id,
    reddit_search_params,
    reddit_subreddit_name,
    remote_reader_returned_block_page,
)


class UrlTests(unittest.TestCase):
    def test_adds_https_scheme(self):
        self.assertEqual(normalize_url("example.com/a"), "https://example.com/a")

    def test_rejects_unsafe_schemes_and_localhost(self):
        for value in (
            "file:///etc/passwd",
            "ftp://example.com/a",
            "http://localhost:3000",
            "http://127.0.0.1/private",
            "http://192.168.1.2/private",
        ):
            with self.subTest(value=value), self.assertRaises(ReaderError):
                normalize_url(value)

    def test_extracts_reddit_post_id(self):
        self.assertEqual(
            reddit_post_id("https://www.reddit.com/r/test/comments/1vnpt5n/title/"),
            "1vnpt5n",
        )
        self.assertEqual(reddit_post_id("https://redd.it/1vnpt5n"), "1vnpt5n")
        self.assertIsNone(reddit_post_id("https://example.com/comments/1vnpt5n/"))

    def test_extracts_reddit_subreddit_name(self):
        self.assertEqual(reddit_subreddit_name("https://www.reddit.com/r/milf/"), "milf")
        self.assertIsNone(
            reddit_subreddit_name("https://www.reddit.com/r/milf/comments/abc/title/")
        )

    def test_recognizes_reddit_home_and_search(self):
        self.assertTrue(reddit_is_home("https://www.reddit.com/"))
        self.assertEqual(
            reddit_search_params(
                "https://www.reddit.com/r/DeepSeek/search/?q=harness&wr_offset=2"
            ),
            ("harness", "DeepSeek", 2),
        )
        self.assertIsNone(reddit_search_params("https://www.reddit.com/r/DeepSeek/"))

    def test_infers_subreddit_and_remaining_query(self):
        self.assertEqual(inferred_subreddit_search("milf ruined"), ("milf", "ruined"))
        self.assertEqual(
            inferred_subreddit_search("r/DeepSeek coding harness"),
            ("DeepSeek", "coding harness"),
        )
        self.assertIsNone(inferred_subreddit_search("oneword"))

    def test_recognizes_scriptbin_script(self):
        self.assertTrue(is_scriptbin_script(
            "https://scriptbin.works/u/writer/example-script"
        ))
        self.assertFalse(is_scriptbin_script("https://scriptbin.works/about"))


class ExtractorTests(unittest.TestCase):
    def test_extracts_visible_text_and_title(self):
        source = """
        <html><head><title>Example title</title><style>.x{}</style></head>
        <body><nav>Navigation</nav><main><h1>Hello</h1><p>Useful <b>text</b>.</p></main>
        <script>alert('hidden')</script></body></html>
        """
        text, title = TextExtractor().extract(source)
        self.assertEqual(title, "Example title")
        self.assertIn("Useful text", text)
        self.assertNotIn("hidden", text)

    def test_detects_remote_reader_block_page(self):
        self.assertTrue(
            remote_reader_returned_block_page(
                "Warning: Target URL returned error 403: Forbidden\n\n"
                "You've been blocked by network security."
            )
        )
        self.assertFalse(remote_reader_returned_block_page("# A normal article\nUseful text"))

    def test_extracts_clickable_markdown_links(self):
        links = extract_content_links(
            "[First](https://example.com/one)\n"
            "![Image](https://example.com/image.png)\n"
            "[First again](https://example.com/one)\n"
            "[Second](https://example.com/two)",
            "https://example.com/",
        )
        self.assertEqual([item.title for item in links], ["First", "Second"])

    def test_marks_pagination_links(self):
        links = extract_content_links(
            "[下一页 →](https://www.reddit.com/r/test/?wr_page=2)",
            "https://www.reddit.com/r/test/",
        )
        self.assertEqual(links[0].kind, "navigation")

    def test_extracts_and_deduplicates_brave_reddit_results(self):
        source = """
        <a href="https://www.reddit.com/r/DeepSeek/comments/abc/a/">
          Reddit reddit.com › r/DeepSeek r/DeepSeek on Reddit: Useful title
        </a>
        <a href="https://www.reddit.com/r/DeepSeek/comments/abc/a/">duplicate</a>
        <a href="https://example.com/not-reddit">ignore</a>
        """
        results = BraveRedditResultExtractor().extract(source)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Useful title")

    def test_extracts_remote_reader_search_results(self):
        source = """
        [![Image](https://image.example/a.png) Reddit reddit.com › r/test r/test on Reddit: Useful result](https://www.reddit.com/r/test/comments/abc/useful_result/)
        [duplicate](https://www.reddit.com/r/test/comments/abc/useful_result/)
        """
        results = extract_reddit_markdown_results(source)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Useful result")

    def test_cleans_brave_breadcrumb_title(self):
        title = (
            "Reddit reddit.com › r › DeepSeek › comments › abc › post_slug "
            "A readable post title"
        )
        self.assertEqual(clean_reddit_search_title(title), "A readable post title")

    def test_extracts_scriptbin_token_and_main_content(self):
        source = """
        <html><head><title>A script - scriptbin</title></head><body>
        <nav>navigation</nav><main><h2>A script</h2><p>{body}</p></main>
        </body></html>
        """.format(body="useful text " * 20)
        content, title = extract_scriptbin_main(source)
        self.assertEqual(title, "A script")
        self.assertIn("useful text", content)
        self.assertNotIn("navigation", content)
        self.assertEqual(
            hidden_input_value(
                '<input name="__RequestVerificationToken" value="token-123">',
                "__RequestVerificationToken",
            ),
            "token-123",
        )

    def test_listing_builds_real_cursor_navigation(self):
        posts = [
            {
                "title": f"Post {number}",
                "permalink": f"/r/test/comments/id{number}/post/",
                "created_utc": 1000 - number,
                "author": "tester",
            }
            for number in range(25)
        ]
        with patch("app.fetch_url", return_value=(
            __import__("json").dumps({"data": posts}),
            "application/json",
            200,
        )) as mocked_fetch:
            content, title, _content_type, _status = reddit_archive_listing_read(
                "https://www.reddit.com/r/test/?wr_page=2&wr_direction=next&wr_before=900",
                "test",
            )
        self.assertIn("before=900", mocked_fetch.call_args.args[0])
        self.assertEqual(title, "r/test 帖子 · 第 2 页")
        self.assertIn("← 上一页", content)
        self.assertIn("下一页 →", content)

    def test_archive_search_uses_scope_query_and_cursor(self):
        posts = [
            {
                "title": f"Ruined post {number}",
                "id": f"id{number}",
                "subreddit": "milf",
                "created_utc": 1000 - number,
                "author": "tester",
            }
            for number in range(10)
        ]
        with patch("app.fetch_url", return_value=(
            __import__("json").dumps({"data": posts}),
            "application/json",
            200,
        )) as mocked_fetch:
            content, title, _content_type, _status = reddit_archive_search_read(
                "https://www.reddit.com/r/milf/search/?q=ruined&wr_page=1",
                "ruined",
                "milf",
                inferred_from="milf ruined",
            )
        requested_url = mocked_fetch.call_args.args[0]
        self.assertIn("subreddit=milf", requested_url)
        self.assertIn("query=ruined", requested_url)
        self.assertEqual(title, "r/milf 搜索：ruined · 第 1 页")
        self.assertIn("以下不是 Reddit 全站结果", content)
        self.assertIn("下一页 →", content)


class FallbackTests(unittest.TestCase):
    def test_scriptbin_requires_explicit_confirmation(self):
        remote_called = False

        def remote(_url):
            nonlocal remote_called
            remote_called = True
            return ("remote" * 100, "Remote", "text/plain", 200)

        result = read_web_content(
            "https://scriptbin.works/u/writer/example-script", remote=remote
        )
        self.assertEqual(result.route, "scriptbin-confirmation")
        self.assertTrue(result.requires_confirmation)
        self.assertFalse(remote_called)

    def test_confirmed_scriptbin_uses_temporary_session_reader(self):
        def scriptbin(_url):
            return ("actual script " * 30, "Actual script", "text/html", 200)

        result = read_web_content(
            "https://scriptbin.works/u/writer/example-script",
            scriptbin=scriptbin,
            adult_confirmed=True,
        )
        self.assertEqual(result.route, "scriptbin-direct")
        self.assertFalse(result.requires_confirmation)

    def test_global_search_infers_scoped_archive_when_search_engine_fails(self):
        posts = [{
            "id": "abc123",
            "subreddit": "milf",
            "title": "Ruined result",
            "created_utc": 1000,
            "author": "tester",
        }]

        def fetch_side_effect(url, *_args, **_kwargs):
            if "arctic-shift" in url:
                return (__import__("json").dumps({"data": posts}), "application/json", 200)
            raise ReaderError("HTTP 429 Too Many Requests")

        with (
            patch("app.resolve_public_ipv4_via_doh", side_effect=ReaderError("blocked")),
            patch("app.fetch_url", side_effect=fetch_side_effect),
            patch("app.remote_reader_read", side_effect=ReaderError("blocked")),
        ):
            content, title, _content_type, _status = reddit_browser_read(
                "https://www.reddit.com/search/?q=milf+ruined&wr_offset=0"
            )
        self.assertEqual(title, "r/milf 搜索：ruined · 第 1 页")
        self.assertIn("以下不是 Reddit 全站结果", content)
        self.assertIn("Ruined result", content)

    def test_reddit_uses_public_archive_first(self):
        remote_called = False

        def archive(_url):
            return ("reddit" * 100, "Archived", "text/markdown", 200)

        def remote(_url):
            nonlocal remote_called
            remote_called = True
            return ("remote" * 100, "Remote", "text/plain", 200)

        result = read_web_content(
            "https://www.reddit.com/r/test/comments/1vnpt5n/title/",
            reddit_archive=archive,
            remote=remote,
        )
        self.assertEqual(result.route, "reddit-archive")
        self.assertFalse(remote_called)
        self.assertEqual(result.attempts[0].route, "Reddit 公开归档")

    def test_reddit_listing_uses_public_archive_first(self):
        def archive(_url):
            return (
                "[Post](https://www.reddit.com/r/test/comments/abc/post/)",
                "r/test 最新帖子",
                "text/markdown",
                200,
            )

        result = read_web_content(
            "https://www.reddit.com/r/test/",
            reddit_archive=archive,
        )
        self.assertEqual(result.route, "reddit-archive")
        self.assertEqual(result.links[0].title, "Post")

    def test_reddit_home_uses_browser_route_first(self):
        remote_called = False

        def browser(_url):
            return ("Reddit home", "Reddit 只读首页", "text/markdown", 200)

        def remote(_url):
            nonlocal remote_called
            remote_called = True
            return ("remote" * 100, "Remote", "text/plain", 200)

        result = read_web_content(
            "https://www.reddit.com/", reddit_browser=browser, remote=remote
        )
        self.assertEqual(result.route, "reddit-browser")
        self.assertFalse(remote_called)

    def test_uses_remote_reader_first(self):
        direct_called = False

        def remote(_url):
            return ("x" * 300, "Remote", "text/plain", 200)

        def direct(_url):
            nonlocal direct_called
            direct_called = True
            return ("y" * 300, "Direct", "text/plain", 200)

        result = read_web_content("https://example.com", remote=remote, direct=direct)
        self.assertEqual(result.route, "remote-reader")
        self.assertFalse(direct_called)
        self.assertEqual(len(result.attempts), 1)

    def test_falls_back_to_direct_and_reports_both_attempts(self):
        def remote(_url):
            raise TimeoutError("timed out")

        def direct(_url):
            return ("x" * 300, "Direct", "text/plain", 200)

        result = read_web_content("https://example.com", remote=remote, direct=direct)
        self.assertEqual(result.route, "direct")
        self.assertFalse(result.attempts[0].ok)
        self.assertTrue(result.attempts[1].ok)


if __name__ == "__main__":
    unittest.main()
