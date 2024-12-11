from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import requests
import re
import json

SPORT_DICT = {
    "NBA": "nba-basketball",
    "NFL": "nfl-football",
    "NHL": "nhl-hockey",
    "MLB": "mlb-baseball",
    "NCAAB": "ncaa-basketball",
    "EPL": "english-premier-league",
    "UCL": "champions-league"
}

@dataclass
class Team:
    full_name: str
    display_name: str
    short_name: str
    rank: Optional[int]

@dataclass
class Game:
    date: str
    status: str
    home_team: Team
    away_team: Team
    home_score: int
    away_score: int
    home_spread: Dict[str, float]
    home_spread_odds: Dict[str, int]
    away_spread: Dict[str, float]
    away_spread_odds: Dict[str, int]
    under_odds: Dict[str, int]
    over_odds: Dict[str, int]
    total: Dict[str, float]
    home_ml: Dict[str, int]
    away_ml: Dict[str, int]

    @classmethod
    def from_event(cls, event: dict, line_type: str) -> 'Game':
        spreads = event['spreads']
        totals = event['totals']
        moneylines = event['moneylines']
        
        game_view = spreads['gameView']
        
        return cls(
            date=game_view['startDate'],
            status=game_view['gameStatusText'],
            home_team=Team(
                full_name=game_view['homeTeam']['fullName'],
                display_name=game_view['homeTeam']['displayName'],
                short_name=game_view['homeTeam']['shortName'],
                rank=game_view['homeTeam']['rank']
            ),
            away_team=Team(
                full_name=game_view['awayTeam']['fullName'],
                display_name=game_view['awayTeam']['displayName'],
                short_name=game_view['awayTeam']['shortName'],
                rank=game_view['awayTeam']['rank']
            ),
            home_score=game_view['homeTeamScore'],
            away_score=game_view['awayTeamScore'],
            home_spread={line['sportsbook']: line[line_type]['homeSpread'] for line in spreads['oddsViews'] if line},
            home_spread_odds={line['sportsbook']: line[line_type]['homeOdds'] for line in spreads['oddsViews'] if line},
            away_spread={line['sportsbook']: line[line_type]['awaySpread'] for line in spreads['oddsViews'] if line},
            away_spread_odds={line['sportsbook']: line[line_type]['awayOdds'] for line in spreads['oddsViews'] if line},
            under_odds={line['sportsbook']: line[line_type]['underOdds'] for line in totals.get('oddsViews', []) if line},
            over_odds={line['sportsbook']: line[line_type]['overOdds'] for line in totals.get('oddsViews', []) if line},
            total={line['sportsbook']: line[line_type]['total'] for line in totals.get('oddsViews', []) if line},
            home_ml={line['sportsbook']: line[line_type]['homeOdds'] for line in moneylines.get('oddsViews', []) if line},
            away_ml={line['sportsbook']: line[line_type]['awayOdds'] for line in moneylines.get('oddsViews', []) if line}
        )

class Scoreboard:
    def __init__(self, sport='NBA', date="", current_line=True):
        self.games: List[Game] = []
        try:
            self.scrape_games(sport, date, current_line)
        except Exception as e:
            print(f"An error occurred: {e}")

    def _fetch_data(self, url: str) -> dict:
        response = requests.get(url)
        return response.json()

    def _process_game_rows(self, json_data: dict) -> Dict[str, dict]:
        game_list = []
        for item in json_data['pageProps']['oddsTables']:
            game_list.extend(item['oddsTableModel']['gameRows'])
        return {g['gameView']['gameId']: g for g in game_list}

    def scrape_games(self, sport="NBA", date="", current_line=True):
        date = date or datetime.today().strftime("%Y-%m-%d")
        line_type = 'currentLine' if current_line else 'openingLine'

        initial_url = f"https://www.sportsbookreview.com/betting-odds/{SPORT_DICT[sport]}/?date={date}"
        build_id = json.loads(re.findall('__NEXT_DATA__" type="application/json">(.*?)</script>', 
                                       requests.get(initial_url).text)[0])['buildId']

        base_url = f"https://www.sportsbookreview.com/_next/data/{build_id}/betting-odds/{SPORT_DICT[sport]}"
        spreads = self._process_game_rows(self._fetch_data(f"{base_url}.json?league={SPORT_DICT[sport]}&date={date}"))
        moneylines = self._process_game_rows(self._fetch_data(f"{base_url}/money-line/full-game.json?league={SPORT_DICT[sport]}&oddsType=money-line&oddsScope=full-game&date={date}"))
        totals = self._process_game_rows(self._fetch_data(f"{base_url}/totals/full-game.json?league={SPORT_DICT[sport]}&oddsType=totals&oddsScope=full-game&date={date}"))

        all_stats = {
            game_id: {'spreads': spreads[game_id], 'moneylines': moneylines[game_id], 'totals': totals[game_id]}
            for game_id in spreads.keys()
        }

        self.games = [Game.from_event(event, line_type) for event in all_stats.values()]

    def get_totals(self, home_team: Optional[str] = None, away_team: Optional[str] = None) -> Dict[str, float]:
        def process_total(totals_dict: Dict[str, float]) -> Optional[float]:
            if not totals_dict:
                return None

            half_point = next((total for total in totals_dict.values() if total and total % 1 == 0.5), None)
            if half_point is not None:
                return half_point

            first_valid = next((total for total in totals_dict.values() if total), None)
            return round(first_valid * 2) / 2 if first_valid else None

        if not home_team and not away_team:
            return {f"{game.home_team.full_name}vs{game.away_team.full_name}": process_total(game.total) 
                    for game in self.games}

        for game in self.games:
            if (game.home_team.full_name == home_team and game.away_team.full_name == away_team):
                return {f"{home_team}vs{away_team}": process_total(game.total)}
            elif (game.home_team.full_name == away_team and game.away_team.full_name == home_team):
                return {f"{away_team}vs{home_team}": process_total(game.total)}
        return {}

    def get_ml(self, home_team: Optional[str] = None, away_team: Optional[str] = None) -> Dict[str, Dict[str, int]]:
        def process_ml(home_ml: Dict[str, int], away_ml: Dict[str, int]) -> Dict[str, int]:
            if not home_ml or not away_ml:
                return {}
            return {
                'home': next((odds for odds in home_ml.values() if odds), None),
                'away': next((odds for odds in away_ml.values() if odds), None)
            }

        if not home_team and not away_team:
            return {f"{game.home_team.full_name}vs{game.away_team.full_name}": process_ml(game.home_ml, game.away_ml) 
                    for game in self.games}

        for game in self.games:
            if (game.home_team.full_name == home_team and game.away_team.full_name == away_team):
                return {f"{home_team}vs{away_team}": process_ml(game.home_ml, game.away_ml)}
            elif (game.home_team.full_name == away_team and game.away_team.full_name == home_team):
                return {f"{away_team}vs{home_team}": process_ml(game.away_ml, game.home_ml)}  # Note: ML odds are swapped here
        return {}
