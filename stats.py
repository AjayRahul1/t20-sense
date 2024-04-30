import os, io, base64, pandas as pd, base_fns
from google.cloud import storage  # Google Cloud Storage Imports
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import plotly.express as px
import plotly.graph_objects as go
import plotly.offline as pyo

from base_fns import get_series_data_from_bucket, get_match_data_from_bucket, get_innings_data, get_match_players_dict, conv_to_base64, conv_to_html
try:
  # Set the path to your service account key file
  os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('API_KEY') # 't20-sense-main.json'
  # Create a client using the credentials
  storage_client = storage.Client()
except:
  print("API KEY not found")

class CricketData:
  def __init__(self, series_id: int, match_id: int):
    self.series_id: int = series_id
    self.match_id: int = match_id
    self.series_data: dict = base_fns.get_series_data_from_bucket(series_id)
    self.match_data: dict = base_fns.get_match_data_from_bucket(series_id, match_id)
    innings_count = self.match_data["match"]["liveInning"]
    self.all_innings_data: list[dict] = [
      base_fns.get_innings_data(series_id, match_id, innings_no) for innings_no in range(1, innings_count+1)
    ]
  
  def runs_in_ovs_fig(self):
    matchInningsContent = self.match_data['content']['innings']
    for k in range(0, len(matchInningsContent)):
      inningovers = matchInningsContent[k]['inningOvers']
      if k==0:
        try:
          # for i in range(0, len(inningovers)):
          #   ov_no_1.append(inningovers[i]['overNumber'])
          #   ov_runs_1.append(inningovers[i]['overRuns'])
          #   ov_wkts_1.append(inningovers[i]['overWickets'])
          ov_no_1, ov_runs_1, ov_wkts_1 = zip(*[(inningovers[i]['overNumber'], inningovers[i]['overRuns'], inningovers[i]['overWickets']) for i in range(0, len(inningovers))])
        except:
          ov_no_1, ov_runs_1, ov_wkts_1 = [0] * len(inningovers), [0] * len(inningovers), [0] * len(inningovers)
      elif k==1:
        try:
          # for i in range(0,len(inningovers)):
          #   ov_no_2.append(inningovers[i]['overNumber'])
          #   ov_runs_2.append(inningovers[i]['overRuns'])
          #   ov_wkts_2.append(inningovers[i]['overWickets'])
          ov_no_2, ov_runs_2, ov_wkts_2 = zip(*[(inningovers[i]['overNumber'], inningovers[i]['overRuns'], inningovers[i]['overWickets']) for i in range(0, len(inningovers))])
        except:
          ov_no_2, ov_runs_2, ov_wkts_2 = [0] * len(inningovers), [0] * len(inningovers), [0] * len(inningovers)
    
    fig1 = Figure(figsize=(8, 6))
    fig2 = Figure(figsize=(8, 6))

    ax = fig1.add_subplot(1, 1, 1)
    ax.set_ylabel('Runs')
    ax.set_xlabel('Overs')
    ax.set_title('Runs Per Over - Innings 1')
    ax.bar(ov_no_1, ov_runs_1)
    inn1_ovs_runs = base_fns.conv_to_base64(fig1)
    
    ax = fig2.add_subplot(1, 1, 1)
    ax.set_ylabel('Runs')
    ax.set_xlabel('Overs')
    ax.set_title('Runs Per Over - Innings 2')
    ax.bar(ov_no_2, ov_runs_2)
    inn2_ovs_runs = base_fns.conv_to_base64(fig2)
    
    return inn1_ovs_runs, inn2_ovs_runs
  
  def division_of_runs(self):
    inn1_runs = [0, 0, 0, 0, 0, 0]
    inn2_runs = [0, 0, 0, 0, 0, 0]

    for innings in [1, 2]:
      try:
        comments = self.all_innings_data[innings-1]['comments']
        for i in range(0, len(comments)):
          runs, wides, four, six = comments[i]['batsmanRuns'], comments[i]['wides'], comments[i]['isFour'], comments[i]['isSix']
          if runs == 1:
            inn_runs = inn1_runs if innings == 1 else inn2_runs
            inn_runs[1] += 1
          elif runs == 2:
            inn_runs = inn1_runs if innings == 1 else inn2_runs
            inn_runs[2] += 1
          elif runs == 3:
            inn_runs = inn1_runs if innings == 1 else inn2_runs
            inn_runs[3] += 1
          if runs == 0 and wides == 0:
            inn_runs = inn1_runs if innings == 1 else inn2_runs
            inn_runs[0] += 1
          if four:
            inn_runs = inn1_runs if innings == 1 else inn2_runs
            inn_runs[4] += 1
          if six:
            inn_runs = inn1_runs if innings == 1 else inn2_runs
            inn_runs[5] += 1
      except:
        print(f"Exception in Division of Runs for s{self.series_id}, m{self.match_id}, i{innings}")
        continue
    fig_labels=["dots", "1s", "2s", "3s", "4s", "6s"]
    fig1 = go.Figure(data=[go.Pie(labels=fig_labels, values=inn1_runs, textinfo='value')])
    fig2 = go.Figure(data=[go.Pie(labels=fig_labels, values=inn2_runs, textinfo='value')])
    i1_runs = base_fns.conv_to_html(fig1)
    i2_runs = base_fns.conv_to_html(fig2)
    return i1_runs, i2_runs

