from bs4 import BeautifulSoup
import json
import requests
import sqlite3
import os
import matplotlib
import matplotlib.pyplot as plt

shazam_url = "https://shazam.p.rapidapi.com/charts/track"

headers = {
	"X-RapidAPI-Key": "a9414d258fmsh1fdef3a7910ac35p1dc953jsn624c88c2e27f",
	"X-RapidAPI-Host": "shazam.p.rapidapi.com"
}

def get_shazam_list():
    shazam_list = []
    start = 0
    for i in range(0,5):
        querystring = {"locale":"en-US","pageSize":"20","startFrom":{start}}
        response = requests.request("GET", shazam_url, headers=headers, params=querystring)
        data = response.text
        dict_list = json.loads(data)
        for i in range(0, 20):
            shazam_list.append((i + start + 1, dict_list['tracks'][i]['title'], dict_list['tracks'][i]['subtitle']))
        start += 20
    return shazam_list

def get_billboard_list():
    r = requests.get('https://www.billboard.com/charts/hot-100/')
    soup = BeautifulSoup(r.content, 'html.parser')
    result = soup.find_all('div', class_='o-chart-results-list-row-container')
    list_of_songs = []
    list_of_artists = []
    count = 1
    billboard_list = []
    for item in result:
        song_title = item.find('h3').text.strip()
        artist_name = item.find('h3').find_next('span').text.strip()
        list_of_songs.append(song_title)
        list_of_artists.append(artist_name)
        
    for i in range(0, 100):
        billboard_list.append((count, list_of_songs[i], list_of_artists[i]))
        count += 1
    return billboard_list

def get_itunes_list(songs_dict):
    itunes_list = []
    for key in songs_dict:
        url = f"https://itunes.apple.com/search?term={key}&entity=song"
        r = requests.get(url)
        if r:
            data = r.text
            dict_list = json.loads(data)
            if (dict_list['results']):
                song_id = songs_dict[key][0]
                time_ms = dict_list['results'][0]['trackTimeMillis']
                genre = dict_list['results'][0]['primaryGenreName']
                itunes_list.append((song_id, time_ms, genre))
    return itunes_list

def setUpDatabase(db_name):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+db_name)
    cur = conn.cursor()
    return cur, conn

def create_song_table(cur, conn):
    cur.execute("DROP TABLE IF EXISTS songs")
    cur.execute("CREATE TABLE songs(song_id INTEGER PRIMARY KEY, song_title TEXT, artist TEXT)")
    conn.commit()
    
def count_songs_in_songs(cur):
    cur.execute("SELECT * FROM songs")
    matches = cur.fetchall()
    return len(matches)
            
def add_songs(shazam_list, billboard_list, cur, conn):
    initial_count = count_songs_in_songs(cur)
    song_id = 101
    songs_dict = {}
    song_title_list = []
    # add each unique song into a dict before inputting that dict into a data base, songs cannot repeat but artists can
    for item in shazam_list:
        songs_dict[item[1]] = (song_id, item[2])
        song_title_list.append(item[1])
        song_id += 1
    for item in billboard_list:
        if item[1] not in songs_dict:
            songs_dict[item[1]] = (song_id, item[2])
            song_title_list.append(item[1])
            song_id += 1
    for i in range(initial_count, len(songs_dict)):
        cur.execute("INSERT OR IGNORE INTO songs (song_id, song_title, artist) VALUES (?,?,?)", (songs_dict[song_title_list[i]][0], song_title_list[i], songs_dict[song_title_list[i]][1]))
        count = count_songs_in_songs(cur)
        if count - initial_count >= 25:
            conn.commit()
            return songs_dict
    return songs_dict
    
def create_shazam_table(cur, conn):
    cur.execute("DROP TABLE IF EXISTS shazam")
    cur.execute("CREATE TABLE shazam(song_id INTEGER PRIMARY KEY, shazam_ranking INT)")
    conn.commit()

def count_songs_in_shazam(cur):
    cur.execute("SELECT * FROM shazam")
    matches = cur.fetchall()
    return len(matches)

