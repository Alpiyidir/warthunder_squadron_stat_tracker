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
                playerRatings[playerKey] = {}
            elif rowCounter == 2:
                playerRatings[playerKey] = row.text

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
        self.go_to_squadron_page(squadronName)

        playerRatings = self.get_players_ratings_from_squadron(squadronName)

        for player in playerRatings:
            print("")

    def update_info_for_all_squadrons(self):
        print("")

    @staticmethod
    def get_player_rating_from_db(playerName):
        conn = sqlite3.connect("squadronstats.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT rating FROM activity WHERE player_id IN(SELECT id FROM players WHERE name = ?)", [playerName])
        row = c.fetchone()

        if not row:
            conn.close()
            return -1
        else:
            conn.close()
            return row["rating"]


a = SquadronInfoTracker()
print(a.get_player_rating_from_squadron("Immortal Legion", "ExoSin"))
print(a.get_player_rating_from_db("Alpiyidir"))
