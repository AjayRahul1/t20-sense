import os, json, io, base64, requests
from google.cloud import storage
from matplotlib.figure import Figure

try:
  # Set the path to your service account key file
  os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('API_KEY') # 't20-sense-main.json'
  # Create a client using the credentials
  storage_client = storage.Client()
except:
  print("API KEY not found")

# Base Functions
def conv_to_base64(fig: Figure) -> str:
  img_stream = io.BytesIO()
  fig.savefig(img_stream, format="png")
  img_stream.seek(0)
  img_data = base64.b64encode(img_stream.read()).decode("utf-8")
  return img_data

def conv_to_html(fig) -> str:
  """Convert the Plotly figure to HTML using plotly.io.to_html"""
  import plotly.io as pio
  fig_html = pio.to_html(fig, full_html=False)
  return fig_html

def get_series_data_from_bucket(series_id: int) -> dict:
  """Retrieves Information about a SERIES/TOURNAMENT.

  Parameters
  ---
    series_id: The ID for the tournaments.
  
  Returns
  ---
    dict
      JSON data (dict) of info about entire series and other data."""
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
    print("GCS Bucket has some exception. So turning to ESPN Cricinfo API to get Series Data")
    url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/series/schedule?lang=en&seriesId={series_id}"
    headers={"User-Agent":	"Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}
    ld = requests.get(url, headers=headers)
  return ld.json() # ld stands for the loaded data that came from JSON

def get_match_data_from_bucket(series_id: int, match_id: int) -> dict:
  """Retrieves info about a MATCH of a series/tournament from GCS Bucket if key was provided else from Cricket API.

  Parameters
  ---
    series_id: ID of the series/tournament.
    match_id: ID of the match in the series/tournament.

  Returns
  ---
    JSON Data for one match in the series/tournament."""
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
    print("GCS Bucket has some exception. So turning to ESPN Cricinfo API to get Match Data")
    url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId={series_id}&matchId={match_id}"
    headers={"User-Agent":	"Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}
    ld = requests.get(url, headers=headers)
  return ld.json() # ld stands for the loaded data that came from JSON

def get_innings_data(series_id: int, match_id: int, innings: int) -> dict:
  """
  Retrieve Innings JSON Data

  Retrieves info about an INNINGS of a match of a series/tournament from GCS Bucket if key was provided else from Cricket API.

  Parameters
  ---
    series_id (int): ID of the tournament.
    match_id (int): ID of the match in the tournament.
    innings (int): 
  
  Returns
  ---
  dict
    JSON Data of ball by ball in each innings
  """
  print("Turning to ESPN Cricinfo API to get Match Data")
  url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/comments?lang=en&seriesId={series_id}&matchId={match_id}&inningNumber={innings}&commentType=ALL&sortDirection=DESC&fromInningOver=-1"
  headers={"User-Agent":	"Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}
  ld = requests.get(url, headers=headers)
  return ld.json()

# Define a custom sorting key to order the latest matches in the order of RUNNING, SCHEDULED, FINISHED
def custom_sort(item):
  order = {"RUNNING": 0, "SCHEDULED": 1, "FINISHED": 2}
  return order.get(item['stage'], float('inf'))

def get_latest_match_data() -> dict:
  headers = {"User-Agent":	"Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}
  ld: dict = requests.get("https://hs-consumer-api.espncricinfo.com/v1/pages/matches/current?lang=en&latest=true", headers=headers).json()
  ld['matches'] = sorted(ld['matches'], key=lambda x: x['objectId'])
  ld['matches'] = [it for it in ld['matches'] if it["statusText"] and it["coverage"] != "N"]
  ld['matches'] = sorted(ld['matches'], key=custom_sort)
  return ld

def get_latest_domestic_match_data() -> dict:
  headers = {"User-Agent":	"Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}
  ld: dict = requests.get("https://hs-consumer-api.espncricinfo.com/v1/pages/matches/current?lang=en&latest=true", headers=headers).json()
  ld['matches'] = sorted(ld['matches'], key=lambda x: x['objectId'])
  ld['matches'] = [it for it in ld['matches'] if it['internationalClassId'] is None]
  ld['matches'] = sorted(ld['matches'], key=custom_sort)
  return ld

def get_match_players_dict(series_id: int, match_id: int) -> dict:
  """If series_id and match_id are passed, then this function gets called, returns players names.
  
  Parameters
  ---
    series_id: ID of the series/tournament.
    match_id: ID of the match in the series/tournament.
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

  Parameters
  ---
    content: The second part of the match dictionary (JSON Data)
    
  Returns
  ---
    Dictionary with information about players
  """
  # Generating a dictionary of players who played in that match to map it later
  # for who ever was out and was in the partnership using Dictionary Comprehension
  players_dict = {
    player['player']['id']: player['player']['longName']
    for team in content['matchPlayers']['teamPlayers']
    for player in team['players']
  }
  return players_dict