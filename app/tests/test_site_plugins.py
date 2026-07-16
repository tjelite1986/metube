import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from yt_dlp_plugins.extractor.mecloud_sites import (
    EromeAlbumIE,
    NuditokIE,
    NuditokUserIE,
    OnlytikIE,
    OnlytikUserIE,
    TikPornIE,
    TikPornProfileIE,
    XfreeIE,
    XfreeProfileIE,
    XxxfollowIE,
    XxxfollowProfileIE,
    _clean_title,
    _title_from,
)


class UrlMatchingTests(unittest.TestCase):
    def _check(self, ie, url, expected):
        self.assertEqual(bool(ie.suitable(url)), expected, f'{ie.__name__} vs {url}')

    def test_video_urls_route_to_video_extractors(self):
        self._check(NuditokIE, 'https://nuditok.com/@user/some-slug-RxE9', True)
        self._check(NuditokIE, 'https://nuditok.com/s/RxE9', True)
        self._check(OnlytikIE, 'https://onlytik.com/@user.name/Ab3xYz', True)
        self._check(TikPornIE, 'https://tik.porn/video/12345', True)
        self._check(XfreeIE, 'https://www.xfree.com/video?id=123456', True)
        self._check(XxxfollowIE, 'https://www.xxxfollow.com/creator/12345678-some-slug', True)
        self._check(EromeAlbumIE, 'https://www.erome.com/a/AbCd1234', True)

    def test_profile_urls_route_to_profile_extractors(self):
        self._check(NuditokUserIE, 'https://nuditok.com/@user', True)
        self._check(OnlytikUserIE, 'https://onlytik.com/@user.name', True)
        self._check(TikPornProfileIE, 'https://tik.porn/lillie-lucas.xuy', True)
        self._check(XfreeProfileIE, 'https://www.xfree.com/somehandle', True)
        self._check(XxxfollowProfileIE, 'https://www.xxxfollow.com/creator', True)

    def test_profile_extractors_reject_video_urls(self):
        self._check(NuditokUserIE, 'https://nuditok.com/@user/some-slug', False)
        self._check(OnlytikUserIE, 'https://onlytik.com/@user/Ab3xYz', False)
        self._check(TikPornProfileIE, 'https://tik.porn/video/12345', False)
        self._check(XfreeProfileIE, 'https://www.xfree.com/video?id=123456', False)
        self._check(XxxfollowProfileIE, 'https://www.xxxfollow.com/creator/12345678', False)

    def test_video_extractors_reject_profile_urls(self):
        self._check(NuditokIE, 'https://nuditok.com/@user', False)
        self._check(TikPornIE, 'https://tik.porn/lillie-lucas.xuy', False)

    def test_unrelated_urls_do_not_match(self):
        for ie in (NuditokIE, OnlytikIE, TikPornIE, XfreeIE, XxxfollowIE, EromeAlbumIE):
            self._check(ie, 'https://www.youtube.com/watch?v=abc', False)


class TitleHelperTests(unittest.TestCase):
    def test_clean_title_strips_hashtags_and_links(self):
        self.assertEqual(_clean_title('Nice clip #tag http://x.example **wow**'), 'Nice clip wow')

    def test_clean_title_empty_when_only_noise(self):
        self.assertEqual(_clean_title('#one #two'), '')

    def test_title_from_falls_back_to_tags_then_id(self):
        self.assertEqual(_title_from('', ['#one', '#two'], 'ab12'), 'one two ab12')
        self.assertEqual(_title_from('', [], 'ab12'), 'ab12')


class PluginDiscoveryTests(unittest.TestCase):
    def test_yt_dlp_resolves_plugin_by_key(self):
        import yt_dlp
        ydl = yt_dlp.YoutubeDL({'quiet': True})
        self.assertIsNotNone(ydl.get_info_extractor('Nuditok'))
        self.assertIsNotNone(ydl.get_info_extractor('EromeAlbum'))


if __name__ == '__main__':
    unittest.main()