def add_songs_shazam(songs_dict, shazam_list, cur, conn):
    initial_count = count_songs_in_shazam(cur)
    # add each unique song into a dict before inputting that dict into a data base, songs cannot repeat but artists can
    for item in shazam_list:
        shazam_ranking = item[0]
        song_id = songs_dict[item[1]][0]
        cur.execute("INSERT OR IGNORE INTO shazam (song_id, shazam_ranking) VALUES (?,?)", (song_id, shazam_ranking))
        count = count_songs_in_shazam(cur)
        if count - initial_count >= 25: 
            conn.commit()
            return

def create_billboard_table(cur, conn):
    cur.execute("DROP TABLE IF EXISTS billboard")
    cur.execute("CREATE TABLE billboard(song_id INTEGER PRIMARY KEY, billboard_ranking TEXT)")
    conn.commit()

def count_songs_in_billboard(cur):
    cur.execute("SELECT * FROM billboard")
    matches = cur.fetchall()
    return len(matches)
    
def add_songs_billboard(songs_dict, billboard_list, cur, conn):
    initial_count = count_songs_in_billboard(cur)
    for item in billboard_list:
        billboard_ranking = item[0]
        song_id = songs_dict[item[1]][0]
        cur.execute("INSERT OR IGNORE INTO billboard (song_id, billboard_ranking) VALUES (?,?)", (song_id, billboard_ranking))
        count = count_songs_in_billboard(cur)
        if count - initial_count >= 25:
            conn.commit()
            return

def create_itunes_table(cur, conn):
    cur.execute("DROP TABLE IF EXISTS itunes")
    cur.execute("CREATE TABLE itunes(song_id INTEGER PRIMARY KEY, time_ms INT, genre TEXT)")
    conn.commit()

def count_songs_in_itunes(cur):
    cur.execute("SELECT * FROM itunes")
    matches = cur.fetchall()
    return len(matches)

def add_songs_itunes(itunes_list, cur, conn):
    initial_count = count_songs_in_itunes(cur)
    for item in itunes_list:
        song_id = item[0]
        time_ms = item[1]
        genre = item[2]
        cur.execute("INSERT OR IGNORE INTO itunes (song_id, time_ms, genre) VALUES (?,?,?)", (song_id, time_ms, genre))
        count = count_songs_in_itunes(cur)
        if count - initial_count >= 25:
            conn.commit()
            return

def get_difference(cur, conn):
    cur.execute("SELECT DISTINCT shazam.song_id, billboard.song_id, shazam.shazam_ranking, billboard.billboard_ranking FROM shazam JOIN billboard WHERE shazam.song_id = billboard.song_id")
    matches = cur.fetchall()
    difference_list = []
    id_list = []
    specific_song_list = []
    for item in matches:
        ranking_difference = item[2] - int(item[3])
        difference_list.append(ranking_difference)
       # print(difference_list)
        id_list.append(item[0])

    for id in id_list:
        cur.execute("SELECT songs.song_id, songs.song_title FROM songs WHERE songs.song_id = ?", (id,))
        specific_song = cur.fetchone()[1]
        # print(specific_song)
        specific_song_list.append(specific_song)
        # print(specific_song_list)
        y = difference_list
        x = specific_song_list
        c = ['gold', 'gold', 'gold', 'gold', 'blue', 'gold', 'blue', 'gold', 'gold', 'blue', 'blue', 'blue', 'gold', 'blue', 'gold', 'gold', 'blue', 'blue', 'blue']
    conn.commit()

    plt.bar(x, y, color = c)
    plt.title('Difference in Song Ranking between Shazam and Billboard Top 100 Lists')
    plt.xlabel('Specific Song')
    plt.xticks(rotation = 45, ha = 'right', wrap = True)
    plt.ylabel('Difference (Shazam Ranking - Billboard Ranking)')
    plt.tight_layout()
    plt.show()
    return difference_list

