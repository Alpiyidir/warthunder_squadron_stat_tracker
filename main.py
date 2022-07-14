import sqlite3

import time

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

caps = DesiredCapabilities().CHROME
caps["pageLoadStrategy"] = "none"

options = Options()
options.add_argument("--headless")


class SquadronInfoTracker:
    def __init__(self):
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def quit(self):
        self.driver.close()

    def go_to_squadron_page(self, squadronName):
        splitSquadronName = squadronName.split()
        squadronInfoLink = "https://warthunder.com/en/community/claninfo/"
        for i in range(len(splitSquadronName)):
            squadronInfoLink += splitSquadronName[i]

            # If the current word is not the last word %20 is added to show the presence of a space
            if not i == len(splitSquadronName) - 1:
                squadronInfoLink += "%20"

        self.driver.get(squadronInfoLink)

    def get_players_ratings_from_squadron(self, squadronName):
        self.go_to_squadron_page(squadronName)

        table = self.driver.find_element(By.CLASS_NAME, "squadrons-members__table")

        tableElements = table.find_elements(By.CLASS_NAME, "squadrons-members__grid-item")

        # Gets first 6 elements from tableElements and converts the divs into text and stores header
        headers = tableElements[slice(0, 6)]
        for i, e in enumerate(headers):
            headers[i] = e.text

        # Removes headers from tableElements
        tableElements = tableElements[slice(6, len(tableElements))]

        playerRatings = {}
        rowCounter = 0
        for row in tableElements:
            if rowCounter == 1:
                playerKey = row.text.lower()
            elif rowCounter == 2:
                playerRatings[playerKey] = int(row.text)

            rowCounter += 1
            if rowCounter == 6:
                rowCounter = 0

        return playerRatings

    def get_player_rating_from_squadron(self, squadronName, playerName):
        playerRatings = self.get_players_ratings_from_squadron(squadronName)

        if playerName.lower() in playerRatings.keys():
            return playerRatings[playerName.lower()]
        else:
            print("Player not found in specified squadron.")
            return -1

    def update_squadron_info(self, squadronName):
        playerRatings = self.get_players_ratings_from_squadron(squadronName)

        conn = sqlite3.connect("squadronstats.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Checks to see if squadron entry exists in squadron table, if not adds it to the table
        c.execute("SELECT id FROM squadrons WHERE name = ?", [squadronName])
        squadron = c.fetchone()

        if squadron:
            currentSquadronId = squadron["id"]
        # Else, this is the first instance of this squadron being updated so the squadron name is added to the sq. table
        else:
            c.execute("INSERT INTO squadrons (name) VALUES (?)", [squadronName])
            conn.commit()

            c.execute("SELECT id FROM squadrons WHERE name = ?", [squadronName])
            currentSquadronId = c.fetchone()["id"]

        for playerName, currentRating in playerRatings.items():
            c.execute("SELECT id FROM players WHERE name = ?", [playerName])
            player = c.fetchone()

            # If player is not already in the database, creates a new entry for them and gets their id, otherwise uses
            # existing id
            if player:
                playerId = player["id"]
            else:
                c.execute("INSERT INTO players (name) VALUES (?)", [playerName])
                conn.commit()
                c.execute("SELECT id FROM players WHERE name = ?", [playerName])
                playerId = c.fetchone()["id"]

            # If player is already in the database checks if the last rating entry has the same rating as the current
            # rating entry, otherwise, it just writes the current rating entry as the player has never been logged
            # before
            currentTime = int(time.time())
            dbUpdatedForPlayer = False
            # Fetches most recent rating entry using timestamp
            c.execute(
                "SELECT rating, squadron_id, timestamp FROM activity WHERE player_id = ? ORDER BY timestamp DESC LIMIT 1",
                [playerId])
            playerInfo = c.fetchone()
            if playerInfo:
                dbRating = playerInfo["rating"]
                dbSquadronId = playerInfo["squadron_id"]
                dbTimestamp = playerInfo["timestamp"]

                # If the current rating of the player is the same as the database entry is the same, no new entry is
                # created and the timestamp for the db entry is edited, otherwise, a new entry with the new timestamp of
                # the time this rating was first seen is created
                if currentRating == dbRating and currentSquadronId == dbSquadronId:
                    c.execute("UPDATE activity SET timestamp = ? WHERE player_id = ? AND timestamp = ?",
                              [currentTime, playerId, dbTimestamp])
                    conn.commit()
                    dbUpdatedForPlayer = True
                # This condition means that the player has changed squadrons, therefore their name is removed from the
                elif currentSquadronId != dbSquadronId:
                    # TODO think about what can be done in this case
                    pass

            # If no action has yet been done on the db, there either wasn't a player that existed, or if there was a
            # player that previously existed in the db their rating/squadron has changed therefore a new entry is made
            if not dbUpdatedForPlayer:
                c.execute("INSERT INTO activity (player_id, squadron_id, rating, timestamp) VALUES (?, ?, ?, ?)",
                          [playerId, currentSquadronId, currentRating, currentTime])
                conn.commit()

        conn.close()

    # TODO check for auto redirects
    def update_info_for_all_squadrons(self):
        conn = sqlite3.connect("squadronstats.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT name FROM squadrons")
        squadrons = c.fetchall()
        for squadron in squadrons:
            print(squadron["name"])
            self.update_squadron_info(squadron["name"])

    # TODO don't forget if a player changes squadrons during the player search they will have to get added to the list
    # TODO again, if this happens nuke their old player entry in the table until their new squadron is added
    @staticmethod
    def get_player_rating_from_db(playerName):
        conn = sqlite3.connect("squadronstats.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute(
            "SELECT rating, squadron_info FROM activity WHERE player_id IN(SELECT id FROM players WHERE name = ?) ORDER BY timestamp DESC",
            [playerName])
        row = c.fetchone()

        if not row:
            conn.close()
            return -1
        else:
            conn.close()
            return row["rating"]


a = SquadronInfoTracker()
#print(a.get_player_rating_from_squadron("Immortal Legion", "Alpiyidir"))
#print(a.get_player_rating_from_db("Alpiyidir"))
a.update_info_for_all_squadrons()
a.quit()
