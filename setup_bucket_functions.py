import pandas as pd, requests, traceback, warnings

def get_request_response_API(series_id, match_id, innings_id):
  url = f'https://hs-consumer-api.espncricinfo.com/v1/pages/match/comments?lang=en&seriesId={series_id}&matchId={match_id}&inningNumber={innings_id}&commentType=ALL&sortDirection=DESC&fromInningOver=-1'
  response = requests.get(url)
  return response

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

comments=pd.DataFrame()
def get_comm(series_id,match_id,innings):
  comm_for_match=get_comments_for_match_innings(series_id, match_id, innings)
  comm_for_match=pd.DataFrame(comm_for_match)
  comments=pd.DataFrame(comm_for_match['comments'])
  return comments

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