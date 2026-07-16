"""Registry of source URLs that have already been downloaded.

Unlike the completed list (which the user clears), this is an unbounded
dedup index. The playlist browser checks entries against it so already
downloaded items can be badged, hidden, and skipped, and the user can
flip a mark manually for items obtained some other way.
"""

import logging
import re
import time
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from state_store import AtomicJsonStore

log = logging.getLogger('downloaded_registry')


def media_key(url: Any) -> str:
    """Stable identity for a media URL: YouTube variants (www./music./m./
    youtu.be/shorts) collapse to the video id; other URLs drop query/hash
    noise.
    """
    if not url:
        return ''
    try:
        u = urlparse(str(url))
        host = re.sub(r'^(www|music|m)\.', '', u.hostname or '')
        if host in ('youtube.com', 'youtu.be'):
            if host == 'youtu.be':
                video_id: Optional[str] = next((p for p in u.path.split('/') if p), None)
            else:
                video_id = (parse_qs(u.query).get('v') or [None])[0] \
                    or next((p for p in reversed(u.path.split('/')) if p), None)
            if video_id:
                return f'yt:{video_id}'
        return f'{host}{u.path}'
    except (ValueError, AttributeError):
        return str(url or '')


class DownloadedRegistry:
    def __init__(self, path: str):
        self._store = AtomicJsonStore(path, kind='downloaded_registry')
        payload = self._store.load()
        entries = payload.get('entries') if payload else None
        self._entries: dict[str, Any] = entries if isinstance(entries, dict) else {}

    def _save(self) -> None:
        try:
            self._store.save({'entries': self._entries})
        except OSError as exc:
            log.warning('downloaded registry write failed: %s', exc)

    def mark(self, url: Any) -> None:
        if not url:
            return
        self._entries[media_key(url)] = {'at': int(time.time())}
        self._save()

    def unmark(self, url: Any) -> None:
        if self._entries.pop(media_key(url), None) is not None:
            self._save()

    def is_downloaded(self, url: Any) -> bool:
        return bool(url) and media_key(url) in self._entries

    def seed(self, urls) -> None:
        """Mark many URLs at once (e.g. finished downloads found at startup),
        writing the file only when something new was added.
        """
        added = False
        for url in urls:
            if url:
                key = media_key(url)
                if key not in self._entries:
                    self._entries[key] = {'at': int(time.time())}
                    added = True
        if added:
            self._save()
