import matplotlib.pyplot as plt
from nba_api.stats.static import players
from nba_api.stats.static import teams
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.library.parameters import SeasonAll
from nba_api.stats.endpoints import commonplayerinfo
from nba_api.stats.endpoints import playerawards
from nba_api.stats.endpoints import playercareerstats

import pandas as pd

# kobe stats
kobe_ppg = 25
kobe_reb = 5.2
kobe_ast = 4.7
kobe_height = "6-6"
kobe_weight = 212
kobe_all_NBA = 15
kobe_all_def = 12
kobe_mvp = 1


def getActivePlayersId():
    players_dict = players.get_players()
    active_players = [player for player in players_dict if player["is_active"] == True]
    # active_players_df = active_players.get_data_frames()[0]
    # convert list of dictionaries to pandas df
    active_players_df = pd.DataFrame(active_players)
    # get active players' id
    active_players_id_df = active_players_df["id"]
    # convert panda series of players' id to list
    active_players_id_list = active_players_id_df.tolist()
    # these elements seem to have a problem
    del active_players_id_list[3]
    del active_players_id_list[48]
    del active_players_id_list[79]
    del active_players_id_list[505]
    del active_players_id_list[507]
    return active_players_id_list


active_players_ids = getActivePlayersId()


def getPlayerStats():
    all_players_stats = []

    # very slow to retrieve data from api, stored data locally in active_players_info.txt for faster load

    for i in range(len(active_players_ids)):
        player_id = active_players_ids[i]
        # print(player_id)
        player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        player_info = player_info.get_normalized_dict()
        # print(player_info)
        player_fullname = player_info.get('CommonPlayerInfo')[0]['DISPLAY_FIRST_LAST']
        player_height = player_info.get('CommonPlayerInfo')[0]['HEIGHT']
        player_weight = player_info.get('CommonPlayerInfo')[0]['WEIGHT']
        season_ppg = player_info.get('PlayerHeadlineStats')[0]["PTS"]
        season_ast = player_info.get('PlayerHeadlineStats')[0]["AST"]
        season_reb = player_info.get('PlayerHeadlineStats')[0]["REB"]
        players_dict = {"id": player_id, "full_name": player_fullname, "PPG": season_ppg, "AST": season_ast,
                        "REB": season_reb, "HEIGHT": player_height, "WEIGHT": player_weight}
        all_players_stats.append(players_dict)

    all_players_stats_df = pd.DataFrame(all_players_stats)
    return all_players_stats_df


def filter_players_above_20_ppg(all_players_stats_df):
    players_above_20ppg = all_players_stats_df.loc[(all_players_stats_df["PPG"] >= 20)]
    return players_above_20ppg


player_above_20_df = filter_players_above_20_ppg(getPlayerStats())


def similarity_score_system_stats(players_info_df):
    # create new col for similarity score
    players_info_df["similarity_score"] = 0

    # STATS COMPARISION

    # players whose PPG are +-1 compared to kobe (kobe averaged 25ppg) increase similarity points by 1
    players_info_df.loc[(players_info_df["PPG"] >= (kobe_ppg - 1)) & (
            players_info_df["PPG"] <= (kobe_ppg + 1)), "similarity_score"] += 1
    # players whose REB are +-1 compared to kobe (kobe averaged 5.2rpg) increase similarity points by 1
    players_info_df.loc[(players_info_df["REB"] >= (kobe_reb - 1)) & (
            players_info_df["REB"] <= (kobe_reb + 1)), "similarity_score"] += 1
    # players whose AST are +-1 compared to kobe's (kobe averaged 5.2rpg) increase similarity points by 1
    players_info_df.loc[(players_info_df["AST"] >= (kobe_ast - 1)) & (
            players_info_df["AST"] <= (kobe_ast + 1)), "similarity_score"] += 1

    # PHYSICALS COMPARISON

    # players who are 6-6 in height (kobe's height is 6-6)
    players_info_df.loc[players_info_df["HEIGHT"] == kobe_height, "similarity_score"] += 1
    # players who are +- 10 lbs compared to kobe (kobe weighs 212lbs)
    # convert "WEIGHT" column from String to Integer for easy comparison
    players_info_df["WEIGHT"] = pd.to_numeric(players_info_df["WEIGHT"])
    players_info_df.loc[(players_info_df["WEIGHT"] >= (kobe_weight - 10)) & (
            players_info_df["WEIGHT"] <= (kobe_weight + 10)), "similarity_score"] += 1

    # only return players who have score at least 1 similarity point
    eligible_players_df = players_info_df.loc[players_info_df["similarity_score"] > 0]
    return eligible_players_df


eligible_players_by_stats_df = similarity_score_system_stats(player_above_20_df)


