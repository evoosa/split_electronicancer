from spotify import PlaylistSplitter

if __name__ == '__main__':

    PLAYLIST_ID = "1x1h9eDSzKdpk5AA2DLJWb"
    GENRE = "techno"
    PLAYLIST_NAME = "i hate techno"

    ps = PlaylistSplitter()  # initiate
    tracks_file_path = ps.analyze_playlist(PLAYLIST_ID)  # get the track/genres mapping, save it to a CSV file
    genre_file_path = ps.create_playlist_of_genre(GENRE, PLAYLIST_NAME)  # create a playlist form a given genre

    print(f"tracks data are saved here: {tracks_file_path}")
    print(f"genre's tracks are saved here: {genre_file_path}")
