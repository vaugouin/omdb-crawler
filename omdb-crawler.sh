#!/bin/bash

# OMDb crawler (OMDB-CRAWLER-001): Rotten Tomatoes, Metacritic, awards text and US box
# office for the T2S movies and series, into T_WC_OMDB_TITLE. Within OMDB_DAILY_LIMIT
# requests per Paris day, so it can run several times a day: the runs share the budget.
# Follow: docker logs -f omdb-crawler.

# Switched off by off.sh, back on with on.sh: the flag file CRON_OFF next to this script makes
# every cron tick exit here. The script keeps its name, so the git clone stays clean.
if [ -f "$(dirname "$(readlink -f "$0")")/CRON_OFF" ]; then
    echo "CRON_OFF present: omdb-crawler switched off (bash on.sh to switch it back on)."
    exit 0
fi

if [ $(docker ps -q -f name=omdb-crawler) ]; then
    echo "omdb-crawler Docker container is already running."
else
    cd $HOME/docker/omdb-crawler
    docker build -t omdb-crawler-python-app .
    docker run -d --rm --network="host" --name omdb-crawler --env-file /home/debian/docker/omdb-crawler/.env omdb-crawler-python-app
    echo "omdb-crawler Docker container started."
fi
