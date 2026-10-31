# OMDb Crawler

Asks the [OMDb API](https://www.omdbapi.com/) about every T2S movie and series that has an IMDb id, and keeps in MariaDB what the other sources of the stack do not carry: the Rotten Tomatoes and Metacritic scores, the awards summary in text and the US box office.

## What it stores

One row per IMDb id in `T_WC_OMDB_TITLE` (reference DDL: [doc/sql/T_WC_OMDB_TITLE.sql](doc/sql/T_WC_OMDB_TITLE.sql); the crawler creates the table on its first run):

- `RT_SCORE` (Rotten Tomatoes, percent), `METACRITIC_SCORE` and `METASCORE` (out of 100);
- `AWARDS`, the awards summary in text ("Won 4 Oscars. 157 wins & 220 nominations total");
- `BOX_OFFICE_USD` (US gross, from "$292,587,330") and `BOX_OFFICE_TEXT`;
- `IMDB_RATING`, `IMDB_VOTES`, `RATED`, `PRODUCTION`, `TOTAL_SEASONS`, `OMDB_TYPE`, `TITLE`, `YEAR_TEXT`;
- the whole answer in `RAW_JSON`, so a field not split into a column today stays readable;
- `RESPONSE_OK` (0 for "not found", with `ERROR_TEXT`) and `TIM_OMDB_FETCHED`.

## Order of work

Within a daily request budget:

1. ids never fetched, most IMDb votes first;
2. ids fetched more than `OMDB_REFRESH_DAYS` ago, oldest first. "Not found" answers are retried at the same age.

The budget is counted per Paris day in the server variables `stromdbcrawlerrequestday` and `stromdbcrawlerrequestcount`, so several runs in one day share it. "Request limit reached!" or an invalid key stops the run at once. Run telemetry: `stromdbcrawlerstartdatetime`, `stromdbcrawlerenddatetime`, `stromdbcrawlertotalruntime`, `stromdbcrawlercurrentprocess`, `stromdbcrawlerlastresult`.

At 950 requests a day, the ~450,000 ids take more than a year; the most voted titles come in the first weeks.

## Configuration

Copy `.env.example` to `.env` (same database keys as the other crawlers) and set `OMDB_API_KEY` (free key: https://www.omdbapi.com/apikey.aspx, 1,000 requests a day). Optional keys: `OMDB_DAILY_LIMIT` (default 950), `OMDB_REFRESH_DAYS` (90), `OMDB_REQUEST_DELAY_SECONDS` (1), `OMDB_MAX_RETRIES` (4), `OMDB_API_URL` (default `https://www.omdbapi.com/`).

## Deployment (VPS)

```bash
cd ~/docker && git clone https://github.com/vaugouin/omdb-crawler.git
cd omdb-crawler && cp ../imdb-crawler/.env .env && nano .env   # add the OMDB_* keys
./omdb-crawler.sh && docker logs -f omdb-crawler
```

Cron, once a day:

```
20 4 * * * bash /home/debian/docker/omdb-crawler/omdb-crawler.sh >> /home/debian/docker/omdb-crawler/omdb-cron.log 2>&1
```

`off.sh` writes the flag file `CRON_OFF`, which makes the wrapper exit at once, and `on.sh` deletes it: that disables and enables the cron run.

## Licence of the data

OMDb content is licensed CC BY-NC 4.0: non-commercial use only, with attribution. The code of this repository is MIT.
