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

client = commands.Bot(command_prefix=commandPrefix, intents=intents)


@client.event
async def on_ready():
    print("Wakey wakey, I am awake.")


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

    ratingUpdates = await tr.get_player_rating_from_db(name, startUnix, endUnix)

    if ratingUpdates == -1:
        await interaction.response.send_message("No record found with specified parameters.")
        return

    if displaymode == "singular":
        message = "Displaying rating updates for {0}:\n\n".format(name)
        for update in ratingUpdates:
            message += "\t{0}: {1}\n".format(datetime.datetime.fromtimestamp(update["timestamp"]),
                                             update["rating"])
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
    ratingInfo = await tr.get_player_rating_from_db(name)
    rating = ratingInfo["rating"]
    timestamp = ratingInfo["timestamp"]
    date = datetime.datetime.fromtimestamp(timestamp)

    if rating == -1:
        await interaction.response.send_message("Player {0} not found in database.".format(name))
    else:
        await interaction.response.send_message("```Current rating for {0}: {1} at {2}```".format(name, rating, date))


database_update_loop.start()
client.run("OTk3Mjg3MjQ0MzgzNjYyMDkx.GLRKvQ.g3HnF5BaoOLQC5uwzWL4vr3DEq12MEZ1wj3e3o")