def bat_impact_pts(series_id: int, match_id: int):
  # players_dictionary = get_match_players_dict(content=content)
  player_dict={}
  # matches_ids = match_ids(series_id)
  # for match_id in matches_ids:
  output1=get_match_data_from_bucket(series_id, match_id)
  content = output1['content']
  for i in range(0,2):
    try:
      matches1 = output1['content']['matchPlayers']['teamPlayers'][i]['players']
      for j in range(0,len(matches1)):
        player_id=matches1[j]['player']['id']
        player_name=matches1[j]['player']['longName']
        player_dict[player_id] = player_name
    except:
      continue
  partnership_df = pd.DataFrame(columns=['innings', 'player1ID', 'player1', 'player2ID', 'player2','player_out_id', 'player1_runs', 'player1_balls','player2_runs', 'player2_balls', 'partnershipRuns', 'partnershipBalls'])
  f = 0
  for k in range(0, 2):
    if(k==0):
      team1_name=content['matchPlayers']['teamPlayers'][k]['team']['longName']
    else:
      team2_name=content['matchPlayers']['teamPlayers'][k]['team']['longName']
    partnerships = content['innings'][k]['inningPartnerships']
    for p in range(0, len(partnerships)):
        partnership_df.loc[f, 'innings'] = k + 1
        partnership_df.loc[f, 'player1ID'] = partnerships[p]['player1']['id']
        partnership_df.loc[f, 'player1'] = partnerships[p]['player1']['longName']
        partnership_df.loc[f, 'player2ID'] = partnerships[p]['player2']['id']
        partnership_df.loc[f, 'player2'] = partnerships[p]['player2']['longName']
        partnership_df.loc[f, 'player_out_id'] = partnerships[p]['outPlayerId']
        partnership_df.loc[f, 'player1_runs'] = partnerships[p]['player1Runs']
        partnership_df.loc[f, 'player1_balls'] = partnerships[p]['player1Balls']
        partnership_df.loc[f, 'player2_runs'] = partnerships[p]['player2Runs']
        partnership_df.loc[f, 'player2_balls'] = partnerships[p]['player2Balls']
        partnership_df.loc[f, 'partnershipRuns'] = partnerships[p]['runs']
        partnership_df.loc[f, 'partnershipBalls'] = partnerships[p]['balls']
        f += 1
  partnership_df['player_out'] = partnership_df['player_out_id'].map(player_dict).fillna("not out")
  for index, row in partnership_df.iterrows():
    partnership_df.at[index, 'p1_contrib'] = (row['player1_runs'] * 100 / row['partnershipRuns']) if row['partnershipRuns'] != 0 else 0
    partnership_df.at[index, 'p2_contrib'] = (row['player2_runs'] * 100 / row['partnershipRuns']) if row['partnershipRuns'] != 0 else 0
    partnership_df.at[index, 'player1_SR'] = (row['player1_runs'] * 100 / row['player1_balls']) if row['player1_balls'] != 0 else 0
    partnership_df.at[index, 'player2_SR'] = (row['player2_runs'] * 100 / row['player2_balls']) if row['player2_balls'] != 0 else 0

  df = pd.DataFrame(list(player_dict.items()), columns=['player id', 'player name'])
  df['runs']=0
  df['balls']=0
  df['impact_points']=0
  df['runs_imp']=0
  df['fours_imp']=0
  df['sixes_imp']=0
  df['team']=None
  team_1_total = 0
  team_2_total = 0
  team1_balls = 0
  team2_balls = 0
  wkts1=0
  wkts2=0

  for innings in range(1,3):
    try:
      matches=get_innings_data(series_id, match_id, innings)['comments']
      impact_points=0
      # Performance_score=0
      for i in range(0,len(matches)):
        over=matches[i]['overNumber']
        oversActual=matches[i]['oversActual']
        totalruns=matches[i]['totalRuns']
        bowler_id=matches[i]['bowlerPlayerId']
        batsman_id=matches[i]['batsmanPlayerId']
        batsman1_id=batsman_id
        batsman_runs=matches[i]['batsmanRuns']
        wides=matches[i]['wides']
        noballs=matches[i]['noballs']
        byes=matches[i]['byes']
        legbyes=matches[i]['legbyes']
        penalties=matches[i]['penalties']
        wicket=matches[i]['isWicket']

        if(batsman_runs==0 and wides==0):
          dot = 1
        else:
          dot = 0
        impact_points=0
        runs_imp=0
        four_imp=0
        sixes_imp=0
        if(wides>0):
          ball=0
        else:
          ball=1

        ##Runrate
        if(innings==1):
          team_1_total=team_1_total + totalruns
          team1_balls=team1_balls+ball
          CRR1=team_1_total*6/team1_balls
        else:
          target=team_1_total
          team_2_total=team_2_total + totalruns
          team2_balls=team2_balls+ball
          required_runs=target-team_2_total
          required_rr=required_runs*6/(120-team2_balls)
          CRR2=team_2_total*6/team2_balls

        ##Impact points
        if(batsman_runs==0):
          impact_points=0
          runs_imp=0
          four_imp=0
          sixes_imp=0
        elif(batsman_runs==1):
          impact_points=1
          runs_imp=1
        elif(batsman_runs==2):
          impact_points=2
          runs_imp=2
        elif(batsman_runs==3):
          impact_points=3
          runs_imp=3
        elif(batsman_runs==4):
          impact_points=4.5
          four_imp=4.5
        elif(batsman_runs==6):
          impact_points=7
          sixes_imp=7


        # k = i + 1
        batsman2_id = None
        check=0
        p=k
        while(check):
          b_id = matches[p]['batsmanPlayerId']
          if b_id != batsman_id:
            batsman2_id = b_id
            check=1
            break
          p += 1

        ##Wicket
        if(wicket==True):
          outplayer_id=matches[i]['outPlayerId']
          next_batsman_id=matches[i+1]['batsmanPlayerId']
          if(next_batsman_id == batsman2_id or batsman_id):
            check=0
            while(check):
              p = k
              b_id = matches[p]['batsmanPlayerId']
              if(b_id != batsman2_id or batsman_id):
                next_batsman_id = b_id
                check=1
                break
              p += 1
          if(innings==1):
            wkts1 += 1
            if(wkts1==1):
              df.loc[df['player id'] == outplayer_id, 'CRR_when_came'] = 0
              df.loc[df['player id'] == batsman2_id, 'CRR_when_came'] = 0
            else:
              df.loc[df['player id'] == outplayer_id, 'CRR_when_out']= CRR1
              df.loc[df['player id'] == outplayer_id, 'team_score']= team_1_total
              df.loc[df['player id'] == outplayer_id, 'team_balls']= team1_balls
              df.loc[df['player id'] == next_batsman_id, 'CRR_when_came']= CRR1
            CRR1_arrived=CRR1

          if(innings==2):
            wkts2 += 1
            next_batsman_id=matches[i+1]['batsmanPlayerId']
            if(next_batsman_id == batsman2_id or batsman_id):
              check=0
              while(check):
                p = k
                b_id = matches[p]['batsmanPlayerId']
                if(b_id != batsman2_id or batsman_id):
                  next_batsman_id = b_id
                  check=1
                  break
                p += 1
            df.loc[df['player id'] == outplayer_id, 'team_score']= team_2_total
            df.loc[df['player id'] == outplayer_id, 'team_balls']= team2_balls
            if(wkts2!=1):
              df.loc[df['player id'] == outplayer_id, 'RRR_when_came']=req_rr
            if(wkts2==1):
              df.loc[df['player id'] == outplayer_id, 'RRR_when_came']=CRR1
              df.loc[df['player id'] == batsman2_id, 'RRR_when_came']=CRR1
              df.loc[df['player id'] == outplayer_id, 'CRR_when_came']=0
              df.loc[df['player id'] == batsman2_id, 'CRR_when_came']=0
            df.loc[df['player id'] == outplayer_id, 'CRR_when_out']= CRR2
            df.loc[df['player id'] == next_batsman_id, 'CRR_when_came']= CRR2
            df.loc[df['player id'] == outplayer_id, 'RRR_when_out']= required_rr
            req_rr=required_rr

        if(innings==2):
          if(oversActual==0.1):
            df.loc[df['player id'] == batsman_id, 'RRR_when_came']=CRR1
            # df.loc[df['player id'] == batsman2_id, 'RRR_when_came']=CRR1


        df.loc[df['player id']==batsman_id,'innings']=innings
        if(innings==1):
          df.loc[df['player id']==batsman_id,'team']=team1_name
        else:
          df.loc[df['player id']==batsman_id,'team']=team2_name
        df.loc[df['player id'] == batsman_id, 'runs'] = df.loc[df['player id'] == batsman_id,'runs'] + batsman_runs
        df.loc[df['player id'] == batsman_id, 'balls'] = df.loc[df['player id'] == batsman_id,'balls'] + ball
        r=0
        dp=0
        if(over<7):
          r=0.5
        elif(over>16 and over<19):
          r=1
          if(dot==1):
            dp=-0.5
        elif(over>18):
          r=2
          if(dot==1):
            dp=-1
        else:
          r=0
        df.loc[df['player id'] == batsman_id, 'runs_imp']+= runs_imp
        # if(totalruns!=0):
        #   df.loc[df['player id'] == batsman_id, 'impact_points']+= impact_points + r
        # elif (batsman_runs==0 and wides==0):
        #   df.loc[df['player id'] == batsman_id, 'impact_points']+= impact_points + dp
        if(four_imp!=0):
          df.loc[df['player id'] == batsman_id, 'fours_imp']+= four_imp + r
        else:
          df.loc[df['player id'] == batsman_id, 'fours_imp']+= four_imp
        if(sixes_imp!=0):
          df.loc[df['player id'] == batsman_id, 'sixes_imp']+= sixes_imp + r
        else:
          df.loc[df['player id'] == batsman_id, 'sixes_imp']+= sixes_imp
      df['impact_points']=df['runs_imp'] + df['fours_imp'] + df['sixes_imp']
      df['SR'] = (df['runs']*100/df['balls']).round(2)

      for i in range(len(df)):
        p=0
        p=df['runs'][i]/10
        df['impact_points'][i]+=p*2
      target=df.loc[df['innings'] == 1, 'runs'].sum()
      target_sr=target/1.2
    except:
      continue

  # for j in range(0,len(partnership_df)):

  for j in range(len(df)):
    if(df['innings'][j]==1):
      first_total=df['runs'].sum()
      first_balls=df['balls'].sum()
      first_SR=first_total*6/first_balls
      if(df['SR'][j]<(first_SR)/2):
        df['impact_points'][j]-=5
      elif(df['SR'][j]<first_SR):
        df['impact_points'][j]-=2
      elif(df['SR'][j]>=1.5*(first_SR)):
        df['impact_points'][j]+=2
      elif(df['SR'][j]>2*(first_SR)):
        df['impact_points'][j]+=5
    else:
      if(df['SR'][j]<(target_sr)/2):
        df['impact_points'][j]-=5
      elif(df['SR'][j]<target_sr):
        df['impact_points'][j]-=2
      elif(df['SR'][j]>=1.5*(target_sr)):
        df['impact_points'][j]+=2
      elif(df['SR'][j]>2*(target_sr)):
        df['impact_points'][j]+=5
    df1 = df[df['impact_points'] != 0]
    df1['CRR_when_out']=df1['CRR_when_out'].fillna(" - ")
    df1['RRR_when_came']=df1['RRR_when_came'].fillna(" - ")
    df1['CRR_when_out']=(df1['CRR_when_out']).apply(lambda x: format(x, ".2f") if isinstance(x, (int, float)) else x)
    # df1['RRR_when_came']=(df1['RRR_when_came']).apply(lambda x: format(x, ".2f") if isinstance(x, (int, float)) else x)
    # df1['RRR_when_out']=(df1['RRR_when_out']).apply(lambda x: format(x, ".2f") if isinstance(x, (int, float)) else x)
    # b_df1 = b_df[b_df['Performance_score'] != 0]
    df1=df1.sort_values(by='impact_points', ascending=False)
    df1['SR'] = df1['SR'].round(2)
  return df1, partnership_df

