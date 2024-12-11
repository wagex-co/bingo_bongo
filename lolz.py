from src.sbrscrape import Scoreboard

sb = Scoreboard(sport="NHL", date="2024-12-13")
totals = sb.get_totals()
print(totals)