def similarity_score_awards(final_players_df):
    final_players_df["all_nba_count"] = 0
    final_players_df["all_def_count"] = 0
    final_players_df["mvp_count"] = 0

    eligible_players_id_list = eligible_players_by_stats_df["id"].tolist()
    for i in range(len(eligible_players_id_list)):
        current_player_id = eligible_players_id_list[i]

        # get player accolades
        kobe_awards = playerawards.PlayerAwards(player_id=current_player_id)
        kobe_awards_df = kobe_awards.get_data_frames()[0]
        all_nba_count = kobe_awards_df.loc[kobe_awards_df.DESCRIPTION == "All-NBA", "DESCRIPTION"].count()
        all_def_count = kobe_awards_df.loc[kobe_awards_df.DESCRIPTION == "All-Defensive Team", "DESCRIPTION"].count()
        mvp_count = kobe_awards_df.loc[kobe_awards_df.DESCRIPTION == "NBA Most Valuable Player", "DESCRIPTION"].count()

        # add players' accolades to df
        final_players_df.loc[
            eligible_players_by_stats_df["id"] == current_player_id, "all_nba_count"] += all_nba_count
        final_players_df.loc[
            eligible_players_by_stats_df["id"] == current_player_id, "all_def_count"] += all_def_count
        final_players_df.loc[eligible_players_by_stats_df["id"] == current_player_id, "mvp_count"] += mvp_count

    # ACCOLADES COMPARISON (2 POINTS FOR EACH CATEGORY INSTEAD OF 1 POINT)

    # players with +- 3 all NBA selections
    final_players_df.loc[(final_players_df["all_nba_count"] >= (kobe_all_NBA - 3)) & (
            final_players_df["all_nba_count"] <= (kobe_all_NBA + 3)), "similarity_score"] += 2
    # players with +- 3 all def selections
    final_players_df.loc[(final_players_df["all_def_count"] >= (kobe_all_def - 3)) & (
            final_players_df["all_def_count"] <= (kobe_all_def + 3)), "similarity_score"] += 2
    # players with at least 1 MVP (Kobe had 1 league MVP)
    final_players_df.loc[final_players_df["mvp_count"] >= kobe_mvp, "similarity_score"] += 2

    return final_players_df


eligible_players_by_stats_df_copy = eligible_players_by_stats_df.copy()
final_players_df = similarity_score_awards(eligible_players_by_stats_df_copy)

# sort players in ascending order based on their similarity score
final_players_df_sorted = final_players_df.sort_values(by=["similarity_score"]).iloc[-15:]

# time to display the data through a scatter plot!
final_plot = final_players_df_sorted.plot.scatter(x="full_name", y="similarity_score", s=100, marker='x')
final_plot.set_ylabel("Similarity Score", fontsize=20)
plt.suptitle("Top 15 Players Most Similar to Kobe", fontsize=20)
plt.xticks(fontsize=7, rotation=90)
plt.show()

# not in use
def player_basic_info_test():
    players_dict = players.get_players()
    lebron = [player for player in players_dict if player["full_name"] == "LeBron James"]
    print(lebron[0])
    lebron_id = lebron[0]["id"]

    gamelog_bron_all = playergamelog.PlayerGameLog(player_id=lebron_id, season=SeasonAll.all)
    print(gamelog_bron_all)

# not in use
def player_stats_test():
    # template for 1 player
    player_info = commonplayerinfo.CommonPlayerInfo(player_id=2544)
    print(player_info.get_normalized_dict())
    player_info = player_info.get_normalized_dict()
    player_fullname = player_info.get('CommonPlayerInfo')[0]['DISPLAY_FIRST_LAST']
    season_ppg = player_info.get('PlayerHeadlineStats')[0]["PTS"]
    season_ast = player_info.get('PlayerHeadlineStats')[0]["AST"]
    season_reb = player_info.get('PlayerHeadlineStats')[0]["REB"]
    print(player_fullname, season_ppg, season_ast, season_reb)

# not in use
def player_accolades_and_advance_stats_test():
    # Kobe player ID : 977
    kobe_career = playercareerstats.PlayerCareerStats(player_id='977')
    kobe_df = kobe_career.get_data_frames()[0]
    # print(kobe_df)

    kobe_awards = playerawards.PlayerAwards(player_id='977')
    kobe_awards_df = kobe_awards.get_data_frames()[0]
    all_nba_count = kobe_awards_df.loc[kobe_awards_df.DESCRIPTION == "All-NBA", "DESCRIPTION"].count()
    all_def_count = kobe_awards_df.loc[kobe_awards_df.DESCRIPTION == "All-Defensive Team", "DESCRIPTION"].count()
    mvp_count = kobe_awards_df.loc[kobe_awards_df.DESCRIPTION == "NBA Most Valuable Player", "DESCRIPTION"].count()
    # count = kobe_awards_df.DESCRIPTION.value_counts()
    kobe_accolades = (all_nba_count, all_def_count, mvp_count)
    print(kobe_accolades)
    return kobe_accolades
