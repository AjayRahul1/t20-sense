import pandas as pd, requests, traceback, warnings
from datetime import datetime
import asyncio

# Google Cloud Storage Imports
from google.cloud import storage
import pandas as pd, os, io

# Settings the warnings to be ignored
warnings.filterwarnings('ignore')

all_series_ids = [313494, 374163, 418064, 466304, 520932, 586733, 695871, 791129, 968923, 1078425, 1131611, 1165643, 1210595, 1249214, 1298423, 1345038]

series_id_taken = 418064
match_id_taken = 419165
innings_taken = 2

"""# Get matches data"""

def set_cloud_bucket_env():
  # Set the path to your service account key file
  os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 't20-sense-8f218a81848c.json'

  # Create a client using the credentials
  client = storage.Client()

  # Specify the bucket name and CSV file path
  bucket_name = 'match_data'

  # Access the bucket
  bucket = client.get_bucket(bucket_name)
  return client, bucket

def get_all_csv_files_from_cloud():
  client, bucket = set_cloud_bucket_env()
  file_path = 'whole_ipl_series_info.csv'

  # Get the blob (file) from the bucket
  blob = bucket.blob(file_path)

  # Read the file contents into memory
  file_content = blob.download_as_text()

  # Create a StringIO object to treat the file content as a file-like object
  csv_file = io.StringIO(file_content)

  # Read the CSV file using pandas
  all_ipl_series_info = pd.read_csv(csv_file)

  return all_ipl_series_info

def get_matches_returns_dict(series_id, stage="FINISHED"):
    try:
        url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/series/schedule?lang=en&seriesId={series_id}"
        output = requests.get(url)
        print(url)
        matches = output.json()['content']["matches"]
        df = pd.json_normalize(data=matches)
        if stage:
            df = df[df['stage']==stage]
        df.rename(columns={"objectId": "match_id", "slug": "match_name"}, inplace=True)
        df['match_name'] = df["match_id"].apply(lambda x: get_match_info(series_id,x)[4])
        df[['match_id', 'match_name']].to_dict('records')
        return df[['match_id', 'match_name']].to_dict('records')
    except Exception as e:
        traceback.print_exc()

"""# Match Info"""

def get_match_info(series_id,match_id):
    try:
        url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId={series_id}&matchId={match_id}"
        output = requests.get(url)
        team1 = output.json()['match']["teams"][0]["team"]["longName"]
        team1_sn = output.json()['match']["teams"][0]["team"]["abbreviation"]


        team2 = output.json()['match']["teams"][1]["team"]["longName"]
        team2_sn = output.json()['match']["teams"][1]["team"]["abbreviation"]


        match_date = datetime.strptime(output.json()['match']['startDate'].split("T")[0], '%Y-%m-%d')
        result = output.json()['match']["statusText"]
        match_num = output.json()['match']['title']
        title = team1_sn + " vs " + team2_sn + " " + match_num
        return team1, team2, match_date.strftime('%B %d %Y'), result, title
    except Exception as e:
        traceback.print_exc()

"""# Get Innings

## Preprocessing Whole DataFrame
"""

def preprocessing_innings_df(req_response):
  # Choosing the features that we are going to need and use
  cols = ["batsman", "bowler", "title", "batsmanPlayerId", "bowlerPlayerId", "noballs", "legbyes", "byes", "wides",
          "isFour", "isSix", "isWicket", "totalRuns", "batsmanRuns", "dismissalType"]
  main_df = pd.json_normalize(data=req_response.json()['comments'])

  # Splitting the features of title to batsman and batsman
  main_df[['bowler', 'batsman']] = main_df['title'].str.split(' to ', expand=True).iloc[:, :2]

  # Making batsman and bowlers dataframe
  batsman_df = main_df[cols]
  bowlers_df = main_df[cols]

  # We have dataset with 20 overs to 1 over. So we need to reverse it.
  batsman_df, bowlers_df = batsman_df[::-1], bowlers_df[::-1]

  return batsman_df, bowlers_df

"""## Bowlers DataFrame"""

#@title Preprocessing
def bowlers_df_preprocessing(bowlers_df):
  # Batsman scoring 0 is a dot.
  bowlers_df["isDot"] = (bowlers_df["batsmanRuns"] == 0) & (bowlers_df["wides"] == 0) & (bowlers_df["noballs"] == 0)

  bowlers_df = bowlers_df[["bowler", "isWicket", "totalRuns", "isDot","isFour", "isSix", "noballs", "legbyes", "byes", "wides", "dismissalType"]]

  # There can be case of wide going for 4 leading to 5 wides. Replace it with 1
  bowlers_df.loc[bowlers_df['wides'] > 0, 'wides'] = 1

  # 4 is runout. It must not be taken into Bowler's account.
  bowlers_df.loc[bowlers_df['dismissalType'] == 4, 'isWicket'] = False

  # Subtracting Wides and No Balls from the bowlers ball count
  bowlers_df["Balls"] = 1 - bowlers_df['wides'] - bowlers_df['noballs']

  # Grouping all the bowlers
  main_bowling_df = bowlers_df.groupby('bowler',as_index=False).sum()

  return main_bowling_df

#@title Operations
def bowlers_df_ops(main_bowling_df):
  # Adding Overs to the Bowler Scorecard
  main_bowling_df["Overs"] = main_bowling_df["Balls"].apply(lambda x:  divmod(x, 6))

  main_bowling_df["DB%"] = main_bowling_df["isDot"] * 100 / main_bowling_df["Balls"]  # Dot Ball Rate

  #Subtracting byes from runs of the bowler
  main_bowling_df["totalRuns"] = main_bowling_df["totalRuns"] - main_bowling_df["legbyes"] - main_bowling_df["byes"]

  main_bowling_df["Econ"] = main_bowling_df["totalRuns"] / (main_bowling_df["Balls"])*6 # Strike Rate

  # Drop dismissaltype
  main_bowling_df.drop(columns='dismissalType',inplace=True)

  # Sorting based on the runs
  main_bowling_df.sort_values(by=['isWicket', 'totalRuns'], ascending=[False, True], inplace=True)

  main_bowling_df[["DB%", "Econ"]] = main_bowling_df[["DB%", "Econ"]].applymap(lambda x: '{0:.2f}'.format(x))

  # Renaming Columns
  main_bowling_df.rename(columns={
      'bowler'    : 'Bowler',
      'isWicket'  : 'Wickets',
      'totalRuns' : 'Runs',
      'isDot'     : 'Dots',
      'isFour'    : 'Fours',
      'isSix'     : 'Sixers',
      'noballs'   : 'NB',
      'legbyes'   : 'LB',
      'wides'     : 'WD',
      'byes'      : 'Byes'
  }, inplace=True)
  main_bowling_df = main_bowling_df[['Bowler', 'Overs', 'Balls', 'Runs', 'Wickets','Dots', 'Fours', 'Sixers', 'WD', 'NB', 'Byes', 'LB', 'Econ', 'DB%']]
  return main_bowling_df

"""## Batsman DataFrame

* Preprocessing
* Operations
"""

def batting_df_pre_operations(batsman_df):

  # Calculating Dot Balls assigning T or F
  batsman_df["isDot"] = (batsman_df["batsmanRuns"] == 0) & (batsman_df["wides"] == 0) & (batsman_df["noballs"] == 0)

  batsman_df = batsman_df[["batsman", "batsmanRuns", "isDot","isFour", "isSix", "wides", "noballs", "legbyes"]]

  # There can be case of wide going for 4 leading to 5 wides. Replace it with 1
  batsman_df.loc[batsman_df['wides'] > 0, 'wides'] = 1
  batsman_df["Balls"] = 1 - batsman_df['wides']

  batsman_score_df = batsman_df.groupby('batsman',as_index=False, sort=False).sum()
  batsman_score_df["4s_SR"] = batsman_score_df["isFour"] * 100 / batsman_score_df["Balls"]
  batsman_score_df["6s_SR"] = batsman_score_df["isSix"] * 100 / batsman_score_df["Balls"]
  batsman_score_df["4&6_SR"] = (batsman_score_df["isSix"]+ batsman_score_df["isFour"] )* 100 / batsman_score_df["Balls"]

  batsman_score_df["DB%"] = batsman_score_df["isDot"] * 100 / batsman_score_df["Balls"]
  batsman_score_df["SR"] = batsman_score_df["batsmanRuns"] * 100 / batsman_score_df["Balls"]
  batsman_score_df["NDSR"] = batsman_score_df["batsmanRuns"] * 100 / (batsman_score_df["Balls"] - batsman_score_df["isDot"])

  batsman_score_df.drop(columns=['wides', 'noballs', 'legbyes'], inplace = True)

  # Formatting data to 2 decimal places
  batsman_score_df[["DB%", "SR", "NDSR", "4s_SR", "6s_SR", "4&6_SR"]] = batsman_score_df[["DB%", "SR", "NDSR", "4s_SR", "6s_SR", "4&6_SR"]].applymap(lambda x: '{0:.2f}'.format(x))

  # Creating Scorecard with features in order
  batsman_score_df = batsman_score_df[["batsman", "batsmanRuns", "Balls", "isDot", "isFour", "isSix", "SR", "NDSR", "DB%", "4s_SR", "6s_SR", "4&6_SR" ]]
  #Renaming columns
  batsman_score_df.rename(columns={
      'batsman'     : 'Batsman',
      'batsmanRuns' : 'Runs',
      'isDot'       : 'Dots',
      'isFour'      : 'Fours',
      'isSix'       : 'Sixes'
  }, inplace=True)

  return batsman_score_df

