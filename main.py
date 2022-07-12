from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

caps = DesiredCapabilities().CHROME
caps["pageLoadStrategy"] = "none"


class SquadronInfoTracker:
    def __init__(self):
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    def go_to_squadron_page(self, squadronName):
        splitSquadronName = squadronName.split()
        squadronInfoLink = "https://warthunder.com/en/community/claninfo/"
        for i in range(len(splitSquadronName)):
            squadronInfoLink += splitSquadronName[i]

            # If the current word is not the last word %20 is added to show the presence of a space
            if not i == len(splitSquadronName) - 1:
                squadronInfoLink += "%20"

        self.driver.get(squadronInfoLink)

    def get_info_from_squadron(self, squadronName):
        self.go_to_squadron_page(squadronName)

        table = self.driver.find_element(By.CLASS_NAME, "squadrons-members__table")

        tableElements = table.find_elements(By.CLASS_NAME, "squadrons-members__grid-item")

        # Gets first 6 elements from tableElements and converts the divs into text and stores header
        headers = tableElements[slice(0, 6)]
        for i, e in enumerate(headers):
            headers[i] = e.text
            print(e.text)

        # Removes headers from tableElements
        tableElements = tableElements[slice(6, len(tableElements))]

        playerInfoDict = {}

        rowCounter = 0
        for row in tableElements:
            if rowCounter == 1:
                playerKey = row.text
                playerInfoDict[playerKey] = {}
            elif rowCounter > 1:
                playerInfoDict[playerKey][headers[rowCounter]] = row.text

            rowCounter += 1
            if rowCounter == 6:
                rowCounter = 0

        print(playerInfoDict["Alpiyidir"]["PERSONAL CLAN RATING"])


a = SquadronInfoTracker()
a.get_info_from_squadron("Immortal Legion")
