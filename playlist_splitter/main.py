from spotify import PlaylistSplitter

if __name__ == '__main__':
    ELECTRONICANCER_ID = "5gLflvThEu19nx7ZoEjGr2"
    GENRE = "house"
    PLAYLIST_NAME = "i hate house music"

    ps = PlaylistSplitter(ELECTRONICANCER_ID)  # initiate
    ps.get_playlist_tracks_genres()  # get the track/genres mapping
    ps.create_playlist_of_genre(PLAYLIST_NAME, GENRE)
