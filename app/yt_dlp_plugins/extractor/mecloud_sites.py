"""yt-dlp extractor plugins for sites yt-dlp does not cover natively.

Ported from grabbit's JS extractors (github.com/tjelite1986/grabbit).
Fork-only: these are not part of upstream MeTube.
"""

import json
import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.networking import HEADRequest
from yt_dlp.utils import ExtractorError, clean_html, traverse_obj

_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
)


def _clean_title(text, maxlen=90):
    """Drop hashtags/links/markdown noise from a caption; '' if nothing left."""
    out = re.sub(r'#[\w\d_]+', '', str(text or ''), flags=re.UNICODE)
    out = re.sub(r'https?://\S+', '', out)
    out = re.sub(r'[#*_`~>|]+', ' ', out)
    out = re.sub(r'\s+', ' ', out).strip()[:maxlen].strip()
    return out if re.search(r'[\w\d]', out, flags=re.UNICODE) else ''


def _title_from(desc, tags, media_id):
    title = _clean_title(desc)
    if title:
        return title
    if tags:
        return ' '.join(t.lstrip('#') for t in tags) + f' {media_id}'
    return str(media_id)


def _hashtags(text):
    return [t.lower() for t in re.findall(r'#[\w\d_]+', str(text or ''), flags=re.UNICODE)]


class NuditokIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nuditok\.com/(?:@[^/?#]+/[^/?#]+|s/[^/?#]+)'
    _HEADERS = {'User-Agent': _UA, 'Referer': 'https://nuditok.com/'}

    def _real_extract(self, url):
        webpage = self._download_webpage(url, 'nuditok', headers={'User-Agent': _UA})
        # The stub mp4 id is bare alphanumerics; the real URL adds a suffix.
        media_id = self._search_regex(r'/videos/([A-Za-z0-9]+)\.mp4', webpage, 'video id')
        data = self._download_json(
            f'https://nuditok.com/api/v1/videos/{media_id}', media_id,
            headers={'User-Agent': _UA})['data']
        if not data.get('video_url'):
            raise ExtractorError('API response missing video_url', expected=True)
        desc = (data.get('description') or '').strip()
        tags = _hashtags(desc)
        return {
            'id': data.get('hash') or media_id,
            'title': _title_from(desc, tags, data.get('hash') or media_id),
            'description': desc,
            'url': data['video_url'],
            'ext': 'mp4',
            'uploader': data.get('username'),
            'thumbnail': data.get('cover_url') or data.get('preview_url'),
            'http_headers': self._HEADERS,
        }


class NuditokUserIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nuditok\.com/@(?P<id>[^/?#]+)/?$'

    def _real_extract(self, url):
        user = self._match_id(url)
        entries = []
        offset = 0
        for _ in range(200):
            data = self._download_json(
                f'https://nuditok.com/api/v1/users/{user}/videos', user,
                query={'offset': offset}, headers={'User-Agent': _UA},
                note=f'Fetching videos (offset {offset})')['data'] or {}
            videos = data.get('videos') or []
            for video in videos:
                if video.get('slug_url'):
                    entries.append(self.url_result(
                        f'https://nuditok.com{video["slug_url"]}', NuditokIE,
                        video_id=video.get('hash'),
                        video_title=_title_from(video.get('description'), _hashtags(video.get('description')), video.get('hash'))))
            offset += len(videos)
            if not data.get('has_more') or not videos:
                break
        return self.playlist_result(entries, user, user)


class OnlytikIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?onlytik\.com/@(?P<user>[A-Za-z0-9_.]+)/(?P<id>[A-Za-z0-9]+)'
    _HEADERS = {'User-Agent': _UA, 'Referer': 'https://onlytik.com/'}

    def _video_from_api(self, video, user):
        video_id = video['video_id']
        video_url = video.get('url') or f'https://cdn2.onlytik.com/videos/{video_id}.mp4'
        cdn_base = re.sub(r'/videos/.*$', '', video_url)
        desc = clean_html(video.get('desc') or '') or ''
        tags = _hashtags(desc)
        return {
            'id': video_id,
            'title': _title_from(desc, tags, video_id),
            'description': desc,
            'url': video_url,
            'ext': 'mp4',
            'uploader': user,
            'thumbnail': f'{cdn_base}/preview/{video_id}.jpg',
            'http_headers': self._HEADERS,
        }

    def _real_extract(self, url):
        user, video_id = self._match_valid_url(url).group('user', 'id')
        data = self._download_json(
            'https://onlytik.com/api/user', video_id, query={'uid': user},
            headers={'User-Agent': _UA}, fatal=False) or {}
        video = next((v for v in data.get('videos') or [] if v.get('video_id') == video_id), None)
        if video:
            return self._video_from_api(video, data.get('username') or user)
        # Clip not in the user listing: scrape the rendered page.
        webpage = self._download_webpage(url, video_id, headers={'User-Agent': _UA})
        mp4 = self._search_regex(
            r'(https?://cdn\d*\.onlytik\.com/videos/[A-Za-z0-9]+\.mp4)', webpage, 'video url')
        return self._video_from_api({'video_id': video_id, 'url': mp4, 'desc': ''}, user)


class OnlytikUserIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?onlytik\.com/@(?P<id>[A-Za-z0-9_.]+)/?$'

    def _real_extract(self, url):
        user = self._match_id(url)
        data = self._download_json(
            'https://onlytik.com/api/user', user, query={'uid': user},
            headers={'User-Agent': _UA})
        name = data.get('username') or user
        entries = [
            self.url_result(
                f'https://onlytik.com/@{name}/{video["video_id"]}', OnlytikIE,
                video_id=video['video_id'])
            for video in data.get('videos') or [] if video.get('video_id')]
        return self.playlist_result(entries, name, name, data.get('bio'))


class TikPornIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tik\.porn/video/(?P<id>\d+)'
    _HEADERS = {'User-Agent': _UA, 'Referer': 'https://tik.porn/'}

    @staticmethod
    def _meta_title(video, creator):
        title = traverse_obj(video, ('video_text', 'meta_title', 'default', 'text')) or ''
        title = re.sub(r'\s*\|\s*Tik\.?\s*Porn\s*$', '', title, flags=re.IGNORECASE)
        if creator:
            title = re.sub(r'^' + re.escape(creator) + r'\s+', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s+', ' ', title).strip()
        return title or video.get('action_name') or str(video.get('video_id'))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, headers={'User-Agent': _UA})
        next_data = self._search_nextjs_data(webpage, video_id)

        found = None

        def walk(obj):
            nonlocal found
            if found or not isinstance(obj, (dict, list)):
                return
            if isinstance(obj, dict):
                oid = str(obj['video_id']) if obj.get('video_id') is not None else None
                dl = obj.get('download_url') or obj.get('downloadLink') or traverse_obj(obj, ('source', 'src'))
                if oid == video_id and dl:
                    found = obj
                    return
                values = obj.values()
            else:
                values = obj
            for value in values:
                walk(value)

        walk(next_data)
        if not found:
            raise ExtractorError('could not find video on page', expected=True)
        creator = traverse_obj(found, ('pornstars', 0, 'name')) or traverse_obj(found, ('user', 'name')) or 'tikporn'
        return {
            'id': video_id,
            'title': self._meta_title(found, creator),
            'url': found.get('download_url') or found.get('downloadLink') or traverse_obj(found, ('source', 'src')),
            'ext': 'mp4',
            'uploader': creator,
            'thumbnail': found.get('poster_url') or found.get('poster'),
            'tags': [str(k).lower() for k in found.get('keywords') or []],
            'http_headers': self._HEADERS,
        }


class TikPornProfileIE(InfoExtractor):
    # Model pages look like /<slug>.<entropy> (e.g. /lillie-lucas.xuy).
    _VALID_URL = r'https?://(?:www\.)?tik\.porn/(?P<id>[A-Za-z0-9-]+\.[A-Za-z0-9]+)/?$'

    def _real_extract(self, url):
        slug = self._match_id(url)
        webpage = self._download_webpage(url, slug, headers={'User-Agent': _UA})
        profile = traverse_obj(
            self._search_nextjs_data(webpage, slug), ('props', 'pageProps', 'profile'))
        if not profile or not profile.get('id') or not profile.get('type'):
            raise ExtractorError('no profile found on page', expected=True)
        ptype = profile['type']
        creator = profile.get('name') or slug
        entries = []
        offset, limit = 0, 60
        for _ in range(50):
            page = self._download_json(
                f'https://apiv2.tik.porn/get{ptype}videos', slug,
                query={f'{ptype}id': profile['id'], 'limit': limit, 'offset': offset, 'sort': 'recent'},
                headers={'User-Agent': _UA}, fatal=False,
                note=f'Fetching videos (offset {offset})')
            content = traverse_obj(page, ('data', 'videos', 'content')) or []
            for video in content:
                if video.get('video_id'):
                    entries.append(self.url_result(
                        f'https://tik.porn/video/{video["video_id"]}', TikPornIE,
                        video_id=str(video['video_id'])))
            offset += len(content)
            if len(content) < limit:
                break
        return self.playlist_result(entries, slug, creator)


class XfreeIE(InfoExtractor):
    # Cloudflare TLS-gates the pages (impersonation required); the CDN is open.
    _VALID_URL = r'https?://(?:www\.)?xfree\.com/video\?id=(?P<id>\d+)'
    _HEADERS = {'User-Agent': _UA, 'Referer': 'https://www.xfree.com/'}

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, impersonate=True)
        mp4 = self._search_regex(
            r'(https://cdn\.xfree\.com/[^"\\ )]+\.mp4)', webpage, 'video url')
        og_title = self._og_search_title(webpage, default='') or ''
        handle = self._search_regex(r'@([A-Za-z0-9_.]+)', og_title, 'handle', default='xfree')
        caption = re.split(r'\s*[-–—]\s*@[A-Za-z0-9_.]', og_title)[0]
        caption = re.sub(r'@[A-Za-z0-9_.]+[\'’]?s?\s+Sex\s+Reel[\s\S]*$', '', caption, flags=re.IGNORECASE)
        caption = re.sub(r'\s*[-–—]?\s*On xfree\.com[\s\S]*$', '', caption, flags=re.IGNORECASE).strip()
        if caption.startswith('@'):
            caption = ''
        return {
            'id': video_id,
            'title': caption or video_id,
            'url': mp4,
            'ext': 'mp4',
            'uploader': handle,
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'http_headers': self._HEADERS,
        }


class XfreeProfileIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?xfree\.com/(?P<id>[A-Za-z0-9_.-]+)/?$'

    @classmethod
    def suitable(cls, url):
        return super().suitable(url) and not re.search(r'/video($|\?)', url)

    def _real_extract(self, url):
        handle = self._match_id(url)
        webpage = self._download_webpage(url, handle, impersonate=True)
        # Only the SSR'd first batch is reachable; the rest hides behind a
        # Cloudflare-challenged XHR.
        ids = sorted(set(re.findall(r'id=(\d{5,})', webpage)))
        if not ids:
            raise ExtractorError('no videos found on this profile page', expected=True)
        entries = [
            self.url_result(f'https://www.xfree.com/video?id={vid}', XfreeIE, video_id=vid)
            for vid in ids]
        return self.playlist_result(entries, handle, handle)


class XxxfollowIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?xxxfollow\.com/(?P<user>[A-Za-z0-9_.-]+)/(?P<id>\d+)'
    _HEADERS = {'User-Agent': _UA, 'Referer': 'https://www.xxxfollow.com/'}

    def _formats_for(self, userdir, userid, media_id):
        base = f'https://www.xxxfollow.com/media/fans/post_public/{userdir}/{userid}/{media_id}'
        formats = []
        # Not every post has every variant; keep only those that answer a HEAD.
        for suffix, format_id, quality in (('_fhd', 'fhd', 2), ('', 'default', 1), ('_sd', 'sd', 0)):
            candidate = f'{base}{suffix}.mp4'
            if self._request_webpage(
                    HEADRequest(candidate), media_id, fatal=False,
                    headers=self._HEADERS, note=f'Checking {format_id} variant'):
                formats.append({
                    'url': candidate, 'format_id': format_id, 'quality': quality,
                    'ext': 'mp4', 'http_headers': self._HEADERS,
                })
        if not formats:
            raise ExtractorError('no downloadable variant found', expected=True)
        return formats

    def _real_extract(self, url):
        user, post_id = self._match_valid_url(url).group('user', 'id')
        webpage = self._download_webpage(url, post_id, headers={'User-Agent': _UA})
        userdir, userid, media_id = self._search_regex(
            r'post_public/(\d+)/([\d-]+)/(\d+)(?:_fhd|_sd)?\.(?:mp4|webp|jpg)',
            webpage, 'media path', group=(1, 2, 3))
        og_title = self._og_search_title(webpage, default='') or ''
        title = re.sub(r'\s+(by|Starring)\s+[^|]*$', '', og_title, flags=re.IGNORECASE).strip()
        return {
            'id': media_id,
            'title': title or media_id,
            'uploader': user,
            'thumbnail': f'https://www.xxxfollow.com/media/fans/post_public/{userdir}/{userid}/{media_id}_small.webp',
            'formats': self._formats_for(userdir, userid, media_id),
        }


class XxxfollowProfileIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?xxxfollow\.com/(?P<id>[A-Za-z0-9_.-]+)/?$'

    def _real_extract(self, url):
        user = self._match_id(url)
        entries = []
        seen = set()
        for page in range(1, 101):
            webpage = self._download_webpage(
                f'https://www.xxxfollow.com/{user}', user, query={'page': page},
                headers={'User-Agent': _UA}, note=f'Fetching page {page}', fatal=False)
            if not webpage:
                break
            added = 0
            for title, userdir, userid, media_id in re.findall(
                    r'alt="([^"]+?)\s+by\s+[^"]*?"[^>]*?post_public/(\d+)/([\d-]+)/(\d+)_small', webpage):
                if media_id in seen:
                    continue
                seen.add(media_id)
                entries.append({
                    '_type': 'url',
                    'url': f'https://www.xxxfollow.com/{user}/{media_id}',
                    'ie_key': 'Xxxfollow',
                    'id': media_id,
                    'title': clean_html(title).strip(),
                })
                added += 1
            if not added:
                break
        if not entries:
            raise ExtractorError('no videos found for this profile', expected=True)
        return self.playlist_result(entries, user, user)


class EromeAlbumIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?erome\.com/a/(?P<id>[A-Za-z0-9]+)'
    _HEADERS = {'User-Agent': _UA, 'Referer': 'https://www.erome.com/'}

    def _real_extract(self, url):
        album_id = self._match_id(url)
        webpage = self._download_webpage(url, album_id, headers={'User-Agent': _UA})
        uploader = re.sub(
            r'\s*-\s*(Porn Videos.*|EroMe)\s*$', '',
            self._html_extract_title(webpage) or '', flags=re.IGNORECASE).strip() or 'erome'
        entries = []
        seen = set()
        # Each media-group block is one item: a <source> mp4 (video) or a
        # `.img` data-src (full image). The CDN 403s without a Referer.
        for block in webpage.split('<div class="media-group"')[1:]:
            video = re.search(r'<source[^>]+src="(https://[^"]+\.mp4)"', block)
            image = None if video else re.search(r'<div class="img"\s+data-src="(https://[^"]+)"', block)
            media_url = (video or image) and (video or image).group(1)
            if not media_url or media_url in seen:
                continue
            seen.add(media_url)
            base = media_url.split('?')[0].rsplit('/', 1)[-1]
            media_id = re.sub(r'_\d+p$', '', re.sub(r'\.[a-z0-9]+$', '', base, flags=re.IGNORECASE)) or 'item'
            poster = re.search(r'poster="([^"]+)"', block)
            entry = {
                'id': media_id,
                'title': media_id,
                'url': media_url,
                'uploader': uploader,
                'http_headers': self._HEADERS,
            }
            if video:
                entry.update({'ext': 'mp4', 'thumbnail': poster and poster.group(1)})
            else:
                ext = re.search(r'\.([a-z0-9]+)$', media_url.split('?')[0], flags=re.IGNORECASE)
                entry.update({'ext': (ext.group(1).lower() if ext else 'jpg'), 'vcodec': 'none'})
            entries.append(entry)
        if not entries:
            raise ExtractorError('No media found in this erome album', expected=True)
        return self.playlist_result(entries, album_id, uploader)