def bowl_impact_pts(series_id: int,match_id: int):
  player_dict={}
  output1 = get_match_data_from_bucket(series_id, match_id)
  for i in range(0,2):
    matches1 = output1['content']['matchPlayers']['teamPlayers'][i]
    if(i==0):
      team1_name=matches1['team']['longName']
    else:
      team2_name=matches1['team']['longName']
    players=matches1['players']
    for j in range(0,len(players)):
      player_id=players[j]['player']['id']
      player_name=players[j]['player']['longName']
      player_dict[player_id] = player_name
  df = pd.DataFrame(list(player_dict.items()), columns=['player id', 'player name'])
  b_df = pd.DataFrame(list(player_dict.items()), columns=['player id', 'player name'])
  b_df['team']=None
  b_df['innings']=0
  b_df['impact_points']=0
  b_df['balls']=0
  b_df['wickets']=0
  df['runs']=0
  df['balls']=0
  
  # bat_runs=0
  for innings in range(1,3):
    try:
      matches = get_innings_data(series_id, match_id, innings)['comments']
      for i in range(0,len(matches)):
        try:
          over=matches[i]['overNumber']
          oversActual=matches[i]['oversActual']
          totalruns=matches[i]['totalRuns']
          bowler_id=matches[i]['bowlerPlayerId']
          batsman_id=matches[i]['batsmanPlayerId']
          batsman_runs=matches[i]['batsmanRuns']
          wides=matches[i]['wides']
          noballs=matches[i]['noballs']
          byes=matches[i]['byes']
          legbyes=matches[i]['legbyes']
          penalties=matches[i]['penalties']
          wicket=matches[i]['isWicket']
          impact_points=0
          if(wides>0):
            ball=0
          else:
            ball=1
          if(batsman_runs==0 and wides==0):
            dot=1
          else:
            dot=0
          df.loc[df['player id'] == batsman_id, 'runs'] = df.loc[df['player id'] == batsman_id,'runs'] + batsman_runs
          df.loc[df['player id'] == batsman_id, 'balls'] = df.loc[df['player id'] == batsman_id,'balls'] + ball

          b_df.loc[b_df['player id'] == bowler_id, 'innings'] = innings
          b_df.loc[b_df['player id'] == bowler_id, 'balls'] = b_df.loc[b_df['player id'] == bowler_id,'balls'] + ball

          if(batsman_runs==0):
            impact_points+=2
          if(batsman_runs==4):
            impact_points+=-2
          if(batsman_runs==6):
            impact_points+=-3
          if(wides>0):
            impact_points=-(wides)
          if(noballs==1):
            impact_points +=-2

          if(wicket == True):
            dismissal_type=matches[i]['dismissalType']
            outplayer_id=matches[i]['outPlayerId']
            if(dismissal_type!=4):
              impact_points+=15
              b_df.loc[b_df['player id'] == bowler_id, 'wickets'] += 1
              dismissed_bat_runs = df.loc[df['player id'] == outplayer_id, 'runs'].sum()
              impact_points += 15

              if dismissed_bat_runs >= 30:
                  impact_points += 5
              elif dismissed_bat_runs > 50:
                  impact_points += 8
              elif dismissed_bat_runs > 100:
                  impact_points += 15
            if(over<7):
              b_df.loc[b_df['player id'] == bowler_id , 'impact_points'] += 2
            if(over>16):
              b_df.loc[b_df['player id'] == bowler_id , 'impact_points'] += 5
          b_df.loc[b_df['player id'] == bowler_id, 'impact_points'] += impact_points   
        except:
          print(id)
          continue
    except:
      print(innings)
      continue
  for b in range(0, len(b_df)):
    if b_df.loc[b, 'innings'] == 1:
        b_df.loc[b, 'team'] = team2_name
    else:
        b_df.loc[b, 'team'] = team1_name
  df['SR']=df['runs']*100/df['balls']
  df = df[df['balls'] != 0]
  b_df = b_df[b_df['balls'] != 0]
  b_df['innings']=b_df['innings'].astype(int)
  b_df=b_df.sort_values(by='impact_points', ascending=False)
  return df,b_df

