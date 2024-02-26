import os, json
from google.cloud import storage

try:
  # Set the path to your service account key file
  os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('API_KEY') # 't20-sense-main.json'
  # Create a client using the credentials
  storage_client = storage.Client()
except:
  print("API KEY not found")

# Base Functions
def get_series_data_from_bucket(series_id: int) -> dict:
  """Retrieves Information about a SERIES/TOURNAMENT.

  :param series_id: The ID for the tournaments.
  :return: Return JSON data (dict) of info about entire series and other data."""
  try:
    bucket_name = os.getenv('BUCKET_NAME')
    # fp stands for File Path
    fp = f't20_sense_series_info/s_{series_id}_data.json'
    bucket = storage_client.get_bucket(bucket_name)
    # Get the blob (file) from the bucket
    blob = bucket.blob(fp)
    # Download the json file data as bytes
    json_data = blob.download_as_bytes()
    # Load the json data
    ld = json.loads(json_data)
    # Lets us know whether bucket is used or API
    print("Getting Series Data from GCS Bucket...")
  except:
    import requests
    print("GCS Bucket has some exception. So turning to ESPN Cricinfo API to get Series Data")
    url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/series/schedule?lang=en&seriesId={series_id}"
    headers={"User-Agent":	"Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}
    ld = requests.get(url, headers=headers)
  return ld.json() # ld stands for the loaded data that came from JSON

def get_match_data_from_bucket(series_id: int, match_id: int) -> dict:
  """Retrieves info about a MATCH of a series/tournament from GCS Bucket if key was provided else from Cricket API.

  :param series_id: ID of the series/tournament.
  :param match_id: ID of the match in the series/tournament.
  :return: JSON Data for one match in the series/tournament.
  """
  try:
    bucket_name = os.getenv('BUCKET_NAME')
    fp = f't20_sense_match_info/s_{series_id}_m_{match_id}_data.json' # fp stands for File Path
    bucket = storage_client.get_bucket(bucket_name)
    # Get the blob (file) from the bucket
    blob = bucket.blob(fp)
    # Download the pickle file data as bytes
    json_data = blob.download_as_bytes()
    # Load the pickled data
    ld = json.loads(json_data)
    # Lets us know whether bucket is used or API
    print("Getting Match Data from GCS Bucket...")
  except:
    import requests
    print("GCS Bucket has some exception. So turning to ESPN Cricinfo API to get Match Data")
    url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId={series_id}&matchId={match_id}"
    headers={"User-Agent":	"Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}
    ld = requests.get(url, headers=headers)
  return ld.json() # ld stands for the loaded data that came from JSON

def get_innings_data(series_id: int, match_id: int, innings: int) -> dict:
  """Retrieves info about an INNINGS of a match of a series/tournament from GCS Bucket if key was provided else from Cricket API.

  :param series_id: ID of the tournament.
  :param match_id: ID of the match in the tournament.
  :param innings_no:
  :return: JSON Data of ball by ball in each innings."""
  import requests
  url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/comments?lang=en&seriesId={series_id}&matchId={match_id}&inningNumber={innings}&commentType=ALL&sortDirection=DESC&fromInningOver=-1"
  headers={"User-Agent":	"Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}
  ld = requests.get(url, headers=headers)
  return ld.json()

# Define a custom sorting key to order the latest matches in the order of RUNNING, SCHEDULED, FINISHED
def custom_sort(item):
  order = {"RUNNING": 0, "SCHEDULED": 1, "FINISHED": 2}
  return order.get(item['stage'], float('inf'))

def get_latest_intl_match_data():
  import requests
  headers = {"User-Agent":	"Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}
  ld = requests.get("https://hs-consumer-api.espncricinfo.com/v1/pages/matches/current?lang=en&latest=true", headers=headers).json()
  ld['matches'] = sorted(ld['matches'], key=lambda x: x['objectId'])
  ld['matches'] = [it for it in ld['matches'] if it['internationalClassId'] is not None and it['internationalNumber'] is not None]
  ld['matches'] = sorted(ld['matches'], key=custom_sort)
  return ld

def get_latest_domestic_match_data():
  import requests
  headers = {"User-Agent":	"Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}
  ld = requests.get("https://hs-consumer-api.espncricinfo.com/v1/pages/matches/current?lang=en&latest=true", headers=headers).json()
  ld['matches'] = sorted(ld['matches'], key=lambda x: x['objectId'])
  ld['matches'] = [it for it in ld['matches'] if it['internationalClassId'] is None]
  ld['matches'] = sorted(ld['matches'], key=custom_sort)
  return ld

def get_match_players_dict(series_id: int, match_id: int) -> dict:
  """If series_id and match_id are passed, then this function gets called, returns players names.
  :param series_id: ID of the series/tournament.
  :param match_id: ID of the match in the series/tournament.
  """
  content = get_match_data_from_bucket(series_id, match_id)['content']
  # Generating a dictionary of players who played in that match to map it later
  # for who ever was out and was in the partnership using Dictionary Comprehension
  players_dict = {
    player['player']['id']: player['player']['longName']
    for team in content['matchPlayers']['teamPlayers']
    for player in team['players']
  }
  return players_dict

def get_match_players_dict(content: dict) -> dict:
  """If content of API JSON are passed, then this function gets called and then loops over it to get player names.

  :param content: The second part of the match dictionary."""
  # Generating a dictionary of players who played in that match to map it later
  # for who ever was out and was in the partnership using Dictionary Comprehension
  players_dict = {
    player['player']['id']: player['player']['longName']
    for team in content['matchPlayers']['teamPlayers']
    for player in team['players']
  }
  return players_dict