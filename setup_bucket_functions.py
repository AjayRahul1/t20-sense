import pandas as pd, requests, os, json
from google.cloud import storage  # Google Cloud Storage Imports

# Global Variables
ipl_all_series_ids = [313494, 374163, 418064, 466304, 520932, 586733, 695871, 791129, 968923, 1078425, 1131611, 1165643, 1210595, 1249214, 1298423, 1345038]

headers={"User-Agent":	"Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"}

def get_series_info_API(series_id: int) -> dict:
  """Information about a SERIES/TOURNAMENT.

  :param series_id: The ID for the tournaments.
  :return: Return JSON data of info about entire series and other data."""
  url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/series/schedule?lang=en&seriesId={series_id}"
  response = requests.get(url, headers=headers)
  return response.json()

def get_match_info_API(series_id:int, match_id: int):
  """Information about a MATCH of a series/tournament.

  :param series_id: ID of the series/tournament.
  :param match_id: ID of the match in the series/tournament.
  :return: JSON Data for one match in the series/tournament.
  """
  url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId={series_id}&matchId={match_id}"
  response = requests.get(url, headers=headers)
  return response.json()

def get_innings_info_API(series_id: int, match_id: int, innings_id: int):
  """Information about an INNINGS in a match of a series

  :param series_id: ID of the tournament.
  :param match_id: ID of the match in the tournament.
  :param innings_no:
  :return: JSON Data of ball by ball in each innings."""
  url = f'https://hs-consumer-api.espncricinfo.com/v1/pages/match/comments?lang=en&seriesId={series_id}&matchId={match_id}&inningNumber={innings_id}&commentType=ALL&sortDirection=DESC&fromInningOver=-1'
  response = requests.get(url, headers=headers)
  return response.json()

def match_ids(series_id: int):
  matches = get_series_info_API(series_id)['content']["matches"]
  df_m = pd.json_normalize(data=matches)
  return df_m['objectId']

def create_series_info_bucket(storage_client):
  # Variables
  global ipl_all_series_ids
  bucket_name = os.getenv('BUCKET_NAME')
  
  try:
    bucket = storage_client.get_bucket(bucket_name)
    # Bucket exists
  except Exception:
    # Bucket doesn't exist. Creating the bucket.
    bucket = storage_client.create_bucket(bucket_name)

  finally:
    bucket = storage_client.get_bucket(bucket_name)
    print('series_info bucket function running...')
    for series_id in ipl_all_series_ids:
      file_name = f"t20_sense_series_info/s_{series_id}_data.json"
      blob = bucket.blob(file_name)
      if blob.exists():
          # File Exists
          continue
      else:
          # File doesn't exist. So uploading
          series_json_data = get_series_info_API(series_id)
          series_json_data = json.dumps(series_json_data)

          # Upload the pickled data to the bucket
          blob.upload_from_string(series_json_data, content_type='application/octet-stream')
    print('series_info JSON files uploaded successfully!')

def create_match_info_bucket():
  global ipl_all_series_ids
  bucket_name = os.getenv('BUCKET_NAME')
  
  try:
    bucket = storage_client.get_bucket(bucket_name)
    # Bucket exists
  except Exception:
    # Bucket doesn't exist. Creating the bucket.
    bucket = storage_client.create_bucket(bucket_name)

  finally:
    print('match_info bucket function running...')
    bucket = storage_client.get_bucket(bucket_name)
    for series_id in ipl_all_series_ids:
      print('Creating match_info files for series', series_id)
      matches_ids = match_ids(series_id)
      for match_id in matches_ids:
        file_name = f"t20_sense_match_info/s_{series_id}_m_{match_id}_data.json"
        blob = bucket.blob(file_name)
        if blob.exists():
            # File Exists
            continue
        else:
          match_json_data = get_match_info_API(series_id, match_id)
          match_json_data = json.dumps(match_json_data)
          
          blob.upload_from_string(match_json_data, content_type='application/octet-stream')
    print('match_info JSON files uploaded successfully!')

if __name__ == '__main__':
  try:
    # Set the path to your service account key file
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('API_KEY') # 't20-sense-main.json'

    # Create a client using the credentials
    storage_client = storage.Client()

    create_series_info_bucket(storage_client)
    create_match_info_bucket(storage_client)
  except:
    print("Unable to setup since API KEY not found. Setup through Environment Variables")