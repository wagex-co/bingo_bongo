from datetime import datetime
import requests
import re
import json

sport_dict = {"NBA": "nba-basketball",
              "NFL": "nfl-football",
              "NHL": "nhl-hockey",
              "MLB": "mlb-baseball",
              "NCAAB": "ncaa-basketball",
              "EPL": "english-premier-league",
              "UCL": "champions-league"}

class Scoreboard:
    def __init__(self, sport='NBA', date="", current_line=True):
        try:
            self.scrape_games(sport, date, current_line)
        except Exception as e:
            print("An error occurred: {}".format(e))
            self.games = []

    def scrape_games(self, sport="NBA", date="", current_line=True):
        if date == "":
            date = datetime.today().strftime("%Y-%m-%d")
        _line = 'currentLine' if current_line else 'openingLine'

        spreads = moneylines = totals = {}

        spread_url = f"https://www.sportsbookreview.com/betting-odds/{sport_dict[sport]}/?date={date}"
        r = requests.get(spread_url)
        j = re.findall('__NEXT_DATA__" type="application/json">(.*?)</script>',r.text)
        try:
            build_id = json.loads(j[0])['buildId']
            spreads_url = f"https://www.sportsbookreview.com/_next/data/{build_id}/betting-odds/{sport_dict[sport]}.json?league={sport_dict[sport]}&date={date}"
            spreads_json = requests.get(spreads_url).json()
            spreads_list = spreads_json['pageProps']['oddsTables'][0]['oddsTableModel']['gameRows']
            spreads = {g['gameView']['gameId']: g for g in spreads_list}
        except IndexError:
            return []

        moneyline_url = f"https://www.sportsbookreview.com/_next/data/{build_id}/betting-odds/{sport_dict[sport]}/money-line/full-game.json?league={sport_dict[sport]}&oddsType=money-line&oddsScope=full-game&date={date}"
        moneyline_json = requests.get(moneyline_url).json()
        moneylines_list = moneyline_json['pageProps']['oddsTables'][0]['oddsTableModel']['gameRows']
        moneylines = {g['gameView']['gameId']: g for g in moneylines_list}
        totals_url = f"https://www.sportsbookreview.com/_next/data/{build_id}/betting-odds/{sport_dict[sport]}/totals/full-game.json?league={sport_dict[sport]}&oddsType=totals&oddsScope=full-game&date={date}"
        totals_json = requests.get(totals_url).json()
        totals_list = totals_json['pageProps']['oddsTables'][0]['oddsTableModel']['gameRows']
        totals = {g['gameView']['gameId']: g for g in totals_list}

        all_stats = {
            game_id: {'spreads': spreads[game_id], 'moneylines': moneylines[game_id], 'totals': totals[game_id], } for game_id in spreads.keys()
        }

        games = []
        for event in all_stats.values():
            game = {}
            game['date'] = event['spreads']['gameView']['startDate']
            game['status'] = event['spreads']['gameView']['gameStatusText']
            game['home_team'] = event['spreads']['gameView']['homeTeam']['fullName']
            game['home_team_loc'] = event['spreads']['gameView']['homeTeam']['displayName']
            game['home_team_abbr'] = event['spreads']['gameView']['homeTeam']['shortName']
            game['home_team_rank'] = event['spreads']['gameView']['homeTeam']['rank']
            game['away_team'] = event['spreads']['gameView']['awayTeam']['fullName']
            game['away_team_loc'] = event['spreads']['gameView']['awayTeam']['displayName']
            game['away_team_abbr'] = event['spreads']['gameView']['awayTeam']['shortName']
            game['away_team_rank'] = event['spreads']['gameView']['awayTeam']['rank']
            game['home_score'] = event['spreads']['gameView']['homeTeamScore']
            game['away_score'] = event['spreads']['gameView']['awayTeamScore']
            game['home_spread'] = {}
            game['home_spread_odds'] = {}
            game['away_spread'] = {}
            game['away_spread_odds'] = {}
            game['under_odds'] = {}
            game['over_odds'] = {}
            game['total'] = {}
            game['home_ml'] = {}
            game['away_ml'] = {}
            if 'spreads' in event:
                for line in event['spreads']['oddsViews']:
                    if not line:
                        continue
                    game['home_spread'][line['sportsbook']] = line[_line]['homeSpread']
                    game['home_spread_odds'][line['sportsbook']] = line[_line]['homeOdds']
                    game['away_spread'][line['sportsbook']] = line[_line]['awaySpread']
                    game['away_spread_odds'][line['sportsbook']] = line[_line]['awayOdds']
            if 'totals' in event and 'oddsViews' in event['totals']:
                for line in event['totals']['oddsViews']:
                    if not line:
                        continue
                    game['under_odds'][line['sportsbook']] = line[_line]['underOdds']
                    game['over_odds'][line['sportsbook']] = line[_line]['overOdds']
                    game['total'][line['sportsbook']] = line[_line]['total']
            if 'moneylines' in event and 'oddsViews' in event['moneylines'] and event['moneylines']['oddsViews']:
                for line in event['moneylines']['oddsViews']:
                    if not line:
                        continue
                    game['home_ml'][line['sportsbook']] = line[_line]['homeOdds']
                    game['away_ml'][line['sportsbook']] = line[_line]['awayOdds']
            games.append(game)
        self.games = games
    
    def get_totals(self, home_team=None, away_team=None):
        """
        Get totals for a specific game by team names, or all games if no teams specified
        Returns a dictionary with format {'TeamAvsTeamB': total_value}
        where total_value is the first half-point total found, or rounded nearest half
        """
        def process_total(totals_dict):
            if not totals_dict:
                return None
            # First try to find a value that ends in .5
            for total in totals_dict.values():
                if total and total % 1 == 0.5:
                    return total
            # If no .5 found, take the first valid number and round to nearest .5
            for total in totals_dict.values():
                if total:
                    return round(total * 2) / 2
            return None

        if home_team is None and away_team is None:
            return {f"{game['home_team']}vs{game['away_team']}": process_total(game['total']) 
                    for game in self.games}
        
        for game in self.games:
            if (game['home_team'] == home_team and game['away_team'] == away_team):
                return {f"{home_team}vs{away_team}": process_total(game['total'])}
            elif (game['home_team'] == away_team and game['away_team'] == home_team):
                return {f"{away_team}vs{home_team}": process_total(game['total'])}
        return {}