def write_txt(matches, filename):
    file_obj = open(filename, 'w')
    for item in matches:
        file_obj.write(str(item))
        file_obj.write('\n')

def get_shazam_genres(cur, conn):
    cur.execute('SELECT itunes.song_id, itunes.genre, shazam.song_id FROM itunes JOIN shazam WHERE itunes.song_id = shazam.song_id')
    matches = cur.fetchall()
    genre_list = []
    for item in matches:
        genre_list.append(item[1])
    conn.commit()
    my_labels = 'Pop', 'Hip-Hop/Rap', 'Alternative', 'Rock', 'Dance', 'Country', 'R&B/Soul', 'Urbano latino', 'Holiday', 'Singer/Songwriter', 'Christmas', 'Indie Pop', 'Latin', 'Soundtrack', 'Hard Rock', 'Brazilian', 'Worldwide', 'Baile Funk', 'Metal', 'Electronic', 'TV Soundtrack', 'Punk', 'Thanksgiving', 'Amapiano', 'Christian', 
    my_data = []
    for label in my_labels:
        count = 0
        for genre in genre_list:
            if genre == label:
                count += 1
        my_data.append(count)
    plt.pie(my_data, autopct='%1.1f%%')
    plt.title('Distribution of Genres for Shazam Top 100')
    plt.axis('equal')
    plt.legend(labels = my_labels, loc="best")
    plt.show()

def get_billboard_genres(cur, conn):
    cur.execute('SELECT itunes.song_id, itunes.genre, billboard.song_id FROM itunes JOIN billboard WHERE itunes.song_id = billboard.song_id')
    matches = cur.fetchall()
    genre_list = []
    for item in matches:
        genre_list.append(item[1])
    conn.commit()
    my_labels = 'Pop', 'Hip-Hop/Rap', 'Alternative', 'Rock', 'Dance', 'Country', 'R&B/Soul', 'Urbano latino', 'Holiday', 'Singer/Songwriter', 'Christmas',  'Soundtrack', 'Christmas: Pop'
    my_data = []
    for label in my_labels:
        count = 0
        for genre in genre_list:
            if genre == label:
                count += 1
        my_data.append(count)
    plt.pie(my_data, autopct='%1.1f%%')
    plt.title('Distribution of Genres for Billboard Top 100')
    plt.axis('equal')
    plt.legend(labels = my_labels, loc="best")
    plt.show()

def main():
    # sets up database
    cur, conn = setUpDatabase('fp.db')

    status = ""
    print("[1] Start Over\n[2] Continue\n[3] Quit\n")
    status = int(input("Would you like to start over or continue: "))
    if status == 1:
        create_song_table(cur, conn)
        shazam_list = get_shazam_list()
        billboard_list = get_billboard_list()
        songs_dict = add_songs(shazam_list, billboard_list, cur, conn)
        create_shazam_table(cur, conn)
        create_billboard_table(cur, conn)
        add_songs_shazam(songs_dict, shazam_list, cur, conn)
        add_songs_billboard(songs_dict, billboard_list, cur, conn)
        itunes_list = get_itunes_list(songs_dict)
        create_itunes_table(cur, conn)
        add_songs_itunes(itunes_list, cur, conn)
        difference_list = get_difference(cur, conn)
        write_txt(difference_list, 'fp.txt')
        get_shazam_genres(cur, conn)
        get_billboard_genres(cur, conn)
    elif status == 2:
        shazam_list = get_shazam_list()
        billboard_list = get_billboard_list()
        songs_dict = add_songs(shazam_list, billboard_list, cur, conn)
        add_songs_shazam(songs_dict, shazam_list, cur, conn)
        add_songs_billboard(songs_dict, billboard_list, cur, conn)
        itunes_list = get_itunes_list(songs_dict)
        add_songs_itunes(itunes_list, cur, conn)
        difference_list = get_difference(cur, conn)
        write_txt(difference_list, 'fp.txt')
        get_shazam_genres(cur, conn)
        get_billboard_genres(cur, conn)
    else:
        pass


if __name__ == "__main__":
    main()
