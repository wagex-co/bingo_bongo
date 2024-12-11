from src.sbrscrape import Scoreboard, SPORT_DICT


sb = Scoreboard(sport="UCL", date="2024-12-11")
# print(sb)
# totals = sb.get_totals()
# ml = sb.get_ml()

# print(totals)
# print(ml)

scores = sb.get_scores(home_team="Arsenal FC", away_team="AS Monaco")
print(scores)