def get_ptnship(series_id, match_id):
  content = get_match_data_from_bucket(series_id, match_id)['content']
  # Generating a dictionary of players who played in that match to map it later
  # for who ever was out and was in the partnership using Dictionary Comprehension
  players_dictionary = get_match_players_dict(content=content)
  partnership_df = pd.DataFrame(columns=['innings', 'player1ID', 'player1', 'player2ID', 'player2','player_out_id', 'player1_runs', 'player1_balls','player2_runs', 'player2_balls', 'partnershipRuns', 'partnershipBalls'])
  f = 0
  for k in range(0, 2):
    partnerships = content['innings'][k]['inningPartnerships']
    for p in range(0, len(partnerships)):
        partnership_df.loc[f, 'innings'] = k + 1
        partnership_df.loc[f, 'player1ID'] = partnerships[p]['player1']['id']
        partnership_df.loc[f, 'player1'] = partnerships[p]['player1']['longName']
        partnership_df.loc[f, 'player2ID'] = partnerships[p]['player2']['id']
        partnership_df.loc[f, 'player2'] = partnerships[p]['player2']['longName']
        partnership_df.loc[f, 'player_out_id'] = partnerships[p]['outPlayerId']
        partnership_df.loc[f, 'player1_runs'] = partnerships[p]['player1Runs']
        partnership_df.loc[f, 'player1_balls'] = partnerships[p]['player1Balls']
        partnership_df.loc[f, 'player2_runs'] = partnerships[p]['player2Runs']
        partnership_df.loc[f, 'player2_balls'] = partnerships[p]['player2Balls']
        partnership_df.loc[f, 'partnershipRuns'] = partnerships[p]['runs']
        partnership_df.loc[f, 'partnershipBalls'] = partnerships[p]['balls']
        f += 1
  partnership_df['player_out'] = partnership_df['player_out_id'].map(players_dictionary).fillna("not out")
  for index, row in partnership_df.iterrows():
    partnership_df.at[index, 'p1_contrib'] = (row['player1_runs'] * 100 / row['partnershipRuns']) if row['partnershipRuns'] != 0 else 0
    partnership_df.at[index, 'p2_contrib'] = (row['player2_runs'] * 100 / row['partnershipRuns']) if row['partnershipRuns'] != 0 else 0
    partnership_df.at[index, 'player1_SR'] = (row['player1_runs'] * 100 / row['player1_balls']) if row['player1_balls'] != 0 else 0
    partnership_df.at[index, 'player2_SR'] = (row['player2_runs'] * 100 / row['player2_balls']) if row['player2_balls'] != 0 else 0

  dff = pd.DataFrame(columns=['Innings','Wicket', 'Player 1', 'Player 2', 'Partnership'])
  for index, row in partnership_df.iterrows():
    inn = row["innings"]
    wicket = index+1
    player1 = f'{row["player1"]} {row["player1_runs"]}({row["player1_balls"]})'
    player2 = f'{row["player2"]} {row["player2_runs"]}({row["player2_balls"]})'
    partnership = f'{row["partnershipRuns"]}({row["partnershipBalls"]})'

    # Add the formatted data to dff DataFrame
    dff.loc[index] = [inn,wicket, player1, player2, partnership]

  dff1 = dff[dff['Innings'] == 1].reset_index(drop=True)
  dff2 = dff[dff['Innings'] == 2].reset_index(drop=True)
  dff1 = dff1[::-1]
  dff2 = dff2[::-1]

  innings_1_partnership = partnership_df[partnership_df['innings'] == 1].reset_index(drop=True)
  innings_2_partnership = partnership_df[partnership_df['innings'] == 2].reset_index(drop=True)
  # Create the plots for both innings


  fig_1, ax_1 = plt.subplots(figsize=(7, 6))
  fig_2, ax_2 = plt.subplots(figsize=(7, 6))
  max_runs = max(innings_1_partnership['player1_runs'].max(), innings_1_partnership['player2_runs'].max())

  ax_1.set_ylabel('Partnerships')
  ax_1.set_xlabel('Runs')
  ax_1.set_title('Partnerships Runs - Innings 1')
  ax_1.set_yticks(range(len(innings_1_partnership)))
  ax_1.set_yticklabels(innings_1_partnership['player2'] + ' & ' + innings_1_partnership['player1'])
  # ax_1.legend()

  ax_1.barh(range(len(innings_1_partnership)), innings_1_partnership['player1_runs'], color='tab:blue', label='Player 1 Runs')
  ax_1.barh(range(len(innings_1_partnership)), -innings_1_partnership['player2_runs'], color='tab:orange', label='Player 2 Runs')
  ax_1.set_xlim(-max_runs, max_runs)

  xticks = [-max_runs, -max_runs//2, 0, max_runs//2, max_runs]
  ax_1.set_xticks(xticks)
  ax_1.set_xticklabels([abs(x) for x in xticks])

  ax_2.set_ylabel('Partnerships')
  ax_2.set_xlabel('Runs')
  ax_2.set_title('Partnerships Runs - Innings 2')
  ax_2.set_yticks(range(len(innings_2_partnership)))
  ax_2.set_yticklabels(innings_2_partnership['player2'] + ' & ' + innings_2_partnership['player1'])
  # ax_2.legend()

  ax_2.barh(range(len(innings_2_partnership)), innings_2_partnership['player1_runs'], color='tab:blue', label='Player 1 Runs')
  ax_2.barh(range(len(innings_2_partnership)), -innings_2_partnership['player2_runs'], color='tab:orange', label='Player 2 Runs')
  ax_2.set_xlim(-max_runs, max_runs)

  ax_2.set_xticks(xticks)
  ax_2.set_xticklabels([abs(x) for x in xticks])

  # plt.tight_layout()
  i1_partnership = pd.DataFrame(columns=['Wicket', 'Player_1', 'Player_2', 'Partnership', 'player_out'])
  i2_partnership = pd.DataFrame(columns=['Wicket', 'Player_1', 'Player_2', 'Partnership', 'player_out'])

  for index, row in innings_1_partnership.iterrows():
    wicket = index+1
    player1 = f'{row["player1"]} {row["player1_runs"]}({row["player1_balls"]})'
    player2 = f'{row["player2"]} {row["player2_runs"]}({row["player2_balls"]})'
    partnership = f'{row["partnershipRuns"]}({row["partnershipBalls"]})'
    player_out = row["player_out"]
    # Add the formatted data to dff DataFrame
    i1_partnership.loc[index] = [wicket, player1, player2, partnership, player_out]

  for index, row in innings_2_partnership.iterrows():
    wicket = index+1
    player1 = f'{row["player1"]} {row["player1_runs"]}({row["player1_balls"]})'
    player2 = f'{row["player2"]} {row["player2_runs"]}({row["player2_balls"]})'
    partnership = f'{row["partnershipRuns"]}({row["partnershipBalls"]})'
    player_out = row["player_out"]
    # Add the formatted data to dff DataFrame
    i2_partnership.loc[index] = [wicket, player1, player2, partnership, player_out]

  buf1 = io.BytesIO()
  fig_1.savefig(buf1, format='png')
  buf1.seek(0)
  figdata1 = base64.b64encode(buf1.getvalue()).decode('utf-8')

  buf2 = io.BytesIO()
  fig_2.savefig(buf2, format='png')
  buf2.seek(0)
  figdata2 = base64.b64encode(buf2.getvalue()).decode('utf-8')

  # Return the DataFrames and the figures
  return i1_partnership,i2_partnership, figdata1, figdata2

def graph_cricket_innings_progression(series_id, match_id):
  # Ball By Ball for 1st innings
  import numpy as np
  try:
    req_response = get_innings_data(series_id, match_id, 1)
    ball_by_ball_json = pd.json_normalize(data=req_response['comments'])
    inn1_team_color = get_match_data_from_bucket(series_id, match_id)['content']['innings'][0]['team']['primaryColor']
    nparr_each_ball_score_inn1 = np.array(ball_by_ball_json['totalInningRuns'])
    nparr_over_no_where_team_score_at_inn1 = np.array(ball_by_ball_json['oversActual'])
  except:
    inn1_team_color = "#00FFFFFF"
    nparr_each_ball_score_inn1 = np.array([])
    nparr_over_no_where_team_score_at_inn1 = np.array([])
  
  # Ball By Ball for 2nd innings
  try:
    req_response = get_innings_data(series_id, match_id, 2)
    ball_by_ball_json = pd.json_normalize(data=req_response['comments'])
    inn2_team_color = get_match_data_from_bucket(series_id, match_id)['content']['innings'][1]['team']['primaryColor']
    nparr_each_ball_score_inn2 = np.array(ball_by_ball_json['totalInningRuns'])
    nparr_over_no_where_team_score_at_inn2 = np.array(ball_by_ball_json['oversActual'])
  except:
    inn2_team_color = "#00FFFFFF"
    nparr_each_ball_score_inn2 = np.array([])
    nparr_over_no_where_team_score_at_inn2 = np.array([])

  fig = Figure()
  ax = fig.add_subplot(1, 1, 1)
  ax.plot(nparr_over_no_where_team_score_at_inn1, nparr_each_ball_score_inn1, color=inn1_team_color)
  ax.plot(nparr_over_no_where_team_score_at_inn2, nparr_each_ball_score_inn2, color=inn2_team_color)
  ax.set_xlabel("Overs")
  ax.set_ylabel("Runs")

  """ Line Graph Description:
  This is a line graph in one figure for runs of both teams at each over in the game.
  This graph consists of 2 line graphs by calculating score in that over and plotting points.
  Then those lines are joined with line plot. """

  line_graph = conv_to_base64(fig)
  return line_graph

def runs_in_ovs_fig(series_id, match_id):
  content = get_match_data_from_bucket(series_id, match_id)['content']['innings']
  ov_no_1 = []
  ov_runs_1 = []
  ov_wkts_1 = []
  ov_no_2 = []
  ov_runs_2 = []
  ov_wkts_2 = []
  for k in range(0,len(content)):
    inningovers=content[k]['inningOvers']
    if k==0:
      try:
        for i in range(0,len(inningovers)):
          ov_no_1.append(inningovers[i]['overNumber'])
          ov_runs_1.append(inningovers[i]['overRuns'])
          ov_wkts_1.append(inningovers[i]['overWickets'])
      except:
        ov_no_1 = [0] * len(inningovers)
        ov_runs_1 =  [0] * len(inningovers)
        ov_wkts_1 = [0] * len(inningovers)
    if k==1:
      try:
        for i in range(0,len(inningovers)):
          ov_no_2.append(inningovers[i]['overNumber'])
          ov_runs_2.append(inningovers[i]['overRuns'])
          ov_wkts_2.append(inningovers[i]['overWickets'])
      except:
        ov_no_2 = [0] * len(inningovers)
        ov_runs_2 =  [0] * len(inningovers)
        ov_wkts_2 = [0] * len(inningovers)
  
  fig1 = Figure(figsize=(8, 6))
  fig2 = Figure(figsize=(8, 6))
  

  ax = fig1.add_subplot(1, 1, 1)
  ax.set_ylabel('Runs')
  ax.set_xlabel('Overs')
  ax.set_title('Runs Per Over - Innings 1')
  ax.bar(ov_no_1, ov_runs_1)
  inn1_ovs_runs = conv_to_base64(fig1)
  
  ax = fig2.add_subplot(1, 1, 1)
  ax.set_ylabel('Runs')
  ax.set_xlabel('Overs')
  ax.set_title('Runs Per Over - Innings 2')
  ax.bar(ov_no_2, ov_runs_2)
  inn2_ovs_runs = conv_to_base64(fig2)
  
  return inn1_ovs_runs, inn2_ovs_runs

def division_of_runs(series_id, match_id):
  inn1_runs = [0, 0, 0, 0, 0, 0]
  inn2_runs = [0, 0, 0, 0, 0, 0]

  for innings in [1, 2]:
    try:
      comments = get_innings_data(series_id, match_id, innings)['comments']
      for i in range(0, len(comments)):
        runs = comments[i]['batsmanRuns']
        wides = comments[i]['wides']
        four = comments[i]['isFour']
        six = comments[i]['isSix']

        if runs == 1:
          inn_runs = inn1_runs if innings == 1 else inn2_runs
          inn_runs[1] += 1
        elif runs == 2:
          inn_runs = inn1_runs if innings == 1 else inn2_runs
          inn_runs[2] += 1
        elif runs == 3:
          inn_runs = inn1_runs if innings == 1 else inn2_runs
          inn_runs[3] += 1
        if runs == 0 and wides == 0:
          inn_runs = inn1_runs if innings == 1 else inn2_runs
          inn_runs[0] += 1
        if four:
          inn_runs = inn1_runs if innings == 1 else inn2_runs
          inn_runs[4] += 1
        if six:
          inn_runs = inn1_runs if innings == 1 else inn2_runs
          inn_runs[5] += 1
    except:
      print("Exception in Division of Runs for s", series_id," m", match_id," i", innings)
      continue
  fig_labels=["dots", "1s", "2s", "3s", "4s", "6s"]
  fig1 = go.Figure(data=[go.Pie(labels=fig_labels, values=inn1_runs, textinfo='value')])
  fig2 = go.Figure(data=[go.Pie(labels=fig_labels, values=inn2_runs, textinfo='value')])
  i1_runs = conv_to_html(fig1)
  i2_runs = conv_to_html(fig2)
  return i1_runs, i2_runs

def DNB(series_id: int, match_id: int) -> tuple[list]:
  """
  Players who did not bat.

  Returns
  ---
    tuple[list]: (DNB1, DNB2)
      tuple of list of players who did not bat in 1st innings & 2nd innings.
  """
  innings = get_match_data_from_bucket(series_id, match_id)['content']['innings']
  DNB1=[]
  DNB2=[]
  for k in range(0, len(innings)):
    if(k==0):
      inningBatsmen=innings[k]['inningBatsmen']
      for i in range(0,len(inningBatsmen)):
        batsman_id=inningBatsmen[i]['player']['id']
        batsman_name=inningBatsmen[i]['player']['longName']
        battedtype=inningBatsmen[i]['battedType']
        if(battedtype=="DNB"):
          DNB1.append(batsman_name)
        else:
          continue
    if(k==1):
      inningBatsmen=innings[k]['inningBatsmen']
      for i in range(0,len(inningBatsmen)):
        batsman_id=inningBatsmen[i]['player']['id']
        batsman_name=inningBatsmen[i]['player']['longName']
        battedtype=inningBatsmen[i]['battedType']
        if(battedtype=="DNB"):
          DNB2.append(batsman_name)
        else:
          continue
  return DNB1, DNB2

def data_query(series_id: int, match_id: int):
  # Your BigQuery SQL query
  q1 = f"""
      SELECT batsman, SUM(batsmanruns) AS run
  FROM `seriesipl.data`
  WHERE series_id = {series_id}
  GROUP BY batsman
  ORDER BY run DESC  -- Order the results by total score in descending order
  LIMIT 50;          -- Limit the results to the top 50 batsmen by score

      """
  q2 = f"""
  SELECT bowler, SUM(CASE WHEN iswicket = TRUE THEN 1 ELSE 0 END) AS total_wickets
  FROM `seriesipl.data`
  WHERE series_id = {match_id}
  GROUP BY bowler
  ORDER BY total_wickets DESC  -- Order the results by total wickets in descending order
  LIMIT 50;                     -- Limit the results to the top 50 bowlers by wickets
  """

  # Run the query
  bat = storage_client.query(q1).to_dataframe().to_dict(orient='records')# batsman data from the series
  bowl = storage_client.query(q2).to_dataframe().to_dict(orient='records')# bolwer data from the series
  return bat, bowl
