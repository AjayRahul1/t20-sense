import requests, os, pickle
import pandas as pd
from google.cloud import storage  # Google Cloud Storage Imports

# Set the path to your service account key file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 't20-sense-8f218a81848c.json'

# Create a client using the credentials
storage_client = storage.Client()

def get_series_data_from_bucket(series_id):
  bucket_name = 't20_sense_series_info'
  file_path = f's_{series_id}_data.pkl'
  bucket = storage_client.get_bucket(bucket_name)
  # Get the blob (file) from the bucket
  blob = bucket.blob(file_path)
  # Download the pickle file data as bytes
  pickled_data = blob.download_as_bytes()
  # Load the pickled data
  loaded_data = pickle.loads(pickled_data)
  return loaded_data

def get_match_data_from_bucket(series_id, match_id):
  bucket_name = 't20_sense_match_info'
  file_path = f's_{series_id}_m_{match_id}_data.pkl'
  bucket = storage_client.get_bucket(bucket_name)
  # Get the blob (file) from the bucket
  blob = bucket.blob(file_path)
  # Download the pickle file data as bytes
  pickled_data = blob.download_as_bytes()
  # Load the pickled data
  loaded_data = pickle.loads(pickled_data)
  return loaded_data

def get_man_of_the_match(series_id, match_id):
  url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId={series_id}&matchId={match_id}"
  response = requests.get(url)
  mom = response.json()['content']['matchPlayerAwards'][0]['player']['longName']
  return mom

def get_best_shots(series_id, match_id):
  url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId={series_id}&matchId={match_id}"
  response = requests.get(url)
  bat_data = response.json()['content']['bestPerformance']['batsmen']
  perf_bat_inn1 = f"{bat_data[0]['teamAbbreviation']} - {bat_data[0]['player']['longName']} with {bat_data[0]['shot']} shot scoring {bat_data[0]['shotRuns']} out of {bat_data[0]['runs']} runs"
  perf_bat_inn2 = f"{bat_data[1]['teamAbbreviation']} - {bat_data[1]['player']['longName']} with {bat_data[1]['shot']} shot scoring {bat_data[1]['shotRuns']} out of {bat_data[1]['runs']} runs"
  return perf_bat_inn1, perf_bat_inn2

def fun_best_bowl_peformance(series_id, match_id):
  # Bowlers Stats Format -> Overs-Maidens-Runs-Wickets
  data = get_match_data_from_bucket(series_id, match_id)
  data = data['content']['bestPerformance']['bowlers']
  data0 = data[0] # 1st bowler
  data1 = data[1] # 2nd bowler
  bowl_perf_inn_1 = f"{data0['teamAbbreviation']} - {data0['player']['longName']} - [{data0['overs']}-{data0['maidens']}-{data0['conceded']}-{data0['wickets']}] conceding {data0['dots']} dots and Econ. {data0['economy']}"
  bowl_perf_inn_2 = f"{data1['teamAbbreviation']} - {data1['player']['longName']} - [{data1['overs']}-{data1['maidens']}-{data1['conceded']}-{data1['wickets']}] conceding {data1['dots']} dots and Econ. {data1['economy']}"
  return bowl_perf_inn_1, bowl_perf_inn_2