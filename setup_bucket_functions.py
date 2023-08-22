import pandas as pd, requests, os, pickle
from google.cloud import storage  # Google Cloud Storage Imports

# Set the path to your service account key file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('API_KEY') # 't20-sense-main.json'

# Create a client using the credentials
storage_client = storage.Client()

# Global Variables
ipl_all_series_ids = [313494, 374163, 418064, 466304, 520932, 586733, 695871, 791129, 968923, 1078425, 1131611, 1165643, 1210595, 1249214, 1298423, 1345038]

def get_series_info_response_API(series_id):
  url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/series/schedule?lang=en&seriesId={series_id}"
  response = requests.get(url)
  return response.json()

def get_match_info_response_API(series_id, match_id):
  url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId={series_id}&matchId={match_id}"
  response = requests.get(url)
  return response.json()

def get_innings_info_response_API(series_id, match_id, innings_id):
  url = f'https://hs-consumer-api.espncricinfo.com/v1/pages/match/comments?lang=en&seriesId={series_id}&matchId={match_id}&inningNumber={innings_id}&commentType=ALL&sortDirection=DESC&fromInningOver=-1'
  response = requests.get(url)
  return response.json()

def match_ids(series_id):
  url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/series/schedule?lang=en&seriesId={series_id}"
  output = requests.get(url)
  matches = output.json()['content']["matches"]
  df_m = pd.json_normalize(data=matches)
  return df_m['objectId']

def create_series_info_bucket():
  # Variables
  global ipl_all_series_ids
  bucket_name = 't20_sense_series_info'
  
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
      file_name = f"s_{series_id}_data.pkl"
      blob = bucket.blob(file_name)
      if blob.exists():
          # File Exists
          continue
      else:
          # File doesn't exist. So uploading
          series_json_data = get_series_info_response_API(series_id)
          series_json_data = pickle.dumps(series_json_data)

          # Upload the pickled data to the bucket
          blob.upload_from_string(series_json_data, content_type='application/octet-stream')

def create_match_info_bucket():
  global ipl_all_series_ids
  bucket_name = 't20_sense_match_info'
  
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
      print('Creating match_info file for ', series_id)
      matches_ids = match_ids(series_id)
      for match_id in matches_ids:
        file_name = f"s_{series_id}_m_{match_id}_data.pkl"
        blob = bucket.blob(file_name)
        if blob.exists():
            # File Exists
            continue
        else:
          match_json_data = get_match_info_response_API(series_id, match_id)
          match_json_data = pickle.dumps(match_json_data)
          
          blob.upload_from_string(match_json_data, content_type='application/octet-stream')

if __name__ == '__main__':
  create_series_info_bucket()
  create_match_info_bucket()