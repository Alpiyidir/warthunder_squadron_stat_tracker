import beautifultracker as tr

import datetime
from datetime import timezone

import nextcord
from nextcord import Interaction
from nextcord.ext import commands, tasks

intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True

commandPrefix = "#"

squibTimeZones = {"EU": [14, 22], "US": [2, 8]}

client = commands.Bot(command_prefix=commandPrefix, intents=intents)


@client.event
async def on_ready():
    print("Wakey wakey, I am awake.")
    database_update_loop.start()


@tasks.loop(seconds=120)
async def database_update_loop():
    await tr.update_info_for_all_squadrons()


# This never gets called as it has subcommands.
@client.slash_command(name="search")
async def search(interaction: Interaction):
    pass


@search.subcommand(name="date",
                   description="Gets activity of a player for the time interval chosen, times in UTC.")
async def date(interaction: Interaction,
               name: str = nextcord.SlashOption(required=True, description="Player name in war thunder"),
               startday: int = nextcord.SlashOption(required=True, description="Start day"),
               startmonth: int = nextcord.SlashOption(required=True, description="Start month"),
               startyear: int = nextcord.SlashOption(required=True, description="Start year"),
               endday: int = nextcord.SlashOption(default=datetime.datetime.utcnow().day, description="End day"),
               endmonth: int = nextcord.SlashOption(default=datetime.datetime.utcnow().month, description="End month"),
               endyear: int = nextcord.SlashOption(default=datetime.datetime.utcnow().year, description="End year"),
               displaymode: str = nextcord.SlashOption(choices={"singular": "singular", "net": "net"},
                                                       default="singular",
                                                       description="Whether to show activity one by one (singular) default, or net change (net)")):
    invalidStart = False
    invalidEnd = False

    try:
        startDate = datetime.datetime(startyear, startmonth, startday, tzinfo=timezone.utc)
    except ValueError:
        invalidStart = True

    # Fyi, the end date is set one day forward as otherwise it takes 00:00 (midnight) as the start time, searching for
    # all days preceding the end date
    try:
        endDate = datetime.datetime(endyear, endmonth, endday, tzinfo=timezone.utc) + datetime.timedelta(days=1)
    except ValueError:
        invalidEnd = True

    # Now some logic checks.
    if startDate > endDate:
        await interaction.response.send_message("Start date is later in time than the end date.")
        return

    unixTimeEpoch = datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
    if startDate < unixTimeEpoch and endDate < unixTimeEpoch:
        await interaction.response.send_message("Start and end date cannot both be prior to unix time epoch, 1/1/1970")
        return
    elif startDate < unixTimeEpoch:
        await interaction.response.send_message("Start date cannot be prior to unix time epoch, 1/1/1970")
        return
    elif endDate < unixTimeEpoch:
        await interaction.response.send_message("End date cannot be prior to unix time epoch, 1/1/1970")
        return

    if invalidStart and invalidStart:
        await interaction.response.send_message("Invalid start and end date.")
        return
    elif invalidStart:
        await interaction.response.send_message("Invalid start date.")
        return
    elif invalidEnd:
        await interaction.response.send_message("Invalid end date.")
        return

    startUnix = startDate.timestamp()
    endUnix = endDate.timestamp()

    ratingUpdates = await tr.get_player_rating_from_db(playerName=name, timeRange={"start": startUnix, "end": endUnix})

    if ratingUpdates == -1:
        await interaction.response.send_message("No record found with specified parameters.")
        return

    if displaymode == "singular":
        message = "Displaying rating updates for {0}:\n".format(name)

        validUpdateCount = 0
        winCount = 0
        previous = {"interval": None, "rating": None, "date": None}
        lastRatingBeforeSession = None
        lastUpdate = False
        tmpMessage = ""
        for i, update in enumerate(ratingUpdates):
            updateDate = datetime.datetime.utcfromtimestamp(update["timestamp"])
            currentUnixInterval = await create_unix_time_zone_for_timeslot(updateDate)

            if i == 0:
                # If this entry is the first ever entry in the ratingUpdates, then db has to fetch latest entry prior to
                # this first entry
                lastRatingBeforeSession = await tr.get_player_rating_from_db(playerName=name,
                                                                             getPreviousToTimestamp=update[
                                                                                 "timestamp"])
                # -1 means that there are no rating entries prior to this rating from the same squadron, so the
                # current entry is the first ever recorded entry
                if lastRatingBeforeSession == -1:
                    lastRatingBeforeSession = update["rating"]
                    message += "\n\t{0}: {1} FIRST ENTRY\n".format(
                        updateDate,
                        lastRatingBeforeSession)
                    continue
                else:
                    lastRatingBeforeSession = lastRatingBeforeSession["rating"]

            if i > 0:
                previous["date"] = datetime.datetime.utcfromtimestamp(ratingUpdates[i - 1]["timestamp"])
                previous["interval"] = await create_unix_time_zone_for_timeslot(previous["date"])
                previous["rating"] = ratingUpdates[i - 1]["rating"]

            if i == len(ratingUpdates) - 1:
                lastUpdate = True

            # first parameter is pretty self explanatory, if previous["interval"] == -1 then there has already been an
            # entry made for the previous run of this loop where a timeslot message was appened to the message, so this
            # run is ignored for one loop until the next interval can be checked, this is done so that if the first
            if previous["interval"] != currentUnixInterval and previous["interval"] != -1:
                netChange = previous["rating"] - lastRatingBeforeSession
                # Net change won't work for first timeslot entry of the list
                if previous["interval"] != -1:
                    tmpMessage = await create_timeslot_msg(previous["interval"]["timeslotName"],
                                                           updateDate.strftime("%d/%m/%y"),
                                                           netChange, winCount, validUpdateCount) + tmpMessage

                validUpdateCount = 0
                winCount = 0
                message += tmpMessage
                if currentUnixInterval == -1:
                    message += "\n\t{0}: {1} UNKNOWN TIMESLOT\n".format(
                        updateDate,
                        lastRatingBeforeSession)
                lastRatingBeforeSession = update["rating"]
                tmpMessage = ""

            win = "L"
            if previous["rating"]:
                if update["rating"] > previous["rating"]:
                    win = "W"
            elif lastRatingBeforeSession:
                if update["rating"] > lastRatingBeforeSession:
                    win = "W"

            if win == "W":
                winCount += 1

            tmpMessage += "\t{0}: {1} {2}\n".format(
                updateDate,
                update["rating"], win)

            if lastUpdate and lastRatingBeforeSession:
                if previous["rating"]:
                    netChange = update["rating"] - lastRatingBeforeSession
                else:
                    netChange = update["rating"]
                # Net change won't work for first timeslot entry of the list

                message += await create_timeslot_msg(previous["interval"]["timeslotName"],
                                                     updateDate.strftime("%d/%m/%y"),
                                                     netChange, winCount, validUpdateCount) + tmpMessage
            validUpdateCount += 1

        await interaction.response.send_message("```{0}```".format(message))
    elif displaymode == "net":
        net = ratingUpdates[-1]["rating"] - ratingUpdates[0]["rating"]
        await interaction.response.send_message(
            "```Net rating change between {0} and {1}: {2}```".format(startDate, endDate, net))


