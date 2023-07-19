from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List
from fastapi.staticfiles import StaticFiles
from ipl_func import get_particular_match_whole_score, get_series_from_year, get_match_ids_from_series_fast, get_match_info, get_all_csv_files_from_cloud, get_team_name_score_ground
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

all_ipl_series_info = get_all_csv_files_from_cloud()
matches_dict = {}
matches_names_list = []

years = list(range(2008, 2024))  # Generate a list of years from 2008 to 2023
match_ids = ["Select the Match"]  # Example match IDs

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
  # years = [313494, 374163, 418064, 466304, 520932, 586733, 695871, 791129, 968923, 1078425, 1131611, 1165643, 1210595, 1249214, 1298423, 1345038]
  finals_and_champs_df = pd.read_csv('Finals.csv')
  finals_and_champs_df = finals_and_champs_df.to_dict(orient='records')
  return templates.TemplateResponse("index.html", {"request": request, "years": years, "match_ids": match_ids, "finals_and_champs_df":finals_and_champs_df})

def updating_match_details_for_refresh(year):
  global matches_dict, match_ids_list
  series_id = get_series_from_year(year)
  matches_dict = get_match_ids_from_series_fast(series_id)  # Your function to retrieve match_ids based on series_id
  matches_names_list = list(matches_dict.keys())
  return matches_names_list

@app.get("/return_matches_names")
async def ret_match_ids(year : int, request : Request):
  matches_names_list = updating_match_details_for_refresh(year)
  return templates.TemplateResponse('content_loading_htmx/ipl_match_options.html', {"request" : request, "matches_names_list" : matches_names_list})
      
@app.get("/get_scorecard", response_class=HTMLResponse)
async def process(
    request: Request,
    year: int,
    match_name: str
  ):
  try:
    matches_names_list = updating_match_details_for_refresh(year=year)
    print("Year: ", year)
    print("Match Name: ", match_name)
    series_id = get_series_from_year(year)
    print("Series ID: ", series_id)
    match_id = int(matches_dict[match_name])

    toss_row_df = get_team_name_score_ground(series_id=series_id, match_id=match_id)

    ground_info = toss_row_df['ground'][0]
    toss_info = toss_row_df['tossWinnerTeamId'][0] + " won the toss and " + toss_row_df['tossWinnerChoice'][0]
    team1_name = toss_row_df['team_bat_first'][0]
    team2_name = toss_row_df['team_bat_second'][0]
    team1_score = toss_row_df['team1_score'][0]
    team2_score = toss_row_df['team2_score'][0]

    batting1, bowling1, batting2, bowling2 = get_particular_match_whole_score(series_id, match_id)

    innings1_overs = str(bowling1['Balls'].sum()//6) + "." + str(bowling1['Balls'].sum()%6) + " ov"
    innings2_overs, team2_target =  toss_row_df['team2_score_info'][0].split(', T:')

    batting1 = batting1.to_dict(orient='records')
    bowling1 = bowling1.to_dict(orient='records')
    batting2 = batting2.to_dict(orient='records')
    bowling2 = bowling2.to_dict(orient='records')

    team1_name, team2_name, match_date, result, match_title = get_match_info(series_id, match_id)
    return templates.TemplateResponse("index.html", {   "year": year, "match_id": match_id,
                              "request": request, "years" : years, "match_ids" : match_ids,
                              "batting1": batting1, "bowling1": bowling1,
                              "batting2": batting2, "bowling2": bowling2,
                              "team1_name": team1_name, "team2_name": team2_name,
                              "match_date": match_date, "result": result, "match_title":match_title,
                              "ground_info": ground_info, "toss_info": toss_info,
                              "team1_name": team1_name, "team2_name":team2_name,
                              "team1_score":team1_score, "team2_score":team2_score,
                              "innings1_overs": innings1_overs, "innings2_overs": innings2_overs,
                              "target" : team2_target })
  except:
    return templates.TemplateResponse('error_pages/no_scorecard.html', {"request": request})