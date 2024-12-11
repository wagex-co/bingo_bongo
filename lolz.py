from src.sbrscrape import Scoreboard, SPORT_DICT


sb = Scoreboard(sport="NHL", date="2024-12-11")
totals = sb.get_totals()
ml = sb.get_ml()

print(totals)
print(ml)



