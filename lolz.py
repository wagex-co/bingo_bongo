from src.sbrscrape import Scoreboard, SPORT_DICT


sb = Scoreboard(sport="NFL", date="2024-12-15")
# print(sb)
totals = sb.get_totals()
# ml = sb.get_ml()

print(totals)
# print(ml)

# scores = sb.get_scores()
# print(scores)

