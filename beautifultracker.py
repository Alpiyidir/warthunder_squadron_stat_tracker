import sqlite3

import datetime

import bs4
import http3

client = http3.AsyncClient()


async def get_squadron_page_html(squadronName):
    splitSquadronName = squadronName.split()
    squadronInfoLink = "https://warthunder.com/en/community/claninfo/"
    for i in range(len(splitSquadronName)):
        squadronInfoLink += splitSquadronName[i]

        # If the current word is not the last word %20 is added to show the presence of a space
        if not i == len(splitSquadronName) - 1:
            squadronInfoLink += "%20"

    return await client.get(squadronInfoLink)


async def get_players_ratings_from_squadron(squadronName):
    html = await get_squadron_page_html(squadronName)

    soup = bs4.BeautifulSoup(html.content, "html.parser")

    table = soup.find(class_="squadrons-members__table")

    tableElements = table.find_all(class_="squadrons-members__grid-item")

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
            playerKey = row.text.strip().lower()
        elif rowCounter == 2:
            playerRatings[playerKey] = int(row.text)

        rowCounter += 1
        if rowCounter == 6:
            rowCounter = 0

    return playerRatings


async def get_player_rating_from_squadron(squadronName, playerName):
    playerRatings = await get_players_ratings_from_squadron(squadronName)

    if playerName.lower() in playerRatings.keys():
        return playerRatings[playerName.lower()]
    else:
        print("Player not found in specified squadron.")
        return -1


async def update_squadron_info(squadronName):
    playerRatings = await get_players_ratings_from_squadron(squadronName)

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
        # Edge case, people who have emails for their names can show up as duplicates
        if "[email protected]" in playerName:
            continue

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
        currentTime = int(datetime.datetime.now().timestamp())
        ratingAndSquadronAreSame = False
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
                #c.execute("UPDATE activity SET timestamp = ? WHERE player_id = ? AND timestamp = ?",
                #          [currentTime, playerId, dbTimestamp])
                #conn.commit()
                ratingAndSquadronAreSame = True

        # If no action has yet been done on the db, there either wasn't a player that existed, or if there was a
        # player that previously existed in the db their rating/squadron has changed therefore a new entry is made
        if not ratingAndSquadronAreSame:
            c.execute("INSERT INTO activity (player_id, squadron_id, rating, timestamp) VALUES (?, ?, ?, ?)",
                      [playerId, currentSquadronId, currentRating, currentTime])
            conn.commit()

    conn.close()


# TODO check for auto redirects
async def update_info_for_all_squadrons():
    conn = sqlite3.connect("squadronstats.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT name FROM squadrons")
    squadrons = c.fetchall()
    for squadron in squadrons:
        await update_squadron_info(squadron["name"])
        print(squadron["name"])


# TODO don't forget if a player changes squadrons during the player search they will have to get added to the list
# TODO again, if this happens nuke their old player entry in the table until their new squadron is added
# only gets rating for same squadron as latest entry
async def get_player_rating_from_db(playerName, timeRange=None, getPreviousToTimestamp=None):
    # TODO ADD SEARCH WITH SQUADRON ID?
    conn = sqlite3.connect("squadronstats.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if not timeRange and not getPreviousToTimestamp:
        c.execute(
            "SELECT rating, timestamp FROM activity WHERE player_id IN(SELECT id FROM players WHERE name = ?) ORDER BY timestamp DESC",
            [playerName.lower()])
        row = c.fetchone()

        conn.close()
        if not row:
            return -1
        else:
            return row
    else:
        c.execute(
            "SELECT squadron_id FROM activity WHERE player_id IN(SELECT id FROM players WHERE name = ?) ORDER BY timestamp DESC",
            [playerName.lower()])
        squadronId = c.fetchone()

        if squadronId:
            squadronId = squadronId["squadron_id"]
        else:
            return -1

        if timeRange:
            c.execute(
                "SELECT rating, timestamp FROM activity WHERE timestamp > ? AND timestamp < ? AND squadron_id = ? AND player_id IN(SELECT id FROM players WHERE name = ?) ORDER BY timestamp ASC",
                [timeRange["start"], timeRange["end"], squadronId, playerName.lower()])
            row = c.fetchall()

            conn.close()
            if not row:
                return -1
            else:
                return row
        elif getPreviousToTimestamp:
            c.execute(
                "SELECT rating, timestamp FROM activity WHERE timestamp < ? AND squadron_id = ? AND player_id IN(SELECT id FROM players WHERE name = ?) ORDER BY timestamp DESC",
                [getPreviousToTimestamp, squadronId, playerName.lower()])
            row = c.fetchone()

            conn.close()
            if not row:
                return -1
            else:
                return row
