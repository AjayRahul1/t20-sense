import pandas as pd, traceback, os, pickle
from google.cloud import storage

# Set the path to your service account key file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('API_KEY') # 't20-sense-main.json'
# Create a client using the credentials
storage_client = storage.Client()

# Base Functions
def get_series_data_from_bucket(series_id):
  try:
    bucket_name = os.getenv('BUCKET_NAME')
    # fp stands for File Path
    fp = f't20_sense_series_info/s_{series_id}_data.pkl'
    bucket = storage_client.get_bucket(bucket_name)
    # Get the blob (file) from the bucket
    blob = bucket.blob(fp)
    # Download the pickle file data as bytes
    pickled_data = blob.download_as_bytes()
    # Load the pickled data
    ld = pickle.loads(pickled_data)
    # Lets us know whether bucket is used or API
    print("Using GCS Bucket to get Series Data")
  except:
    import requests
    print("GCS Bucket has some exception. So turning to ESPN Cricinfo API to get Series Data")
    url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/series/schedule?lang=en&seriesId={series_id}"
    ld = requests.get(url)
    ld= ld.json()
  return ld # ld stands for the loaded data that came from JSON

def get_match_data_from_bucket(series_id, match_id):
  try:
    bucket_name = os.getenv('BUCKET_NAME')
    fp = f't20_sense_match_info/s_{series_id}_m_{match_id}_data.pkl' # fp stands for File Path
    bucket = storage_client.get_bucket(bucket_name)
    # Get the blob (file) from the bucket
    blob = bucket.blob(fp)
    # Download the pickle file data as bytes
    pickled_data = blob.download_as_bytes()
    # Load the pickled data
    ld = pickle.loads(pickled_data)
    # Lets us know whether bucket is used or API
    print("Using GCS Bucket to get Match Data")
  except:
    import requests
    print("GCS Bucket has some exception. So turning to ESPN Cricinfo API to get Match Data")
    url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId={series_id}&matchId={match_id}"
    ld = requests.get(url)
    ld = ld.json()
  return ld # ld stands for the loaded data that came from JSON

# Define a custom sorting key to order the latest matches in the order of RUNNING, SCHEDULED, FINISHED
def custom_sort(item):
  order = {"RUNNING": 0, "SCHEDULED": 1, "FINISHED": 2}
  return order.get(item['stage'], float('inf'))

def get_latest_intl_match_data():
  import requests
  ld = requests.get("https://hs-consumer-api.espncricinfo.com/v1/pages/matches/current?lang=en&latest=true").json()
  ld['matches'] = sorted(ld['matches'], key=lambda x: x['objectId'])
  ld['matches'] = [it for it in ld['matches'] if it['internationalClassId'] is not None and it['internationalNumber'] is not None]
  ld['matches'] = sorted(ld['matches'], key=custom_sort)
  return ld

def get_latest_domestic_match_data():
  import requests
  ld = requests.get("https://hs-consumer-api.espncricinfo.com/v1/pages/matches/current?lang=en&latest=true").json()
  ld['matches'] = sorted(ld['matches'], key=lambda x: x['objectId'])
  ld['matches'] = [it for it in ld['matches'] if it['internationalClassId'] is None]
  ld['matches'] = sorted(ld['matches'], key=custom_sort)
  return ld
