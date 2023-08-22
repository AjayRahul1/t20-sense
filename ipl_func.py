import pandas as pd, requests, traceback, warnings, numpy as np, base64
from matplotlib.figure import Figure
from datetime import datetime
import asyncio, os, io

# Google Cloud Storage Imports
from google.cloud import storage

# Settings the warnings to be ignored
warnings.filterwarnings('ignore')

all_series_ids = [313494, 374163, 418064, 466304, 520932, 586733, 695871, 791129, 968923, 1078425, 1131611, 1165643, 1210595, 1249214, 1298423, 1345038]

series_id_taken = 418064
match_id_taken = 419165
innings_taken = 2

"""# Get matches data"""

def set_cloud_bucket_env():
  # Set the path to your service account key file
  os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('API_KEY') #'t20-sense-main.json'

  # Create a client using the credentials
  client = storage.Client()

  # Specify the bucket name and CSV file path
  bucket_name = os.getenv("BUCKET_NAME")

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
  main_bowling_df["Overs"] = main_bowling_df["Balls"].apply(lambda x:  f"{x//6}.{x%6}")

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

def get_match_info_response_API(series_id, match_id):
  url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId={series_id}&matchId={match_id}"
  response = requests.get(url)
  return response.json()

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

def get_graphical_stats_from_each_ball_data(series_id, match_id):
  # Ball By Ball for 1st innings
  req_response = get_request_response_API(series_id, match_id, 1)
  ball_by_ball_json = pd.json_normalize(data=req_response.json()['comments'])
  
  inn1_team_color = get_match_info_response_API(series_id, match_id)['content']['innings'][0]['team']['primaryColor']
  inn2_team_color = get_match_info_response_API(series_id, match_id)['content']['innings'][1]['team']['primaryColor']

  nparr_each_ball_score_inn1 = np.array(ball_by_ball_json['totalInningRuns'])
  nparr_over_no_where_team_score_at_inn1 = np.array(ball_by_ball_json['oversActual'])
  
  # Ball By Ball for 2nd innings
  req_response = get_request_response_API(series_id, match_id, 2)
  ball_by_ball_json = pd.json_normalize(data=req_response.json()['comments'])
  
  nparr_each_ball_score_inn2 = np.array(ball_by_ball_json['totalInningRuns'])
  nparr_over_no_where_team_score_at_inn2 = np.array(ball_by_ball_json['oversActual'])

  fig = Figure()
  ax = fig.add_subplot(1, 1, 1)
  ax.plot(nparr_over_no_where_team_score_at_inn1, nparr_each_ball_score_inn1, color=inn1_team_color)
  ax.plot(nparr_over_no_where_team_score_at_inn2, nparr_each_ball_score_inn2, color=inn2_team_color)
  ax.set_xlabel("Overs")
  ax.set_ylabel("Runs")

  img_stream = io.BytesIO()
  fig.savefig(img_stream, format="png")
  img_stream.seek(0)
  line_plot_cumulative_team_score_graph_base64 = base64.b64encode(img_stream.read()).decode("utf-8")

  return line_plot_cumulative_team_score_graph_base64

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

def get_best_shots(series_id, match_id):
  url = f"https://hs-consumer-api.espncricinfo.com/v1/pages/match/home?lang=en&seriesId={series_id}&matchId={match_id}"
  response = requests.get(url)
  bst_perf_bat = response.json()['content']['bestPerformance']['batsmen']
  perf_bat_inn1 = f"{bst_perf_bat[0]['teamAbbreviation']} - {bst_perf_bat[0]['player']['longName']} with {bst_perf_bat[0]['shot']} shot scoring {bst_perf_bat[0]['shotRuns']} out of {bst_perf_bat[0]['runs']} runs"
  perf_bat_inn2 = f"{bst_perf_bat[1]['teamAbbreviation']} - {bst_perf_bat[1]['player']['longName']} with {bst_perf_bat[1]['shot']} shot scoring {bst_perf_bat[1]['shotRuns']} out of {bst_perf_bat[1]['runs']} runs"
  return perf_bat_inn1, perf_bat_inn2