"""## Get Innings DataFrame"""

def get_innings_df(series_id, match_id, innings):
  # get respone from API and the data and save to req_response
  req_response = requests.get(
      f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/comments?lang=en&seriesId={series_id}&matchId={match_id}&inningNumber={innings}&commentType=ALL&sortDirection=DESC&fromInningOver=-1"
      )

  # Preprocessing the dataframe required
  # Getting Batsman and Bowling Dataframes separated
  batsman_df, bowlers_df = preprocessing_innings_df(req_response)

  ''' Bowling Scorecard '''

  # Preprocessing Bowlers DataFrame
  final_bowling_df = bowlers_df_preprocessing(bowlers_df)

  # Operations on Bowlers DataFrame
  final_bowling_df = bowlers_df_ops(final_bowling_df)

  ''' Batsman Scorecard '''

  # Both Preprocessing and Operations
  final_batsman_df = batting_df_pre_operations(batsman_df)

  return final_batsman_df, final_bowling_df

"""# It's Generating CSV time!"""

def scorecard_to_csv_gen(series_id, match_id):
  for match_innings in [1,2]:
    batting, bowling = get_innings_df(series_id, match_id, match_innings)
    batting.to_csv(f'ser{series_id}_mat{match_id}_inn{match_innings}_batting.csv', index=False)
    bowling.to_csv(f'ser{series_id}_mat{match_id}_inn{match_innings}_bowling.csv', index=False)

def get_particular_match_whole_score(series_id, match_id):
  batting = {}
  bowling = {}
  for match_innings in [1,2]:
    batting[match_innings],bowling[match_innings] = get_innings_df(series_id, match_id, match_innings)

  asyncio.sleep(1)
  return batting[1], bowling[1], batting[2], bowling[2]

def get_request_response_API(series_id, match_id, innings_id):
  url = f'https://hs-consumer-api.espncricinfo.com/v1/pages/match/comments?lang=en&seriesId={series_id}&matchId={match_id}&inningNumber={innings_id}&commentType=ALL&sortDirection=DESC&fromInningOver=-1'
  response = requests.get(url)
  return response

"""## Comments Extraction"""

#@title Get Comments of a single innings in a match
def get_comments_for_match_innings(series_id, match_id, innings_id):
  # Getting request response
  response = get_request_response_API(series_id, match_id, innings_id)

  # Initialized empty list
  innings_comments = []

  # JSON loading
  for i in response.json()['comments']:
    comment_obj = {}
    if i['commentTextItems']:
      comment_obj['comments'] = i['commentTextItems'][0]['html']
    elif i['commentTextItems'] is None:
      comment_obj['comments'] = ' '
    comment_obj['wagonZone'] = i['wagonZone']
    innings_comments.append(comment_obj)
  return innings_comments

#@title Extracting comments into a dataframe
comments=pd.DataFrame()
def get_comm(series_id,match_id,innings):
  comm_for_match=get_comments_for_match_innings(series_id, match_id, innings)
  comm_for_match=pd.DataFrame(comm_for_match)
  comments=pd.DataFrame(comm_for_match['comments'])
  return comments

"""## Get one innings from extracted data

* Gets you ball by ball data of 1 innings.
* innings_id ->
  * 1 - 1st innings data
  * 2 - 2nd innings data
"""

def get_one_innings_from_extracted_data(series_id, match_id, innings_id):
  cols_to_be_taken = ['id','inningNumber','oversActual',
                      'overNumber','ballNumber','totalRuns',
                      'batsmanRuns', 'isFour', 'isSix', 'isWicket',
                      'dismissalType', 'byes', 'legbyes','wides',
                      'noballs', 'penalties','title']

  req_response = get_request_response_API(series_id, match_id, innings_id)
  main_df = pd.json_normalize(data=req_response.json()['comments'])

  # Getting all the comments
  innings_comments = get_comm(series_id, match_id, innings_id)

  # Selectively picking the columns
  final_df = main_df[cols_to_be_taken]

  # Adding comments to the dataframe at the end
  final_df["Comment"] = innings_comments

  # Inserting match_id as 1st column
  final_df.insert(0, 'series_id', series_id)

  # Inserting match_id as 2nd column
  final_df.insert(1, 'match_id', match_id)

  # Splitting title into batsman and bowler Reorder the columns
  split_columns = final_df['title'].str.split(' to ', expand=True)
  final_df.insert(8, 'batsman', split_columns[1])
  final_df.insert(9, 'bowler', split_columns[0])
  final_df.drop(columns='title', inplace=True)

  # Renaming id to ball_id
  final_df.rename(columns={'id':'ball_id'}, inplace=True)

  # Reversing the dataframe from 20th to 1st over into 1st to 20th over
  final_df = final_df[::-1]
  return final_df

def get_matches_returns_list(series_id, stage="FINISHED"):
    try:
        url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/series/schedule?lang=en&seriesId={series_id}"
        output = requests.get(url)
        matches = output.json()['content']["matches"]
        df = pd.json_normalize(data=matches)
        if stage:
            df = df[df['stage']==stage]
        df.rename(columns={"objectId": "match_id", "slug": "match_name"}, inplace=True)
        df = pd.DataFrame(df[['match_id', 'match_name']].to_dict('records'))
        df = df['match_id'].to_list()
        return df
    except Exception as e:
        traceback.print_exc()

"""## Get single series Ball by Ball Data"""

def get_series_info(series_id):
  temp_df_to_concat = pd.DataFrame(columns=['series_id', 'match_id', 'ball_id', 'inningNumber', 'oversActual',
       'overNumber', 'ballNumber', 'totalRuns', 'batsman', 'bowler', 'batsmanRuns', 'isFour',
       'isSix', 'isWicket', 'dismissalType', 'byes', 'legbyes', 'wides',
       'noballs', 'penalties', 'Comment'])

  # LSG vs CSK 2nd Innings washed out due to rain.
  # match_ids_list.remove(1359519)

  all_match_ids_list = get_matches_returns_list(series_id)
  for match_id_iter in all_match_ids_list:
    try:
      for innings_iter in [1,2]:
        temp_df = get_one_innings_from_extracted_data(series_id, match_id_iter, innings_iter)
        temp_df_to_concat = pd.concat([temp_df_to_concat, temp_df])
    except Exception as e:
      print(f'The series {series_id} - match {match_id_iter} - innings {innings_iter} did not take place')
      continue
  return temp_df_to_concat

def get_all_series_info(all_series_ids_list):
  temp_df_to_concat = pd.DataFrame(columns=['series_id', 'match_id', 'ball_id', 'inningNumber', 'oversActual',
       'overNumber', 'ballNumber', 'totalRuns', 'batsman', 'bowler', 'batsmanRuns', 'isFour',
       'isSix', 'isWicket', 'dismissalType', 'byes', 'legbyes', 'wides',
       'noballs', 'penalties', 'Comment'])

  # LSG vs CSK 2nd Innings washed out due to rain.

  for series_iter in all_series_ids_list:
    all_match_ids_list = get_matches_returns_list(series_iter)
    for match_id_iter in all_match_ids_list:
      try:
        for innings_iter in [1,2]:
          temp_df = get_one_innings_from_extracted_data(series_iter, match_id_iter, innings_iter)
          temp_df_to_concat = pd.concat([temp_df_to_concat, temp_df])
      except Exception as e:
        print(f'The series {series_iter} - match {match_id_iter} - innings {innings_iter} did not take place')
        continue
  return temp_df_to_concat

def get_series_from_year(year):
  match year:
    case 2008:
       return 313494
    case 2009:
       return 374163
    case 2010:
       return 418064
    case 2011:
       return 466304
    case 2012:
       return 520932
    case 2013:
       return 586733
    case 2014:
       return 695871
    case 2015:
       return 791129
    case 2016:
       return 968923
    case 2017:
       return 1078425
    case 2018:
       return 1131611
    case 2019:
       return 1165643
    case 2020:
       return 1210595
    case 2021:
       return 1249214
    case 2022:
       return 1298423
    case 2023:
       return 1345038

