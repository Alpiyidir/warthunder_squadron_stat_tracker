# Warthunder Squadron Statistics Tracker
A Python program that consists of a web-scraping element a discord bot. The web-scraping part scrapes War Thunder players’ points from a website using beautifulsoup4. It uses this scraped data from the website to create a backlog of player points to allow for the viewing and tracking of points over time. This is possible because each point entry added to the locally hosted sqlite3 database includes a timestamp in unix time. This data can then be displayed in a discord server via a bot written using the nextcord library. The discord bot includes advanced viewing functionality that allows for the viewing of point updates between two given dates in time.