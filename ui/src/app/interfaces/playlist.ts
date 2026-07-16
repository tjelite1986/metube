export interface PlaylistItem {
  id: string | null;
  title: string;
  url: string;
  duration: number | null;
  thumbnail: string | null;
  channel: string | null;
  downloaded: boolean;
  // Client-side selection state for the playlist browser.
  selected?: boolean;
}

export interface PlaylistProbe {
  status: string;
  msg?: string;
  is_playlist?: boolean;
  title?: string | null;
  count?: number;
  truncated?: boolean;
  items?: PlaylistItem[];
}
