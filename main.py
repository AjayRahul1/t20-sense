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
matches_ids_list = []

years = list(range(2008, 2024))  # Generate a list of years from 2008 to 2023
match_ids = ["Select the Match"]  # Example match IDs

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # years = [313494, 374163, 418064, 466304, 520932, 586733, 695871, 791129, 968923, 1078425, 1131611, 1165643, 1210595, 1249214, 1298423, 1345038]
    return templates.TemplateResponse("index.html", {"request": request, "years": years, "match_ids": match_ids})

@app.get("/get_match_ids")
async def get_match_ids(year: int):
    global matches_dict, match_ids_list
    series_id = get_series_from_year(year)
    print(series_id)
    matches_dict = get_match_ids_from_series_fast(series_id)  # Your function to retrieve match_ids based on series_id
    match_ids_list = list(matches_dict.keys())
    return JSONResponse(content=match_ids_list)

@app.post("/process", response_class=HTMLResponse)
async def process(
        request: Request,
        year: int = Form(...),
        match_id: str = Form(...)
    ):
    print("Year: ", year)
    print("Match Name: ", match_id)
    series_id = get_series_from_year(year)
    print("Series ID: ", series_id)
    match_id = int(matches_dict[match_id])

    toss_row_df = get_team_name_score_ground(series_id=series_id, match_id=match_id)
    toss_row_ground = toss_row_df['ground'][0]


    batting1, bowling1, batting2, bowling2 = get_particular_match_whole_score(series_id, match_id)
    batting1 = batting1.to_dict(orient='records')
    bowling1 = bowling1.to_dict(orient='records')
    batting2 = batting2.to_dict(orient='records')
    bowling2 = bowling2.to_dict(orient='records')



    team1_name, team2_name, match_date, result, match_title = get_match_info(series_id, match_id)
    return templates.TemplateResponse("index.html", {   "request": request, "years" : years, "match_ids" : match_ids,
                                                        "batting1": batting1, "bowling1": bowling1,
                                                        "batting2": batting2, "bowling2": bowling2,
                                                        "team1_name": team1_name, "team2_name": team2_name,
                                                        "match_date": match_date, "result": result, "match_title":match_title,
                                                        "ground_info": toss_row_ground })