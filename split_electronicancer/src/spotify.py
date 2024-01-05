from utils import get_logger
import csv
import os

# LOG_PATH = os.path.join


class PlaylistSplitter:
    def __init__(self, src_playlist_id, genres):
        self.src_playlist_id = src_playlist_id
        self.genres = genres
        self.logger = get_logger()

    def get_playlist_tracks_genres(self):
        """ get the genres of all the tracks in a given playlist """
        pass

    def _save_to_csv(self, data: dict):
        """ save the given data to CSV """
        pass

    def _get_track_genres(self):
        """ get the genres of a track """
        pass

    def create_playlist_from_genre(self, genre):
        """ create a playlist with tracks of the given genre from the src playlist """
        pass