def get_match_ids_from_series(series_id):
  try:
      url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/series/schedule?lang=en&seriesId={series_id}"
      output = requests.get(url)
      matches = output.json()['content']["matches"]
      df = pd.json_normalize(data=matches)
      df.rename(columns={"objectId": "match_id", "slug": "match_name"}, inplace=True)
      matches_id_list=df['match_id'].to_list()
      matches_names_list=[]
      for match_id in matches_id_list:
        url_info = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId={series_id}&matchId={match_id}"
        output_1 = requests.get(url_info)
        team1_sn = output_1.json()['match']['teams'][0]['team']['abbreviation']
        team2_sn = output_1.json()['match']['teams'][1]['team']['abbreviation']
        match_num = output_1.json()['match']['title']
        title = team1_sn + " vs " + team2_sn + " " + match_num
        matches_names_list.append(title)
      match_dict=dict(zip(matches_names_list,matches_id_list))
      return match_dict
        
  except Exception as e:
      traceback.print_exc()

def get_match_ids_from_series_fast(series_id):
    # 2023
    if (series_id == 1345038):
       return { 'CSK vs GT 1st Match': 1359475, 'PBKS vs KKR 2nd Match': 1359476, 'LSG vs DC 3rd Match': 1359477, 'RR vs SRH 4th Match': 1359478, 'MI vs RCB 5th Match': 1359479, 'CSK vs LSG 6th Match': 1359480, 'DC vs GT 7th Match': 1359481, 'PBKS vs RR 8th Match': 1359482, 'KKR vs RCB 9th Match': 1359483, 'SRH vs LSG 10th Match': 1359484, 'RR vs DC 11th Match': 1359485, 'MI vs CSK 12th Match': 1359486, 'GT vs KKR 13th Match': 1359487, 'PBKS vs SRH 14th Match': 1359488, 'RCB vs LSG 15th Match': 1359489, 'DC vs MI 16th Match': 1359490, 'RR vs CSK 17th Match': 1359491, 'PBKS vs GT 18th Match': 1359492, 'SRH vs KKR 19th Match': 1359493, 'RCB vs DC 20th Match': 1359494, 'LSG vs PBKS 21st Match': 1359495, 'KKR vs MI 22nd Match': 1359496, 'GT vs RR 23rd Match': 1359497, 'CSK vs RCB 24th Match': 1359498, 'MI vs SRH 25th Match': 1359499, 'LSG vs RR 26th Match': 1359500, 'RCB vs PBKS 27th Match': 1359501, 'KKR vs DC 28th Match': 1359502, 'SRH vs CSK 29th Match': 1359503, 'GT vs LSG 30th Match': 1359504, 'PBKS vs MI 31st Match': 1359505, 'RCB vs RR 32nd Match': 1359506, 'CSK vs KKR 33rd Match': 1359507, 'DC vs SRH 34th Match': 1359508, 'GT vs MI 35th Match': 1359509, 'KKR vs RCB 36th Match': 1359510, 'RR vs CSK 37th Match': 1359511, 'LSG vs PBKS 38th Match': 1359512, 'KKR vs GT 39th Match': 1359513, 'SRH vs DC 40th Match': 1359514, 'CSK vs PBKS 41st Match': 1359515, 'RR vs MI 42nd Match': 1359516, 'RCB vs LSG 43rd Match': 1359517, 'DC vs GT 44th Match': 1359518, 'LSG vs CSK 45th Match': 1359519, 'PBKS vs MI 46th Match': 1359520, 'KKR vs SRH 47th Match': 1359521, 'RR vs GT 48th Match': 1359522, 'MI vs CSK 49th Match': 1359523, 'RCB vs DC 50th Match': 1359524, 'GT vs LSG 51st Match': 1359525, 'RR vs SRH 52nd Match': 1359526, 'PBKS vs KKR 53rd Match': 1359527, 'RCB vs MI 54th Match': 1359528, 'CSK vs DC 55th Match': 1359529, 'KKR vs RR 56th Match': 1359530, 'MI vs GT 57th Match': 1359531, 'SRH vs LSG 58th Match': 1359532, 'PBKS vs DC 59th Match': 1359533, 'RCB vs RR 60th Match': 1359534, 'CSK vs KKR 61st Match': 1359535, 'GT vs SRH 62nd Match': 1359536, 'LSG vs MI 63rd Match': 1359537, 'DC vs PBKS 64th Match': 1359538, 'SRH vs RCB 65th Match': 1359539, 'PBKS vs RR 66th Match': 1359540, 'CSK vs DC 67th Match': 1359541, 'LSG vs KKR 68th Match': 1359542, 'SRH vs MI 69th Match': 1359543, 'RCB vs GT 70th Match': 1359544, 'CSK vs GT Qualifier 1': 1370350, 'MI vs LSG Eliminator': 1370351, 'GT vs MI Qualifier 2': 1370352, 'GT vs CSK Final': 1370353}
    # 2022
    elif(series_id == 1298423):
      return { 'CSK vs KKR 1st Match': 1304047, 'MI vs DC 2nd Match': 1304048, 'RCB vs PBKS 3rd Match': 1304049, 'LSG vs GT 4th Match': 1304050, 'RR vs SRH 5th Match': 1304051, 'KKR vs RCB 6th Match': 1304052, 'CSK vs LSG 7th Match': 1304053, 'PBKS vs KKR 8th Match': 1304054, 'RR vs MI 9th Match': 1304055, 'GT vs DC 10th Match': 1304056, 'PBKS vs CSK 11th Match': 1304057, 'LSG vs SRH 12th Match': 1304058, 'RR vs RCB 13th Match': 1304059, 'MI vs KKR 14th Match': 1304060, 'DC vs LSG 15th Match': 1304061, 'PBKS vs GT 16th Match': 1304062, 'CSK vs SRH 17th Match': 1304063, 'MI vs RCB 18th Match': 1304064, 'DC vs KKR 19th Match': 1304065, 'RR vs LSG 20th Match': 1304066, 'GT vs SRH 21st Match': 1304067, 'CSK vs RCB 22nd Match': 1304068, 'PBKS vs MI 23rd Match': 1304069, 'GT vs RR 24th Match': 1304070, 'KKR vs SRH 25th Match': 1304071, 'LSG vs MI 26th Match': 1304072, 'RCB vs DC 27th Match': 1304073, 'PBKS vs SRH 28th Match': 1304074, 'CSK vs GT 29th Match': 1304075, 'RR vs KKR 30th Match': 1304076, 'RCB vs LSG 31st Match': 1304077, 'PBKS vs DC 32nd Match': 1304078, 'MI vs CSK 33rd Match': 1304079, 'RR vs DC 34th Match': 1304080, 'GT vs KKR 35th Match': 1304081, 'RCB vs SRH 36th Match': 1304082, 'LSG vs MI 37th Match': 1304083, 'PBKS vs CSK 38th Match': 1304084, 'RR vs RCB 39th Match': 1304085, 'SRH vs GT 40th Match': 1304086, 'KKR vs DC 41st Match': 1304087, 'LSG vs PBKS 42nd Match': 1304088, 'RCB vs GT 43rd Match': 1304089, 'RR vs MI 44th Match': 1304090, 'LSG vs DC 45th Match': 1304091, 'CSK vs SRH 46th Match': 1304092, 'RR vs KKR 47th Match': 1304093, 'GT vs PBKS 48th Match': 1304094, 'RCB vs CSK 49th Match': 1304095, 'DC vs SRH 50th Match': 1304096, 'MI vs GT 51st Match': 1304097, 'PBKS vs RR 52nd Match': 1304098, 'LSG vs KKR 53rd Match': 1304099, 'RCB vs SRH 54th Match': 1304100, 'CSK vs DC 55th Match': 1304101, 'KKR vs MI 56th Match': 1304102, 'GT vs LSG 57th Match': 1304103, 'RR vs DC 58th Match': 1304104, 'CSK vs MI 59th Match': 1304105, 'PBKS vs RCB 60th Match': 1304106, 'KKR vs SRH 61st Match': 1304107, 'CSK vs GT 62nd Match': 1304108, 'RR vs LSG 63rd Match': 1304109, 'DC vs PBKS 64th Match': 1304110, 'SRH vs MI 65th Match': 1304111, 'LSG vs KKR 66th Match': 1304112, 'GT vs RCB 67th Match': 1304113, 'CSK vs RR 68th Match': 1304114, 'DC vs MI 69th Match': 1304115, 'SRH vs PBKS 70th Match': 1304116, 'RR vs GT Qualifier 1': 1312197, 'RCB vs LSG Eliminator': 1312198, 'RCB vs RR Qualifier 2': 1312199, 'RR vs GT Final': 1312200}
    # 2021
    elif(series_id == 1249214):
      return {'MI vs RCB 1st Match': 1254058, 'CSK vs DC 2nd Match': 1254059, 'KKR vs SRH 3rd Match': 1254060, 'PBKS vs RR 4th Match': 1254061, 'MI vs KKR 5th Match': 1254062, 'RCB vs SRH 6th Match': 1254063, 'DC vs RR 7th Match': 1254064, 'PBKS vs CSK 8th Match': 1254065, 'MI vs SRH 9th Match': 1254066, 'RCB vs KKR 10th Match': 1254067, 'PBKS vs DC 11th Match': 1254068, 'CSK vs RR 12th Match': 1254069, 'MI vs DC 13th Match': 1254070, 'PBKS vs SRH 14th Match': 1254071, 'CSK vs KKR 15th Match': 1254072, 'RR vs RCB 16th Match': 1254073, 'MI vs PBKS 17th Match': 1254074, 'KKR vs RR 18th Match': 1254075, 'CSK vs RCB 19th Match': 1254076, 'DC vs SRH 20th Match': 1254077, 'PBKS vs KKR 21st Match': 1254078, 'RCB vs DC 22nd Match': 1254079, 'SRH vs CSK 23rd Match': 1254080, 'RR vs MI 24th Match': 1254081, 'KKR vs DC 25th Match': 1254082, 'PBKS vs RCB 26th Match': 1254083, 'CSK vs MI 27th Match': 1254084, 'RR vs SRH 28th Match': 1254085, 'PBKS vs DC 29th Match': 1254086, 'CSK vs MI 30th Match': 1254104, 'RCB vs KKR 31st Match': 1254087, 'RR vs PBKS 32nd Match': 1254111, 'SRH vs DC 33rd Match': 1254105, 'MI vs KKR 34th Match': 1254096, 'RCB vs CSK 35th Match': 1254113, 'DC vs RR 36th Match': 1254097, 'PBKS vs SRH 37th Match': 1254107, 'KKR vs CSK 38th Match': 1254098, 'RCB vs MI 39th Match': 1254108, 'RR vs SRH 40th Match': 1254100, 'DC vs KKR 41st Match': 1254092, 'PBKS vs MI 42nd Match': 1254099, 'RR vs RCB 43rd Match': 1254103, 'SRH vs CSK 44th Match': 1254091, 'KKR vs PBKS 45th Match': 1254102, 'MI vs DC 46th Match': 1254112, 'CSK vs RR 47th Match': 1254089, 'RCB vs PBKS 48th Match': 1254090, 'SRH vs KKR 49th Match': 1254109, 'CSK vs DC 50th Match': 1254110, 'RR vs MI 51st Match': 1254093, 'SRH vs RCB 52nd Match': 1254095, 'CSK vs PBKS 53rd Match': 1254094, 'KKR vs RR 54th Match': 1254106, 'DC vs RCB 56th Match': 1254101, 'MI vs SRH 55th Match': 1254088, 'DC vs CSK Qualifier 1': 1254114, 'RCB vs KKR Eliminator': 1254115, 'DC vs KKR Qualifier 2': 1254116, 'CSK vs KKR Final': 1254117 }
    # 2020
    elif(series_id == 1210595):
      return { 'MI vs CSK 1st Match': 1216492, 'DC vs KXIP 2nd Match': 1216493, 'RCB vs SRH 3rd Match': 1216534, 'RR vs CSK 4th Match': 1216496, 'MI vs KKR 5th Match': 1216508, 'KXIP vs RCB 6th Match': 1216510, 'DC vs CSK 7th Match': 1216539, 'SRH vs KKR 8th Match': 1216545, 'KXIP vs RR 9th Match': 1216527, 'RCB vs MI 10th Match': 1216547, 'SRH vs DC 11th Match': 1216532, 'KKR vs RR 12th Match': 1216504, 'MI vs KXIP 13th Match': 1216503, 'SRH vs CSK 14th Match': 1216516, 'RR vs RCB 15th Match': 1216514, 'DC vs KKR 16th Match': 1216515, 'MI vs SRH 17th Match': 1216538, 'KXIP vs CSK 18th Match': 1216513, 'DC vs RCB 19th Match': 1216519, 'MI vs RR 20th Match': 1216511, 'KKR vs CSK 21st Match': 1216501, 'SRH vs KXIP 22nd Match': 1216542, 'DC vs RR 23rd Match': 1216500, 'KKR vs KXIP 24th Match': 1216523, 'RCB vs CSK 25th Match': 1216525, 'SRH vs RR 26th Match': 1216507, 'DC vs MI 27th Match': 1216529, 'RCB vs KKR 28th Match': 1216540, 'CSK vs SRH 29th Match': 1216528, 'DC vs RR 30th Match': 1216543, 'RCB vs KXIP 31st Match': 1216531, 'KKR vs MI 32nd Match': 1216526, 'RR vs RCB 33rd Match': 1216522, 'CSK vs DC 34th Match': 1216509, 'KKR vs SRH 35th Match': 1216512, 'MI vs KXIP 36th Match': 1216517, 'CSK vs RR 37th Match': 1216533, 'DC vs KXIP 38th Match': 1216546, 'KKR vs RCB 39th Match': 1216494, 'RR vs SRH 40th Match': 1216518, 'CSK vs MI 41st Match': 1216521, 'KKR vs DC 42nd Match': 1216497, 'KXIP vs SRH 43rd Match': 1216498, 'RCB vs CSK 44th Match': 1216544, 'MI vs RR 45th Match': 1216541, 'KKR vs KXIP 46th Match': 1216520, 'SRH vs DC 47th Match': 1216524, 'RCB vs MI 48th Match': 1216499, 'KKR vs CSK 49th Match': 1216536, 'KXIP vs RR 50th Match': 1216537, 'DC vs MI 51st Match': 1216535, 'RCB vs SRH 52nd Match': 1216502, 'KXIP vs CSK 53rd Match': 1216506, 'KKR vs RR 54th Match': 1216530, 'RCB vs DC 55th Match': 1216505, 'MI vs SRH 56th Match': 1216495, 'MI vs DC Qualifier 1': 1237177, 'RCB vs SRH Eliminator': 1237178, 'DC vs SRH Qualifier 2': 1237180, 'DC vs MI Final': 1237181 }
    # 2019
    elif(series_id == 1165643):
      return { 'RCB vs CSK 1st Match': 1175356, 'SRH vs KKR 2nd Match': 1175357, 'DC vs MI 3rd Match': 1175358, 'KXIP vs RR 4th Match': 1175359, 'DC vs CSK 5th Match': 1175360, 'KKR vs KXIP 6th Match': 1175361, 'MI vs RCB 7th Match': 1175362, 'RR vs SRH 8th Match': 1175363, 'MI vs KXIP 9th Match': 1175364, 'KKR vs DC 10th Match': 1175365, 'SRH vs RCB 11th Match': 1175366, 'CSK vs RR 12th Match': 1175367, 'KXIP vs DC 13th Match': 1175368, 'RCB vs RR 14th Match': 1175369, 'MI vs CSK 15th Match': 1175370, 'DC vs SRH 16th Match': 1175371, 'RCB vs KKR 17th Match': 1175372, 'CSK vs KXIP 18th Match': 1178393, 'MI vs SRH 19th Match': 1178394, 'RCB vs DC 20th Match': 1178395, 'RR vs KKR 21st Match': 1178396, 'SRH vs KXIP 22nd Match': 1178397, 'KKR vs CSK 23rd Match': 1178398, 'KXIP vs MI 24th Match': 1178399, 'RR vs CSK 25th Match': 1178400, 'KKR vs DC 26th Match': 1178401, 'MI vs RR 27th Match': 1178402, 'KXIP vs RCB 28th Match': 1178403, 'KKR vs CSK 29th Match': 1178404, 'DC vs SRH 30th Match': 1178405, 'RCB vs MI 31st Match': 1178406, 'KXIP vs RR 32nd Match': 1178407, 'CSK vs SRH 33rd Match': 1178408, 'MI vs DC 34th Match': 1178409, 'RCB vs KKR 35th Match': 1178410, 'MI vs RR 36th Match': 1178411, 'KXIP vs DC 37th Match': 1178412, 'KKR vs SRH 38th Match': 1178413, 'RCB vs CSK 39th Match': 1178414, 'RR vs DC 40th Match': 1178415, 'SRH vs CSK 41st Match': 1178416, 'RCB vs KXIP 42nd Match': 1178417, 'KKR vs RR 43rd Match': 1178418, 'MI vs CSK 44th Match': 1178419, 'SRH vs RR 45th Match': 1178420, 'DC vs RCB 46th Match': 1178421, 'KKR vs MI 47th Match': 1178422, 'SRH vs KXIP 48th Match': 1178423, 'RCB vs RR 49th Match': 1178424, 'CSK vs DC 50th Match': 1178425, 'MI vs SRH 51st Match': 1178426, 'KXIP vs KKR 52nd Match': 1178427, 'RR vs DC 53rd Match': 1178428, 'SRH vs RCB 54th Match': 1178429, 'CSK vs KXIP 55th Match': 1178430, 'KKR vs MI 56th Match': 1178431, 'CSK vs MI Qualifier 1': 1181764, 'SRH vs DC Eliminator': 1181766, 'DC vs CSK Qualifier 2': 1181767, 'MI vs CSK Final': 1181768 }
    # 2018
    elif(series_id == 1131611):
      return { 'MI vs CSK 1st match': 1136561, 'DC vs KXIP 2nd match': 1136562, 'RCB vs KKR 3rd match': 1136563, 'RR vs SRH 4th match': 1136564, 'KKR vs CSK 5th match': 1136565, 'RR vs DC 6th match': 1136566, 'MI vs SRH 7th match': 1136567, 'KXIP vs RCB 8th match': 1136568, 'MI vs DC 9th match': 1136569, 'KKR vs SRH 10th match': 1136570, 'RR vs RCB 11th match': 1136571, 'KXIP vs CSK 12th match': 1136572, 'KKR vs DC 13th match': 1136573, 'MI vs RCB 14th match': 1136574, 'RR vs KKR 15th match': 1136575, 'KXIP vs SRH 16th match': 1136576, 'CSK vs RR 17th match': 1136577, 'KKR vs KXIP 18th match': 1136578, 'DC vs RCB 19th match': 1136579, 'CSK vs SRH 20th match': 1136580, 'MI vs RR 21st match': 1136581, 'KXIP vs DC 22nd match': 1136582, 'SRH vs MI 23rd match': 1136583, 'RCB vs CSK 24th match': 1136584, 'SRH vs KXIP 25th match': 1136585, 'DC vs KKR 26th match': 1136586, 'CSK vs MI 27th match': 1136587, 'SRH vs RR 28th match': 1136588, 'RCB vs KKR 29th match': 1136589, 'CSK vs DC 30th match': 1136590, 'RCB vs MI 31st match': 1136591, 'DC vs RR 32nd match': 1136592, 'CSK vs KKR 33rd match': 1136593, 'KXIP vs MI 34th match': 1136594, 'RCB vs CSK 35th match': 1136595, 'DC vs SRH 36th match': 1136596, 'MI vs KKR 37th match': 1136597, 'RR vs KXIP 38th match': 1136598, 'SRH vs RCB 39th match': 1136599, 'RR vs KXIP 40th match': 1136600, 'MI vs KKR 41st match': 1136601, 'DC vs SRH 42nd match': 1136602, 'CSK vs RR 43rd match': 1136603, 'KKR vs KXIP 44th match': 1136604, 'DC vs RCB 45th match': 1136605, 'SRH vs CSK 46th match': 1136606, 'MI vs RR 47th match': 1136607, 'KXIP vs RCB 48th match': 1136608, 'RR vs KKR 49th match': 1136609, 'MI vs KXIP 50th match': 1136610, 'RCB vs SRH 51st match': 1136611, 'DC vs CSK 52nd match': 1136612, 'RR vs RCB 53rd match': 1136613, 'SRH vs KKR 54th match': 1136614, 'DC vs MI 55th match': 1136615, 'KXIP vs CSK 56th match': 1136616, 'SRH vs CSK Qualifier 1': 1136617, 'KKR vs RR Eliminator': 1136618, 'SRH vs KKR Qualifier 2': 1136619, 'SRH vs CSK Final': 1136620 } 
    # 2017
    elif(series_id == 1078425):
      return { 'SRH vs RCB 1st match': 1082591, 'MI vs RPS 2nd match': 1082592, 'GL vs KKR 3rd match': 1082593, 'RPS vs KXIP 4th match': 1082594, 'RCB vs DC 5th match': 1082595, 'GL vs SRH 6th match': 1082596, 'KKR vs MI 7th match': 1082597, 'RCB vs KXIP 8th match': 1082598, 'DC vs RPS 9th match': 1082599, 'SRH vs MI 10th match': 1082600, 'KXIP vs KKR 11th match': 1082601, 'RCB vs MI 12th match': 1082602, 'RPS vs GL 13th match': 1082603, 'KKR vs SRH 14th match': 1082604, 'DC vs KXIP 15th match': 1082605, 'GL vs MI 16th match': 1082606, 'RPS vs RCB 17th match': 1082607, 'DC vs KKR 18th match': 1082608, 'SRH vs KXIP 19th match': 1082609, 'RCB vs GL 20th match': 1082610, 'SRH vs DC 21st match': 1082611, 'KXIP vs MI 22nd match': 1082612, 'KKR vs GL 23rd match': 1082613, 'SRH vs RPS 24th match': 1082615, 'MI vs DC 25th match': 1082614, 'KXIP vs GL 26th match': 1082616, 'KKR vs RCB 27th match': 1082617, 'RPS vs MI 28th match': 1082618, 'RCB vs SRH 29th match': 1082619, 'RPS vs KKR 30th match': 1082620, 'RCB vs GL 31st match': 1082621, 'DC vs KKR 32nd match': 1082622, 'SRH vs KXIP 33rd match': 1082623, 'RPS vs RCB 34th match': 1082624, 'GL vs MI 35th match': 1082625, 'DC vs KXIP 36th match': 1082626, 'SRH vs KKR 37th match': 1082627, 'RCB vs MI 38th match': 1082628, 'GL vs RPS 39th match': 1082629, 'SRH vs DC 40th match': 1082630, 'KKR vs RPS 41st match': 1082631, 'GL vs DC 42nd match': 1082632, 'KXIP vs RCB 43rd match': 1082633, 'RPS vs SRH 44th match': 1082634, 'MI vs DC 45th match': 1082635, 'RCB vs KKR 46th match': 1082636, 'KXIP vs GL 47th match': 1082637, 'MI vs SRH 48th match': 1082638, 'KXIP vs KKR 49th match': 1082639, 'GL vs DC 50th match': 1082640, 'KXIP vs MI 51st match': 1082641, 'DC vs RPS 52nd match': 1082642, 'GL vs SRH 53rd match': 1082643, 'MI vs KKR 54th match': 1082644, 'KXIP vs RPS 55th match': 1082645, 'RCB vs DC 56th match': 1082646, 'RPS vs MI Qualifier 1': 1082647, 'SRH vs KKR Eliminator': 1082648, 'KKR vs MI Qualifier 2': 1082649, 'MI vs RPS Final': 1082650 }
    # 2016
    elif(series_id == 968923):
      return { 'MI vs RPS 1st match': 980901,'DC vs KKR 2nd match': 980903,'KXIP vs GL 3rd match': 980905,'RCB vs SRH 4th match': 980907,'KKR vs MI 5th match': 980909,'RPS vs GL 6th match': 980911,'KXIP vs DC 7th match': 980913,'SRH vs KKR 8th match': 980915,'MI vs GL 9th match': 980917,'RPS vs KXIP 10th match': 980919,'RCB vs DC 11th match': 980921,'MI vs SRH 12th match': 980923,'KXIP vs KKR 13th match': 980925,'RCB vs MI 14th match': 980927,'GL vs SRH 15th match': 980929,'RCB vs RPS 16th match': 980931,'DC vs MI 17th match': 980933,'KXIP vs SRH 18th match': 980935,'RCB vs GL 19th match': 980937,'RPS vs KKR 20th match': 980939,'MI vs KXIP 21st match': 980941,'SRH vs RPS 22nd match': 980943,'GL vs DC 23rd match': 980945,'KKR vs MI 24th match': 980947,'RPS vs GL 25th match': 980949,'DC vs KKR 26th match': 980951,'SRH vs RCB 27th match': 980953,'KXIP vs GL 28th match': 980955,'RPS vs MI 29th match': 980957,'RCB vs KKR 30th match': 980959,'GL vs DC 31st match': 980961,'KKR vs KXIP 32nd match': 980963,'DC vs RPS 33rd match': 980965,'GL vs SRH 34th match': 980967,'RPS vs RCB 35th match': 980969,'KXIP vs DC 36th match': 980971,'SRH vs MI 37th match': 980973,'KKR vs GL 38th match': 980975,'RCB vs KXIP 39th match': 980977,'SRH vs RPS 40th match': 980979,'RCB vs MI 41st match': 980981,'SRH vs DC 42nd match': 980983,'MI vs KXIP 43rd match': 980985,'RCB vs GL 44th match': 980987,'RPS vs KKR 45th match': 980989,'KXIP vs SRH 46th match': 980991,'MI vs DC 47th match': 980993,'KKR vs RCB 48th match': 980995,'DC vs RPS 49th match': 980997,'RCB vs KXIP 50th match': 980999,'KKR vs GL 51st match': 981001,'SRH vs DC 52nd match': 981003,'KXIP vs RPS 53rd match': 981005,'MI vs GL 54th match': 981007,'KKR vs SRH 55th match': 981009,'DC vs RCB 56th match': 981011,'GL vs RCB Qualifier 1': 981013,'SRH vs KKR Eliminator': 981015,'GL vs SRH Qualifier 2': 981017,'SRH vs RCB Final': 981019}
    # 2015
    elif(series_id == 791129):
      return { 'MI vs KKR 1st match': 829705, 'CSK vs DC 2nd match': 829707, 'RR vs KXIP 3rd match': 829709, 'CSK vs SRH 4th match': 829711, 'KKR vs RCB 5th match': 829713, 'DC vs RR 6th match': 829715, 'KXIP vs MI 7th match': 829717, 'RCB vs SRH 8th match': 829719, 'MI vs RR 9th match': 829721, 'KXIP vs DC 10th match': 829725, 'SRH vs RR 11th match': 829727, 'MI vs CSK 12th match': 829729, 'DC vs SRH 13th match': 829731, 'KXIP vs KKR 14th match': 829733, 'CSK vs RR 15th match': 829735, 'MI vs RCB 16th match': 829737, 'DC vs KKR 17th match': 829739, 'RR vs KXIP 18th match': 829741, 'SRH vs KKR 19th match': 829743, 'CSK vs RCB 20th match': 829745, 'DC vs MI 21st match': 829747, 'RR vs RCB 22nd match': 829749, 'MI vs SRH 23rd match': 829751, 'CSK vs KXIP 24th match': 829753, 'KKR vs RR 25th match': 829755, 'DC vs RCB 26th match': 829757, 'SRH vs KXIP 27th match': 829759, 'CSK vs KKR 28th match': 829765, 'RCB vs RR 29th match': 829763, 'CSK vs KKR 30th match': 829723, 'KXIP vs DC 31st match': 829767, 'MI vs RR 32nd match': 829769, 'KKR vs RCB 33rd match': 829771, 'SRH vs CSK 34th match': 829773, 'MI vs KXIP 35th match': 829775, 'RR vs DC 36th match': 829777, 'CSK vs RCB 37th match': 829779, 'KKR vs SRH 38th match': 829781, 'DC vs MI 39th match': 829783, 'RCB vs KXIP 40th match': 829785, 'SRH vs RR 41st match': 829787, 'KKR vs DC 42nd match': 829761, 'CSK vs MI 43rd match': 829789, 'KXIP vs KKR 44th match': 829791, 'SRH vs DC 45th match': 829793, 'RCB vs MI 46th match': 829795, 'CSK vs RR 47th match': 829797, 'SRH vs KXIP 48th match': 829799, 'CSK vs DC 49th match': 829801, 'KXIP vs RCB 50th match': 829803, 'MI vs KKR 51st match': 829805, 'SRH vs RCB 52nd match': 829807, 'KXIP vs CSK 53rd match': 829809, 'RR vs KKR 54th match': 829811, 'DC vs RCB 55th match': 829813, 'SRH vs MI 56th match': 829815, 'MI vs CSK Qualifier 1': 829817, 'RCB vs RR Eliminator': 829819, 'RCB vs CSK Qualifier 2': 829821, 'MI vs CSK Final': 829823 }
    # 2014
    elif(series_id == 695871):
      return { 'KKR vs MI 1st match': 729279, 'DC vs RCB 2nd match': 729281, 'CSK vs KXIP 3rd match': 729283, 'SRH vs RR 4th match': 729285, 'MI vs RCB 5th match': 729287, 'KKR vs DC 6th match': 729289, 'RR vs KXIP 7th match': 729291, 'CSK vs DC 8th match': 729293, 'KXIP vs SRH 9th match': 729295, 'CSK vs RR 10th match': 729297, 'KKR vs RCB 11th match': 729299, 'SRH vs DC 12th match': 729301, 'MI vs CSK 13th match': 729303, 'RCB vs RR 14th match': 729305, 'KXIP vs KKR 15th match': 729307, 'MI vs DC 16th match': 729309, 'SRH vs CSK 17th match': 729311, 'RCB vs KXIP 18th match': 729313, 'RR vs KKR 19th match': 729315, 'SRH vs MI 20th match': 729317, 'CSK vs KKR 21st match': 733971, 'KXIP vs MI 22nd match': 733973, 'DC vs RR 23rd match': 733975, 'SRH vs RCB 24th match': 733977, 'RR vs KKR 25th match': 733979, 'DC vs CSK 26th match': 733981, 'MI vs RCB 27th match': 733983, 'DC vs KKR 28th match': 733985, 'KXIP vs CSK 29th match': 733987, 'SRH vs RR 30th match': 733989, 'KXIP vs RCB 31st match': 733991, 'DC vs SRH 32nd match': 733993, 'MI vs CSK 33rd match': 733995, 'KXIP vs KKR 34th match': 733997, 'RCB vs RR 35th match': 733999, 'SRH vs MI 36th match': 734001, 'RR vs CSK 37th match': 734003, 'RCB vs DC 38th match': 734005, 'SRH vs KXIP 39th match': 734007, 'MI vs KKR 40th match': 734009, 'RR vs DC 41st match': 734011, 'CSK vs RCB 42nd match': 734013, 'SRH vs KKR 43rd match': 734015, 'MI vs RR 44th match': 734017, 'DC vs KXIP 45th match': 734019, 'RCB vs SRH 46th match': 734021, 'CSK vs KKR 47th match': 734023, 'KXIP vs MI 48th match': 734025, 'KKR vs RCB 49th match': 734027, 'CSK vs SRH 50th match': 734029, 'MI vs DC 51st match': 734031, 'KXIP vs RR 52nd match': 734033, 'RCB vs CSK 53rd match': 734035, 'SRH vs KKR 54th match': 734037, 'DC vs KXIP 55th match': 734039, 'RR vs MI 56th match': 734041, 'KKR vs KXIP Qualifier 1': 734043, 'MI vs CSK Eliminator': 734045, 'KXIP vs CSK Qualifier 2': 734047, 'KXIP vs KKR Final': 734049}
    # 2013
    elif(series_id == 586733):
      return { 'DC vs KKR 1st match': 597998, 'RCB vs MI 2nd match': 597999, 'SRH vs PWI 3rd match': 598000, 'RR vs DC 4th match': 598001, 'MI vs CSK 5th match': 598002, 'PWI vs KXIP 6th match': 598003, 'RCB vs SRH 7th match': 598004, 'RR vs KKR 8th match': 598005, 'SRH vs RCB 9th match': 598048, 'MI vs DC 10th match': 598006, 'KXIP vs CSK 11th match': 598007, 'KKR vs RCB 12th match': 598008, 'RR vs PWI 13th match': 598009, 'DC vs SRH 14th match': 598010, 'MI vs PWI 15th match': 598011, 'RCB vs CSK 16th match': 598012, 'KKR vs SRH 17th match': 598013, 'KXIP vs RR 18th match': 598014, 'PWI vs CSK 19th match': 598015, 'KXIP vs KKR 20th match': 598016, 'DC vs RCB 21st match': 598017, 'SRH vs PWI 22nd match': 598018, 'RR vs MI 23rd match': 598019, 'CSK vs DC 24th match': 598020, 'KXIP vs SRH 25th match': 598021, 'KKR vs CSK 26th match': 598022, 'RR vs RCB 27th match': 598023, 'MI vs DC 28th match': 598024, 'PWI vs KXIP 29th match': 598025, 'RR vs CSK 30th match': 598026, 'RCB vs PWI 31st match': 598027, 'DC vs KXIP 32nd match': 598059, 'KKR vs MI 33rd match': 598029, 'SRH vs CSK 34th match': 598030, 'KXIP vs KKR 35th match': 598031, 'SRH vs RR 36th match': 598032, 'MI vs RCB 37th match': 598033, 'CSK vs KKR 38th match': 598034, 'DC vs PWI 39th match': 598035, 'RCB vs RR 40th match': 598036, 'MI vs KXIP 41st match': 598037, 'CSK vs PWI 42nd match': 598038, 'MI vs SRH 43rd match': 598039, 'KKR vs DC 44th match': 598040, 'CSK vs KXIP 45th match': 598041, 'RCB vs PWI 46th match': 598042, 'RR vs KKR 47th match': 598043, 'DC vs SRH 48th match': 598044, 'MI vs CSK 49th match': 598046, 'PWI vs RR 50th match': 598047, 'RCB vs KXIP 51st match': 598064, 'DC vs RR 52nd match': 598049, 'MI vs KKR 53rd match': 598050, 'CSK vs SRH 54th match': 598051, 'KXIP vs RR 55th match': 598052, 'KKR vs PWI 56th match': 598053, 'RCB vs DC 57th match': 598054, 'PWI vs MI 58th match': 598055, 'SRH vs KXIP 59th match': 598056, 'RCB vs KKR 60th match': 598057, 'CSK vs RR 61st match': 598058, 'SRH vs MI 62nd match': 598060, 'RCB vs KXIP 63rd match': 598045, 'CSK vs DC 64th match': 598062, 'PWI vs KKR 65th match': 598061, 'MI vs RR 66th match': 598063, 'KXIP vs DC 67th match': 598028, 'SRH vs RR 68th match': 598065, 'KXIP vs MI 69th match': 598066, 'RCB vs CSK 70th match': 598068, 'PWI vs DC 71st match': 598067, 'KKR vs SRH 72nd match': 598069, 'CSK vs MI Qualifier 1': 598070, 'SRH vs RR Eliminator': 598071, 'RR vs MI Qualifier 2': 598072, 'MI vs CSK Final': 598073}
    # 2012
    elif(series_id == 520932):
      return { 'CSK vs MI 1st match': 548306, 'KKR vs DC 2nd match': 548307, 'PWI vs MI 3rd match': 548308, 'RR vs KXIP 4th match': 548309, 'RCB vs DC 5th match': 548310, 'CSK vs DC 6th match': 548311, 'RR vs KKR 7th match': 548312, 'PWI vs KXIP 8th match': 548313, 'DC vs MI 9th match': 548314, 'KKR vs RCB 10th match': 548315, 'CSK vs DC 11th match': 548316, 'MI vs RR 12th match': 548317, 'RCB vs CSK 13th match': 548318, 'PWI vs KXIP 14th match': 548319, 'RR vs KKR 15th match': 548320, 'CSK vs PWI 16th match': 548322, 'KXIP vs KKR 17th match': 548323, 'RR vs RCB 18th match': 548324, 'MI vs DC 19th match': 548325, 'DC vs RR 20th match': 548326, 'PWI vs RCB 21st match': 548327, 'KXIP vs KKR 22nd match': 548328, 'DC vs DC 23rd match': 548321, 'CSK vs PWI 24th match': 548330, 'KXIP vs RCB 25th match': 548331, 'RR vs CSK 26th match': 548332, 'PWI vs DC 27th match': 548333, 'MI vs KXIP 28th match': 548334, 'DC vs KKR 29th match': 548335, 'RCB vs RR 30th match': 548336, 'PWI vs DC 31st match': 548337, 'KKR vs DC 32nd match': 548338, 'KXIP vs MI 33rd match': 548339, 'RCB vs CSK 34th match': 548340, 'DC vs PWI 35th match': 548341, 'DC vs MI 36th match': 548342, 'KXIP vs CSK 37th match': 548343, 'KKR vs RCB 38th match': 548344, 'DC vs RR 39th match': 548345, 'DC vs MI 40th match': 548346, 'CSK vs KKR 41st match': 548347, 'DC vs PWI 42nd match': 548348, 'RR vs DC 43rd match': 548349, 'RCB vs KXIP 44th match': 548350, 'MI vs PWI 45th match': 548351, 'CSK vs DC 46th match': 548352, 'KKR vs PWI 47th match': 548353, 'RR vs KXIP 48th match': 548354, 'CSK vs MI 49th match': 548355, 'DC vs RCB 50th match': 548356, 'DC vs KKR 51st match': 548357, 'PWI vs RR 52nd match': 548358, 'KXIP vs DC 53rd match': 548359, 'MI vs RCB 54th match': 548360, 'DC vs DC 55th match': 548329, 'RR vs CSK 56th match': 548361, 'RCB vs PWI 57th match': 548362, 'MI vs KKR 58th match': 548363, 'DC vs CSK 59th match': 548364, 'RR vs PWI 60th match': 548365, 'DC vs KXIP 61st match': 548366, 'RCB vs MI 62nd match': 548367, 'KKR vs CSK 63rd match': 548368, 'KXIP vs DC 64th match': 548369, 'KKR vs MI 65th match': 548370, 'CSK vs KXIP 66th match': 548371, 'RCB vs DC 67th match': 548372, 'RR vs DC 68th match': 548373, 'KXIP vs DC 69th match': 548374, 'KKR vs PWI 70th match': 548375, 'DC vs RCB 71st match': 548376, 'RR vs MI 72nd match': 548377, 'KKR vs DC 1st Qualifying Match': 548378, 'CSK vs MI Elimination Final': 548379, 'CSK vs DC 2nd Qualifying Match': 548380, 'CSK vs KKR Final': 548381 }
    # 2011
    elif(series_id == 466304):
      return { 'CSK vs KKR 1st match': 501198, 'DC vs RR 2nd match': 501199, 'Kochi vs RCB 3rd match': 501200, 'DC vs MI 4th match': 501201, 'KXIP vs PWI 5th match': 501202, 'KKR vs DC 6th match': 501203, 'DC vs RR 7th match': 501204, 'RCB vs MI 8th match': 501205, 'CSK vs KXIP 9th match': 501206, 'Kochi vs PWI 10th match': 501207, 'DC vs RCB 11th match': 501208, 'RR vs KKR 12th match': 501209, 'MI vs Kochi 13th match': 501210, 'CSK vs RCB 14th match': 501211, 'DC vs KXIP 15th match': 501212, 'PWI vs DC 16th match': 501213, 'RR vs KKR 17th match': 501214, 'CSK vs Kochi 18th match': 501215, 'DC vs DC 19th match': 501216, 'RCB vs RR 20th match': 501217, 'PWI vs MI 21st match': 501218, 'Kochi vs KKR 22nd match': 501219, 'KXIP vs RR 23rd match': 501220, 'KKR vs RCB 24th match': 501222, 'MI vs CSK 25th match': 501221, 'DC vs KXIP 26th match': 501223, 'MI vs DC 27th match': 501224, 'Kochi vs RR 28th match': 501225, 'CSK vs PWI 29th match': 501226, 'DC vs RCB 30th match': 501227, 'PWI vs CSK 31st match': 501228, 'DC vs Kochi 32nd match': 501229, 'KKR vs DC 33rd match': 501230, 'MI vs RR 34th match': 501231, 'RCB vs PWI 35th match': 501232, 'DC vs Kochi 36th match': 501233, 'KXIP vs KKR 37th match': 501234, 'PWI vs RR 38th match': 501235, 'CSK vs DC 39th match': 501236, 'MI vs KXIP 40th match': 501237, 'DC vs Kochi 41st match': 501238, 'KKR vs DC 42nd match': 501239, 'RR vs CSK 43rd match': 501240, 'MI vs PWI 44th match': 501241, 'Kochi vs KKR 45th match': 501242, 'DC vs DC 46th match': 501243, 'RCB vs KXIP 47th match': 501244, 'CSK vs KKR 48th match': 501245, 'MI vs DC 49th match': 501246, 'Kochi vs RCB 50th match': 501247, 'KXIP vs PWI 51st match': 501248, 'CSK vs RR 52nd match': 501249, 'DC vs PWI 53rd match': 501250, 'KXIP vs MI 54th match': 501251, 'RR vs RCB 55th match': 501252, 'CSK vs DC 56th match': 501253, 'Kochi vs KXIP 57th match': 501254, 'KKR vs RCB 58th match': 501255, 'DC vs MI 59th match': 501256, 'KXIP vs DC 60th match': 501257, 'RR vs Kochi 61st match': 501258, 'PWI vs DC 62nd match': 501259, 'KXIP vs RCB 63rd match': 501260, 'CSK vs Kochi 64th match': 501261, 'PWI vs KKR 65th match': 501262, 'MI vs RR 66th match': 501263, 'DC vs KXIP 67th match': 501264, 'DC vs PWI 68th match': 501265, 'CSK vs RCB 69th match': 501266, 'KKR vs MI 70th match': 501267, 'RCB vs CSK 1st Qualifying Final': 501268, 'KKR vs MI Elimination Final': 501269, 'RCB vs MI 2nd Qualifying Final': 501270, 'CSK vs RCB Final': 501271}
    # 2010
    elif(series_id == 418064):
      return { 'KKR vs DC 1st match': 419106, 'MI vs RR 2nd match': 419107, 'KXIP vs DC 3rd match': 419108, 'RCB vs KKR 4th match': 419109, 'DC vs CSK 5th match': 419110, 'RR vs DC 6th match': 419111, 'KXIP vs RCB 7th match': 419112, 'CSK vs KKR 8th match': 419113, 'MI vs DC 9th match': 419114, 'RR vs RCB 10th match': 419115, 'DC vs CSK 11th match': 419116, 'DC vs KXIP 12th match': 419117, 'RR vs KKR 13th match': 419118, 'MI vs RCB 14th match': 419119, 'DC vs DC 15th match': 419120, 'KXIP vs CSK 16th match': 419121, 'KKR vs MI 17th match': 419122, 'RCB vs CSK 18th match': 419123, 'RR vs KXIP 19th match': 419124, 'DC vs RCB 20th match': 419128, 'CSK vs MI 21st match': 419125, 'DC vs RR 22nd match': 419126, 'KKR vs KXIP 23rd match': 419127, 'RR vs CSK 24th match': 419129, 'MI vs DC 25th match': 419130, 'DC vs KKR 26th match': 419131, 'KXIP vs MI 27th match': 419132, 'RCB vs CSK 28th match': 419133, 'DC vs RR 29th match': 419134, 'KKR vs DC 30th match': 419135, 'KXIP vs RCB 31st match': 419136, 'CSK vs RR 32nd match': 419137, 'MI vs DC 33rd match': 419138, 'KKR vs KXIP 34th match': 419139, 'DC vs RCB 35th match': 419140, 'RR vs DC 36th match': 419141, 'CSK vs MI 37th match': 419142, 'KXIP vs RR 38th match': 419143, 'KKR vs DC 39th match': 419144, 'RCB vs DC 40th match': 419145, 'MI vs KXIP 41st match': 419146, 'CSK vs DC 42nd match': 419147, 'KKR vs RCB 43rd match': 419148, 'DC vs KXIP 44th match': 419149, 'MI vs RR 45th match': 419150, 'DC vs RCB 46th match': 419151, 'MI vs DC 47th match': 419152, 'KKR vs CSK 48th match': 419153, 'RR vs RCB 49th match': 419154, 'CSK vs DC 50th match': 419155, 'KXIP vs DC 51st match': 419156, 'MI vs RCB 52nd match': 419157, 'RR vs KKR 53rd match': 419158, 'KXIP vs CSK 54th match': 419159, 'DC vs DC 55th match': 419160, 'MI vs KKR 56th match': 419161, 'MI vs RCB 1st Semi-Final': 419162, 'CSK vs DC 2nd Semi-Final': 419163, 'DC vs RCB 3rd Place Play-off': 419164, 'CSK vs MI Final': 419165 }
    # 2009
    elif(series_id == 374163):
      return { 'MI vs CSK 1st match': 392181, 'RCB vs RR 2nd match': 392182, 'KXIP vs DC 3rd match': 392183, 'KKR vs DC 4th match': 392184, 'CSK vs RCB 5th match': 392185, 'KXIP vs KKR 6th match': 392186, 'MI vs RR 7th match': 392187, 'DC vs RCB 8th match': 392188, 'DC vs CSK 9th match': 392189, 'RR vs KKR 10th match': 392190, 'RCB vs KXIP 11th match': 392191, 'DC vs MI 12th match': 392192, 'CSK vs KKR 13th match': 392193, 'RCB vs DC 14th match': 392194, 'KXIP vs RR 15th match': 392195, 'CSK vs DC 16th match': 392196, 'MI vs KKR 17th match': 392197, 'DC vs RR 18th match': 392198, 'KKR vs RCB 19th match': 392199, 'KXIP vs MI 20th match': 392200, 'DC vs DC 21st match': 392201, 'CSK vs RR 22nd match': 392202, 'MI vs KKR 23rd match': 392203, 'RCB vs KXIP 24th match': 392204, 'DC vs RR 25th match': 392205, 'CSK vs DC 26th match': 392206, 'KKR vs KXIP 27th match': 392207, 'MI vs RCB 28th match': 392208, 'CSK vs DC 29th match': 392209, 'RR vs KXIP 30th match': 392210, 'KKR vs DC 31st match': 392211, 'DC vs MI 32nd match': 392212, 'RCB vs RR 33rd match': 392213, 'CSK vs KXIP 34th match': 392214, 'MI vs DC 35th match': 392215, 'DC vs KXIP 36th match': 392216, 'RR vs CSK 37th match': 392217, 'MI vs RCB 38th match': 392218, 'KKR vs DC 39th match': 392219, 'DC vs RR 40th match': 392220, 'KKR vs RCB 41st match': 392221, 'KXIP vs MI 42nd match': 392222, 'DC vs DC 43rd match': 392223, 'CSK vs RCB 44th match': 392224, 'RR vs MI 45th match': 392225, 'DC vs KXIP 46th match': 392226, 'MI vs CSK 47th match': 392227, 'KKR vs DC 48th match': 392228, 'KXIP vs DC 49th match': 392229, 'DC vs RR 50th match': 392230, 'CSK vs KKR 51st match': 392231, 'DC vs RCB 52nd match': 392232, 'RR vs KKR 53rd match': 392233, 'CSK vs KXIP 54th match': 392234, 'MI vs DC 55th match': 392235, 'RCB vs DC 56th match': 392236, 'DC vs DC 1st Semi-Final': 392237, 'CSK vs RCB 2nd Semi-Final': 392238, 'DC vs RCB Final': 392239 }
    # 2008
    elif(series_id == 313494):
      return { 'KKR vs RCB 1st match': 335982, 'CSK vs KXIP 2nd match': 335983, 'RR vs DC 3rd match': 335984, 'DC vs KKR 4th match': 335986, 'MI vs RCB 5th match': 335985, 'KXIP vs RR 6th match': 335987, 'DC vs DC 7th match': 335988, 'CSK vs MI 8th match': 335989, 'DC vs RR 9th match': 335990, 'KXIP vs MI 10th match': 335991, 'KKR vs CSK 11th match': 335993, 'RCB vs RR 12th match': 335992, 'DC vs KXIP 13th match': 335995, 'MI vs DC 14th match': 335994, 'CSK vs RCB 15th match': 335996, 'KKR vs MI 16th match': 335997, 'DC vs RCB 17th match': 335998, 'RR vs KKR 18th match': 336000, 'DC vs KXIP 19th match': 335999, 'CSK vs DC 20th match': 336001, 'RCB vs DC 21st match': 336034, 'KXIP vs KKR 22nd match': 336003, 'MI vs DC 23rd match': 336004, 'CSK vs RR 24th match': 336005, 'RCB vs KXIP 25th match': 336006, 'CSK vs DC 26th match': 336007, 'RR vs MI 27th match': 336008, 'DC vs CSK 28th match': 336009, 'KKR vs RCB 29th match': 336010, 'DC vs RR 30th match': 336011, 'CSK vs KXIP 31st match': 336013, 'KKR vs DC 32nd match': 336014, 'DC vs RR 33rd match': 336015, 'RCB vs KXIP 34th match': 336016, 'KKR vs DC 35th match': 336017, 'CSK vs MI 36th match': 336018, 'DC vs DC 37th match': 336020, 'KKR vs MI 38th match': 336021, 'RR vs RCB 39th match': 336023, 'DC vs KXIP 40th match': 336022, 'KKR vs CSK 41st match': 336025, 'MI vs DC 42nd match': 336024, 'RCB vs DC 43rd match': 336026, 'KKR vs RR 44th match': 336027, 'KXIP vs MI 45th match': 336028, 'RCB vs CSK 46th match': 336029, 'DC vs KKR 47th match': 336030, 'DC vs KXIP 48th match': 336031, 'RR vs CSK 49th match': 336033, 'MI vs DC 50th match': 336032, 'DC vs RCB 51st match': 336002, 'KXIP vs KKR 52nd match': 336035, 'MI vs RR 53rd match': 336036, 'DC vs CSK 54th match': 336037, 'RCB vs MI 55th match': 336012, 'KXIP vs RR 56th match': 336019, 'RR vs DC 1st Semi-Final': 336038, 'KXIP vs CSK 2nd Semi-Final': 336039, 'CSK vs RR Final': 336040}
    else:
      return get_match_ids_from_series(series_id)
  
def get_all_toss_info():
  client, bucket = set_cloud_bucket_env()
  files_path = {}
  for series_id in all_series_ids:
    # Get the blob (file) from the bucket
    blob1 = bucket.blob(f"all_series_toss_info/{series_id}_toss_info.csv")

    # Read the file contents into memory
    file_content1 = blob1.download_as_text()

    # Create a StringIO object to treat the file content as a file-like object
    csv_io = io.StringIO(file_content1)

    files_path[series_id] = pd.read_csv(csv_io)
  return files_path

def get_team_name_score_ground(series_id, match_id):
  all_toss_infos = get_all_toss_info()
  particular_match_toss_info = all_toss_infos[series_id]
  particular_match_toss_info = pd.DataFrame(particular_match_toss_info)
  particular_match_toss_info = particular_match_toss_info[particular_match_toss_info['match_id'] == match_id]
  particular_match_toss_info.reset_index(drop=True, inplace=True)
  return particular_match_toss_info