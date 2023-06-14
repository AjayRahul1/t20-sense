from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List
from ipl_func import get_particular_match_whole_score
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    years = [313494, 374163, 418064, 466304, 520932, 586733, 695871, 791129, 968923, 1078425, 1131611, 1165643, 1210595, 1249214, 1298423, 1345038]
    match_ids = [419165]  # Example match IDs
    return templates.TemplateResponse("index.html", {"request": request, "years": years, "match_ids": match_ids})

@app.post("/process", response_class=HTMLResponse)
def process( request: Request, series_id: int = Form(...), match_id: int = Form(...)):
    # Call the data processing function with the selected year and match ID
    batting1, bowling1, batting2, bowling2 = get_particular_match_whole_score(series_id, match_id)
    batting1 = batting1.to_dict(orient='records')
    bowling1 = bowling1.to_dict(orient='records')
    batting2 = batting2.to_dict(orient='records')
    bowling2 = bowling2.to_dict(orient='records')
    # batting1 = pd.read_csv('ser418064_mat419165_inn1_batting.csv').to_dict(orient='records')
    # bowling1 = pd.read_csv('ser418064_mat419165_inn1_bowling.csv').to_dict(orient='records')
    # batting2 = pd.read_csv('ser418064_mat419165_inn2_batting.csv').to_dict(orient='records')
    # bowling2 = pd.read_csv('ser418064_mat419165_inn2_bowling.csv').to_dict(orient='records')
    return templates.TemplateResponse("results.html", {"request": request, "batting1": batting1, "bowling1": bowling1, "batting2": batting2, "bowling2": bowling2})