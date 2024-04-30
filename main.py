from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import traceback, dotenv, json

from ipl_func import get_particular_match_whole_score
from base_fns import get_series_data_from_bucket, get_latest_match_data
from stats import CricketData, bat_impact_pts, bowl_impact_pts, get_ptnship, DNB, graph_cricket_innings_progression

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load .env variables into the environment
dotenv.load_dotenv(".env")

# all_ipl_series_info = get_all_csv_files_from_cloud()

# Note!!
# page_indices key is important for every page since navbar uses it.
with open("page_indices.json", "r") as file:
  page_indices: dict = json.load(file)

all_ipl_series_ids = {1345038: 2023, 1298423: 2022, 1249214: 2021, 1210595: 2020, 1165643: 2019, 1131611: 2018, 1078425: 2017, 968923: 2016, 791129: 2015, 695871: 2014, 586733: 2013, 520932: 2012, 466304: 2011, 418064: 2010, 374163: 2009, 313494: 2008} # Generate a list of years from 2008 to 2023
mlc_years = {1357742 : 2023}

@app.get("/")
async def home(request: Request):
  global page_indices
  latest_data = get_latest_match_data()
  return templates.TemplateResponse("home.html", {"request": request, "latest_data": latest_data, "page_indices_json": page_indices})

@app.get("/series/{series_id}")
async def seriesPage(request: Request, series_id: int):
  ser_data = get_series_data_from_bucket(series_id=series_id)
  return templates.TemplateResponse("series.html", {"request": request, "series_id": series_id, "ser_data": ser_data, "page_indices_json": page_indices})

@app.get("/series/{series_id}/match/{match_id}/full-scorecard", response_class=HTMLResponse)
async def scoreacard(request: Request, series_id: int, match_id: int):
  try:
    print("Match ID: ", match_id, "\nSeries ID: ", series_id)

    cricket_data = CricketData(series_id, match_id)
    match_data: dict = cricket_data.match_data

    batting1, bowling1, batting2, bowling2 = get_particular_match_whole_score(series_id, match_id)
    
    bat_imp_pts, bow_imp_pts= {}, {}
    try:
      bat_imp_pts, ptnrshp_df = bat_impact_pts(series_id, match_id)  # Batting impact points
      bat_df, bow_imp_pts = bowl_impact_pts(series_id, match_id)  # Bowlers impact points
      bat_imp_pts = bat_imp_pts.to_dict(orient='records')
      bow_imp_pts = bow_imp_pts.to_dict(orient='records')
    except Exception:
      bat_imp_pts, bow_imp_pts= {}, {}

    line_plot_cumulative_team_score_graph_base64 = graph_cricket_innings_progression(series_id=series_id, match_id=match_id)
    i1_ptnr_df, i2_ptnr_df, ptnr_fig1, ptnr_fig2= {}, {}, "", ""
    try:
      i1_ptnr_df, i2_ptnr_df, ptnr_fig1, ptnr_fig2 = get_ptnship(series_id, match_id)
      i1_ptnr_df = i1_ptnr_df.to_dict(orient='records')
      i2_ptnr_df = i2_ptnr_df.to_dict(orient='records')
    except:
      i1_ptnr_df, i2_ptnr_df, ptnr_fig1, ptnr_fig2= {}, {}, "", ""

    i1_ovs_runs, i2_ovs_runs = cricket_data.runs_in_ovs_fig()
    i1_runs, i2_runs = cricket_data.division_of_runs()

    dnb1, dnb2 = DNB(series_id, match_id)

    context = {
      "request": request, "series_id": series_id, "match_id": match_id, "match_data_json": match_data,
      "batting1": batting1, "bowling1": bowling1, "batting2": batting2, "bowling2": bowling2,
      "imp_pts": bat_imp_pts, "bow_imp_pts": bow_imp_pts,
      "ptnr_df1": i1_ptnr_df, "ptnr_df2": i2_ptnr_df, "ptnr_f1" : ptnr_fig1, "ptnr_f2" : ptnr_fig2,
      "i1_runs": i1_runs, "i2_runs": i2_runs, "dnb1" : dnb1, "dnb2" : dnb2,
      "i1_ov_runs": i1_ovs_runs,  "i2_ov_runs": i2_ovs_runs,
      "each_team_cumulative_score_per_over": line_plot_cumulative_team_score_graph_base64,
      "page_indices_json": page_indices
    }

    return templates.TemplateResponse("scorecard.html", context=context)
  except:
    traceback.print_exc()
    return templates.TemplateResponse('error_pages/no_scorecard.html', {"request": request}, status_code=404)