# @search.subcommand(name="elapsedtime", description="Gets activity of a player for the past amount of time chosen.")
# async def elapsedtime(interaction: Interaction, name: str, day: int, hour: int, minute: int):
# pass


@search.subcommand(name="current", description="Gets current rating of player.")
async def current(interaction: Interaction, name: str):
    ratingRow = await tr.get_player_rating_from_db(playerName=name)

    if ratingRow == -1:
        await interaction.response.send_message("Player {0} not found in database.".format(name))
    else:
        rating = ratingRow["rating"]
        timestamp = ratingRow["timestamp"]
        date = datetime.datetime.utcfromtimestamp(timestamp)
        await interaction.response.send_message("```Current rating for {0}: {1} at {2}```".format(name, rating, date))


async def create_unix_time_zone_for_timeslot(currentDate: datetime.datetime):
    # The first part of this code decides whether it is the eu or us timeslot the activity was in
    for timeslotName, timezoneRange in squibTimeZones.items():
        timeSlotStart = datetime.datetime(currentDate.year, currentDate.month, currentDate.day, timezoneRange[0],
                                          tzinfo=timezone.utc)
        timeSlotEnd = datetime.datetime(currentDate.year, currentDate.month, currentDate.day, timezoneRange[1],
                                        tzinfo=timezone.utc)

        # By making the start time 1 hour prior, it accounts for daylight savings time (sloppily)
        timeSlotStart = (timeSlotStart + datetime.timedelta(hours=-1)).timestamp()
        # By making end 2h later, accounts for games that might end at the start of the next hour, 1h shift is the
        # normal to get end of current hr
        timeSlotEnd = (timeSlotEnd + datetime.timedelta(hours=2)).timestamp()

        if timeSlotStart <= currentDate.timestamp() <= timeSlotEnd:
            return {"start": timeSlotStart, "end": timeSlotEnd, "timeslotName": timeslotName}

    # If update doesn't fit any timeslots, then it was either the last game the player played in a timeslot and
    # is getting constantly updated
    return -1


async def create_timeslot_msg(previousTimeSlotName, dateString, netChange, winCount, gameCount):
    return "\n{0} Timeslot on {1} NET CHANGE: {2} WINRATE: {3}%\n".format(
        previousTimeSlotName,
        dateString,
        netChange, await calculate_win_rate(winCount, gameCount))


async def calculate_win_rate(wins, games):
    if games == 0:
        return -1
    else:
        return int(wins / games * 100)


client.run("OTk3Mjg3MjQ0MzgzNjYyMDkx.GLRKvQ.g3HnF5BaoOLQC5uwzWL4vr3DEq12MEZ1wj3e3o")
