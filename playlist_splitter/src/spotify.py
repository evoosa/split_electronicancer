from .utils import get_logger, save_to_csv
from .lastfm import get_lastfm_track_tags
import csv
import os
from datetime import datetime

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()
NOW = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


class PlaylistSplitter:
    def __init__(self, src_playlist_id, genres):
        # INPUTS
        self.playlist_id = src_playlist_id
        self.genres = genres

        # FILES
        self.log_file_path = f"playlist_splitter_{NOW}.log"
        self.playlist_data_file_path = f"playlist_splitter_{NOW}.csv"

        # STUFF
        self.logger = get_logger(self.log_file_path)
        self.client = PlaylistSplitter._get_sp_client()
        self.tracks_data = []
        self.failed_tracks = []

    @staticmethod
    def _get_sp_client():
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
        ))

    def get_playlist_tracks_genres(self):
        """ get the genres of all the tracks in a given playlist """
        offset = 0
        limit = 100  # Maximum limit per request
        while True:
            results = self.client.playlist_items(self.playlist_id, offset=offset, limit=limit)
            tracks = results['items']
            for track in tracks:
                try:
                    artist_name = track['track']['artists'][0]['name']
                    track_name = track['track']['name']
                    genres = self._get_track_genres(artist_name, track_name)
                    track_data = {
                        "track_id": track['track']['id'],
                        "genres": genres,
                        "artist_name": artist_name,
                        "track_name": track_name
                    }
                    self.tracks_data.append(track_data)
                except Exception as e:
                    self.logger.error(f"FAILED fetching for: \ntrack: {track}\nerror: {e}")
                    self.failed_tracks.append(track)
                    raise
            if not tracks:
                break  # No more tracks
            offset += limit

    def save_playlist_data_to_csv(self):
        """ save the playlist tracks data to a CSV file """
        with open(self.playlist_data_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["track_id", "genres", "track_name", "artist_name"])
            writer.writeheader()
            for row in self.tracks_data:
                writer.writerow(row)
        self.logger.info(f"saved CSV to: {self.playlist_data_file_path}")

    def _get_track_genres(self, artist_name: str, track_name: str):
        return get_lastfm_track_tags(artist_name, track_name, self.logger)

    def create_playlist_from_genre(self, genre):
        """ create a playlist with tracks of the given genre from the src playlist """
        pass
