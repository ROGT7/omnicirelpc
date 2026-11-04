import unittest
from unittest.mock import patch

from feedparser import FeedParserDict

from open_source_scraper import OpenSourceDataCollector


REUTERS_RSS = (
    'https://news.google.com/rss/search?q=site%3Areuters.com+world'
    '&hl=en-US&gl=US&ceid=US%3Aen'
)


class WorldNewsTests(unittest.TestCase):
    def feed(self, title):
        return FeedParserDict(entries=[FeedParserDict(
            title=title,
            summary='World news summary. ' * 20,
            link='https://news.google.com/rss/articles/test',
            published='Mon, 05 Oct 2026 10:00:00 GMT',
        )])

    @patch('open_source_scraper.time.sleep')
    @patch('open_source_scraper.feedparser.parse')
    def test_reuters_uses_public_indexed_feed(self, parse, sleep):
        parse.side_effect = lambda url: (
            self.feed('Reuters world report') if url == REUTERS_RSS
            else FeedParserDict(entries=[])
        )
        collector = OpenSourceDataCollector()
        with patch.object(collector.session, 'get', side_effect=AssertionError('No network')):
            news = collector.get_world_news()
        self.assertEqual(len(news), 1)
        self.assertEqual(news[0]['source'], 'Reuters via Google News')
        self.assertEqual(news[0]['category'], 'world')
        self.assertEqual(news[0]['title'], 'Reuters world report')
        parse.assert_any_call(REUTERS_RSS)
        self.assertNotIn('https://www.reuters.com/rssFeed/worldNews',
                         [call.args[0] for call in parse.call_args_list])

    @patch('open_source_scraper.time.sleep')
    @patch('open_source_scraper.feedparser.parse')
    def test_other_sources_survive_empty_reuters_feed(self, parse, sleep):
        parse.side_effect = lambda url: (
            FeedParserDict(entries=[]) if url == REUTERS_RSS
            else self.feed(url)
        )
        news = OpenSourceDataCollector().get_world_news()
        self.assertEqual({item['source'] for item in news}, {'BBC News', 'Google News'})
        self.assertEqual(parse.call_count, 3)


REDDIT_ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Reddit post</title>
<link href="https://www.reddit.com/r/test/comments/abc/post/"/>
<updated>2026-10-17T10:00:00+00:00</updated>
<content type="html">&lt;p&gt;Hello &lt;b&gt;world&lt;/b&gt;&lt;/p&gt;</content></entry>
</feed>"""


class FakeResponse:
    def __init__(self, status_code, content=b'', headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


class RedditTrendsTests(unittest.TestCase):
    @patch('open_source_scraper.time.sleep')
    def test_falls_back_to_public_rss_when_json_forbidden(self, sleep):
        collector = OpenSourceDataCollector()
        calls = []

        def fake_get(url, timeout=None):
            calls.append(url)
            return FakeResponse(403) if url.endswith('.json?limit=10') else FakeResponse(200, REDDIT_ATOM)

        with patch.object(collector.session, 'get', side_effect=fake_get):
            trends = collector.scrape_reddit_trends()
        self.assertEqual(len(trends), 4)
        self.assertEqual(trends[0]['title'], 'Reddit post')
        self.assertEqual(trends[0]['content'], 'Hello world')
        self.assertEqual(trends[0]['url'], 'https://www.reddit.com/r/test/comments/abc/post/')
        self.assertEqual(trends[0]['source'], 'Reddit r/worldnews')
        self.assertEqual(trends[0]['timestamp'].year, 2026)
        self.assertIn('https://www.reddit.com/r/worldnews/hot.rss?limit=10', calls)
        self.assertEqual(len([url for url in calls if url.endswith('.json?limit=10')]), 1)
        self.assertEqual(len(calls), 5)

    @patch('open_source_scraper.time.sleep')
    def test_returns_empty_when_rss_also_unavailable(self, sleep):
        collector = OpenSourceDataCollector()
        with patch.object(collector.session, 'get', return_value=FakeResponse(403)):
            self.assertEqual(collector.scrape_reddit_trends(), [])

    @patch('open_source_scraper.time.sleep')
    def test_stops_after_rss_rate_limit(self, sleep):
        collector = OpenSourceDataCollector()
        responses = [FakeResponse(403), FakeResponse(200, REDDIT_ATOM),
                     FakeResponse(429, headers={'Retry-After': '120'})]
        with patch.object(collector.session, 'get', side_effect=responses) as get:
            trends = collector.scrape_reddit_trends()
            self.assertEqual(len(trends), 1)
            self.assertEqual(get.call_count, 3)
            self.assertEqual(collector.scrape_reddit_trends(), [])
            self.assertEqual(get.call_count, 3)


    @patch('open_source_scraper.time.sleep')
    def test_respects_exhausted_rss_quota(self, sleep):
        collector = OpenSourceDataCollector()
        quota = {'x-ratelimit-remaining': '0.0', 'x-ratelimit-reset': '53'}
        responses = [FakeResponse(403), FakeResponse(200, REDDIT_ATOM, quota)]
        with patch.object(collector.session, 'get', side_effect=responses) as get:
            trends = collector.scrape_reddit_trends()
        self.assertEqual(len(trends), 1)
        self.assertEqual(get.call_count, 2)
        self.assertGreater(collector.reddit_block_until, 0)

if __name__ == '__main__':
    unittest.main()
