import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from downloaded_registry import DownloadedRegistry, media_key


class MediaKeyTests(unittest.TestCase):
    def test_youtube_variants_collapse_to_video_id(self):
        expected = 'yt:te12AU8sjBI'
        self.assertEqual(media_key('https://www.youtube.com/watch?v=te12AU8sjBI'), expected)
        self.assertEqual(media_key('https://music.youtube.com/watch?v=te12AU8sjBI&list=PL123'), expected)
        self.assertEqual(media_key('https://youtu.be/te12AU8sjBI'), expected)
        self.assertEqual(media_key('https://m.youtube.com/watch?v=te12AU8sjBI'), expected)
        self.assertEqual(media_key('https://www.youtube.com/shorts/te12AU8sjBI'), expected)

    def test_other_urls_drop_query_noise(self):
        self.assertEqual(
            media_key('https://soundcloud.com/forss/flickermood?utm_source=x#t=10'),
            'soundcloud.com/forss/flickermood',
        )

    def test_garbage_input(self):
        self.assertEqual(media_key(None), '')
        self.assertEqual(media_key(''), '')


class DownloadedRegistryTests(unittest.TestCase):
    def test_mark_unmark_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = DownloadedRegistry(os.path.join(tmp, 'downloaded_registry'))
            url = 'https://www.youtube.com/watch?v=abc123'
            self.assertFalse(reg.is_downloaded(url))
            reg.mark(url)
            # Any URL variant of the same video counts as downloaded.
            self.assertTrue(reg.is_downloaded('https://youtu.be/abc123'))
            reg.unmark('https://music.youtube.com/watch?v=abc123')
            self.assertFalse(reg.is_downloaded(url))

    def test_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'downloaded_registry')
            DownloadedRegistry(path).mark('https://example.com/video/1')
            self.assertTrue(DownloadedRegistry(path).is_downloaded('https://example.com/video/1'))

    def test_seed_only_writes_new_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'downloaded_registry')
            reg = DownloadedRegistry(path)
            reg.mark('https://example.com/a')
            first_mtime = os.path.getmtime(path)
            reg.seed(['https://example.com/a', None, ''])
            self.assertEqual(os.path.getmtime(path), first_mtime)
            reg.seed(['https://example.com/a', 'https://example.com/b'])
            self.assertTrue(reg.is_downloaded('https://example.com/b'))


if __name__ == '__main__':
    unittest.main()
