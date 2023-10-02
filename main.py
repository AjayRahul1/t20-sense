from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd, traceback

# Load .env variables into the environment
from dotenv import load_dotenv
load_dotenv()

from ipl_func import get_particular_match_whole_score, get_match_info, get_team_name_score_ground, get_graphical_stats_from_each_ball_data
from functionality import get_match_ids_from_series_fast
from stats import get_man_of_the_match, get_best_shots, fun_best_bowl_peformance, batting_impact_points, bowlers_impact_points, get_ptnship, runs_in_ovs_fig,division_of_runs,DNB,team_squads

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# all_ipl_series_info = get_all_csv_files_from_cloud()
matches_names_and_ids_dict = {}

drdnSerIds = {}

gbl_series_id=0
gbl_match_id=0

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
  global drdnSerIds
  all_ipl_series_ids = {1345038: 2023, 1298423: 2022, 1249214: 2021, 1210595: 2020, 1165643: 2019, 1131611: 2018, 1078425: 2017, 968923: 2016, 791129: 2015, 695871: 2014, 586733: 2013, 520932: 2012, 466304: 2011, 418064: 2010, 374163: 2009, 313494: 2008} # Generate a list of years from 2008 to 2023
  # years = [313494, 374163, 418064, 466304, 520932, 586733, 695871, 791129, 968923, 1078425, 1131611, 1165643, 1210595, 1249214, 1298423, 1345038]
  drdnSerIds = all_ipl_series_ids
  finals_and_champs_df = pd.read_csv('Finals.csv')
  finals_and_champs_df = finals_and_champs_df.to_dict(orient='records')
  return templates.TemplateResponse("index.html", {"request": request, "years": all_ipl_series_ids, "finals_and_champs_df":finals_and_champs_df})

@app.get("/mlc", response_class=HTMLResponse)
def mlc_home(request: Request):
  global drdnSerIds
  mlc_years = {1357742 : 2023}
  drdnSerIds = mlc_years
  mlc_home_p = True
  return templates.TemplateResponse("index.html", {"request": request, "years": mlc_years, "mlc_home": mlc_home_p})

@app.post("/redirect_to_scorecard")
def submit_form(series_id: int = Form(...), match_id: int = Form(...)):
  global gbl_series_id, gbl_match_id
  gbl_series_id = series_id
  gbl_match_id = match_id
  redirect_url = f"/get_scorecard/{series_id}/{match_id}"
  return RedirectResponse(url=redirect_url, status_code=303)

# @app.get('/get_mom')
# async def get_mom():
#   man_of_the_match = get_man_of_the_match(series_id, match_id)
#   return f"{man_of_the_match}"

def updating_match_details_for_refresh(series_id):
  global matches_names_and_ids_dict
  # series_id = get_series_from_year(year)
  matches_names_and_ids_dict = get_match_ids_from_series_fast(series_id)  # Your function to retrieve match_ids based on series_id
  return matches_names_and_ids_dict

@app.get("/return_matches_names")
async def ret_match_ids(series_id : int, request : Request):
  global matches_names_and_ids_dict
  matches_names_and_ids_dict = updating_match_details_for_refresh(series_id)
  return templates.TemplateResponse('content_templates/ipl_match_options.html', {"request" : request, "matches_names_and_ids_dict" : matches_names_and_ids_dict})

# @app.get('/ld_imp_pts/{series_id}/{match_id}')
# async def get_impact_points(request : Request, series_id: int, match_id: int):
#   return templates.TemplateResponse('content_templates/imp_pts_tbl.html', {"request" : request, })

@app.get("/get_scorecard/{series_id}/{match_id}", response_class=HTMLResponse)
async def process(
    request: Request,
    series_id: int,
    match_id: int
  ):
  try:
    matches_names_and_ids_dict = updating_match_details_for_refresh(series_id)
    # print("Year: ", year)
    print("Match ID: ", match_id)
    # series_id = get_series_from_year(year)
    print("Series ID: ", series_id)
    # match_id = int(matches_names_and_ids_dict[match_name])

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
    
    man_of_the_match = get_man_of_the_match(series_id, match_id)
    bst_perf_bat_inn1, bst_perf_bat_inn2 = get_best_shots(series_id, match_id)
    bst_perf_bowl_inn1, bst_perf_bowl_inn2 = fun_best_bowl_peformance(series_id, match_id)

    imp_pts, ptnrshp_df = batting_impact_points(series_id, match_id)  # Batting impact points
    bat_df,bow_imp_pts = bowlers_impact_points(series_id,match_id)  #Bowlers impact points
    imp_pts = imp_pts.to_dict(orient='records')
    bow_imp_pts = bow_imp_pts.to_dict(orient='records')

    line_plot_cumulative_team_score_graph_base64 = get_graphical_stats_from_each_ball_data(series_id=series_id, match_id=match_id)
    
    i1_ptnr_df, i2_ptnr_df, ptnr_f1, ptnr_f2 = get_ptnship(series_id, match_id)
    i1_ptnr_df = i1_ptnr_df.to_dict(orient='records')
    i2_ptnr_df = i2_ptnr_df.to_dict(orient='records')
    i1_ovs_runs, i2_ovs_runs = runs_in_ovs_fig(series_id, match_id)

    i1_runs,i2_runs=division_of_runs(series_id,match_id)

    dnb1,dnb2 = DNB(series_id,match_id)

    squad1,squad2 = team_squads(series_id,match_id)
    
    return templates.TemplateResponse("index.html", {   "selected_year": series_id, "selected_match_id": match_id,
                              "request": request, "years" : drdnSerIds,
                              "batting1": batting1, "bowling1": bowling1,
                              "batting2": batting2, "bowling2": bowling2,
                              "team1_name": team1_name, "team2_name": team2_name,
                              "match_date": match_date, "result": result, "match_title":match_title,
                              "ground_info": ground_info, "toss_info": toss_info, "man_of_the_match":man_of_the_match,
                              "team1_name": team1_name, "team2_name":team2_name,
                              "team1_score":team1_score, "team2_score":team2_score,
                              "innings1_overs": innings1_overs, "innings2_overs": innings2_overs, "target" : team2_target,
                              "bst_perf_bat_inn1": bst_perf_bat_inn1, "bst_perf_bat_inn2": bst_perf_bat_inn2, 
                              "bst_perf_bowl_inn1": bst_perf_bowl_inn1, "bst_perf_bowl_inn2": bst_perf_bowl_inn2, 
                              "imp_pts": imp_pts, "bow_imp_pts": bow_imp_pts,
                              "ptnr_df1": i1_ptnr_df, "ptnr_df2": i2_ptnr_df,
                              "ptnr_f1" : ptnr_f1, "ptnr_f2" : ptnr_f2,
                              "i1_runs" : i1_runs, "i2_runs" : i2_runs,
                              "dnb1" : dnb1, "dnb2" : dnb2,
                              "squad1" : squad1, "squad2" : squad2,
                              "i1_ov_runs": i1_ovs_runs, "i2_ov_runs": i2_ovs_runs,
                              "each_team_cumulative_score_per_over" : line_plot_cumulative_team_score_graph_base64 })
  except Exception as e:
    traceback.print_exc()
    return templates.TemplateResponse('error_pages/no_scorecard.html', {"request": request})

