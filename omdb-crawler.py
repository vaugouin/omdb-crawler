"""
OMDb crawler (OMDB-CRAWLER-001): fetches, for the T2S movies and series that carry an
IMDb id, what the OMDb API adds to the database: the Rotten Tomatoes and Metacritic
scores, the Metascore, the awards summary in text and the US box office.

One row per IMDb id in T_WC_OMDB_TITLE (created here if absent: this crawler is its only
writer). The raw JSON is kept, so a field not split into a column today stays readable.

Order of work, within a daily request budget (OMDB_DAILY_LIMIT, free key: 1,000/day):
  1. ids never fetched, most IMDb votes first;
  2. ids fetched more than OMDB_REFRESH_DAYS ago, oldest first.
"Not found" answers are stored too (RESPONSE_OK = 0) and retried at the refresh age.
The budget is counted per Paris day in server variables, so several runs in one day
share it. "Request limit reached!" stops the run at once.

    ./omdb-crawler.sh
"""

import json
import os
import re
import time
from datetime import datetime, timedelta

import requests

import citizenphil as cp

STR_API_URL = os.environ.get("OMDB_API_URL", "https://www.omdbapi.com/")
STR_API_KEY = os.environ.get("OMDB_API_KEY", "")
LNG_DAILY_LIMIT = int(os.environ.get("OMDB_DAILY_LIMIT") or 950)
LNG_REFRESH_DAYS = int(os.environ.get("OMDB_REFRESH_DAYS") or 90)
DBL_REQUEST_DELAY = float(os.environ.get("OMDB_REQUEST_DELAY_SECONDS") or 1.0)
INT_MAX_RETRIES = int(os.environ.get("OMDB_MAX_RETRIES") or 4)
STR_TABLE = "T_WC_OMDB_TITLE"

STR_DDL = f"""
CREATE TABLE IF NOT EXISTS {STR_TABLE} (
  `ID_IMDB` varchar(20) NOT NULL,
  `OMDB_TYPE` varchar(20) DEFAULT NULL,
  `TITLE` varchar(500) DEFAULT NULL,
  `YEAR_TEXT` varchar(20) DEFAULT NULL,
  `RESPONSE_OK` tinyint(1) NOT NULL DEFAULT 0,
  `ERROR_TEXT` varchar(255) DEFAULT NULL,
  `RT_SCORE` int(11) DEFAULT NULL,
  `METACRITIC_SCORE` int(11) DEFAULT NULL,
  `METASCORE` int(11) DEFAULT NULL,
  `IMDB_RATING` decimal(3,1) DEFAULT NULL,
  `IMDB_VOTES` int(11) DEFAULT NULL,
  `AWARDS` varchar(1000) DEFAULT NULL,
  `BOX_OFFICE_USD` bigint(20) DEFAULT NULL,
  `BOX_OFFICE_TEXT` varchar(50) DEFAULT NULL,
  `RATED` varchar(30) DEFAULT NULL,
  `PRODUCTION` varchar(500) DEFAULT NULL,
  `TOTAL_SEASONS` int(11) DEFAULT NULL,
  `RAW_JSON` mediumtext DEFAULT NULL,
  `TIM_OMDB_FETCHED` datetime DEFAULT NULL,
  `DELETED` int(5) DEFAULT NULL,
  `ID_CREATOR` int(5) DEFAULT NULL,
  `DAT_CREAT` date DEFAULT NULL,
  `ID_OWNER` int(5) DEFAULT NULL,
  `TIM_UPDATED` datetime DEFAULT NULL,
  `ID_USER_UPDATED` int(5) DEFAULT NULL,
  PRIMARY KEY (`ID_IMDB`),
  KEY `RESPONSE_OK` (`RESPONSE_OK`),
  KEY `RT_SCORE` (`RT_SCORE`),
  KEY `METACRITIC_SCORE` (`METACRITIC_SCORE`),
  KEY `METASCORE` (`METASCORE`),
  KEY `BOX_OFFICE_USD` (`BOX_OFFICE_USD`),
  KEY `TIM_OMDB_FETCHED` (`TIM_OMDB_FETCHED`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def f_intornone(strvalue, strpattern=r"^(\d+)"):
    """First integer of an OMDb field ("87%", "74/100", "N/A"), or None."""
    if strvalue is None:
        return None
    objmatch = re.match(strpattern, str(strvalue).strip())
    return int(objmatch.group(1)) if objmatch else None


def f_moneyornone(strvalue):
    """"$292,587,330" to 292587330; "N/A" to None."""
    strdigits = re.sub(r"[^0-9]", "", str(strvalue or ""))
    return int(strdigits) if strdigits else None


def f_textornone(strvalue, intmaxlength):
    if strvalue is None or str(strvalue).strip() in ("", "N/A"):
        return None
    return str(strvalue).strip()[:intmaxlength]


def f_omdbrow(strimdbid, objjson):
    """Columns of T_WC_OMDB_TITLE from one OMDb answer."""
    blnok = str(objjson.get("Response", "")).lower() == "true"
    arrrow = {
        "ID_IMDB": strimdbid,
        "RESPONSE_OK": 1 if blnok else 0,
        "ERROR_TEXT": None if blnok else f_textornone(objjson.get("Error"), 255),
        "TIM_OMDB_FETCHED": datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S"),
        "RAW_JSON": json.dumps(objjson, ensure_ascii=False),
    }
    if not blnok:
        return arrrow
    lngrt = None
    lngmc = None
    for objrating in objjson.get("Ratings") or []:
        strsource = str(objrating.get("Source", ""))
        if strsource == "Rotten Tomatoes":
            lngrt = f_intornone(objrating.get("Value"))
        elif strsource == "Metacritic":
            lngmc = f_intornone(objrating.get("Value"))
    strrating = str(objjson.get("imdbRating") or "")
    arrrow.update({
        "OMDB_TYPE": f_textornone(objjson.get("Type"), 20),
        "TITLE": f_textornone(objjson.get("Title"), 500),
        "YEAR_TEXT": f_textornone(objjson.get("Year"), 20),
        "RT_SCORE": lngrt,
        "METACRITIC_SCORE": lngmc,
        "METASCORE": f_intornone(objjson.get("Metascore")),
        "IMDB_RATING": float(strrating) if re.match(r"^\d+(\.\d+)?$", strrating) else None,
        "IMDB_VOTES": f_moneyornone(objjson.get("imdbVotes")),
        "AWARDS": f_textornone(objjson.get("Awards"), 1000),
        "BOX_OFFICE_USD": f_moneyornone(objjson.get("BoxOffice")),
        "BOX_OFFICE_TEXT": f_textornone(objjson.get("BoxOffice"), 50),
        "RATED": f_textornone(objjson.get("Rated"), 30),
        "PRODUCTION": f_textornone(objjson.get("Production"), 500),
        "TOTAL_SEASONS": f_intornone(objjson.get("totalSeasons")),
    })
    return arrrow


def f_omdbfetch(strimdbid):
    """One OMDb call with retries and backoff. Returns the JSON dict, or None."""
    dbldelay = DBL_REQUEST_DELAY
    for intattempt in range(1, INT_MAX_RETRIES + 1):
        try:
            objresponse = requests.get(STR_API_URL, params={"i": strimdbid, "apikey": STR_API_KEY, "plot": "short"}, timeout=30)
            if objresponse.status_code == 429 or objresponse.status_code >= 500:
                raise requests.HTTPError(f"HTTP {objresponse.status_code}")
            # OMDb answers 401 with a JSON body for a bad key or an exhausted quota
            return objresponse.json()
        except (requests.RequestException, ValueError) as e:
            print(f"⚠️ {strimdbid}: attempt {intattempt}/{INT_MAX_RETRIES} failed: {e}")
            time.sleep(dbldelay)
            dbldelay *= 2
    return None


def f_candidates(cursor, lnglimit):
    """IMDb ids to fetch: never fetched first (most votes), then the oldest refresh."""
    strrefresh = (datetime.now(cp.paris_tz) - timedelta(days=LNG_REFRESH_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    strsql = f"""
SELECT c.ID_IMDB FROM (
  SELECT ID_IMDB, MAX(IMDB_VOTES) AS VOTES FROM (
    SELECT ID_IMDB, IMDB_VOTES FROM T_WC_T2S_MOVIE WHERE ID_IMDB LIKE 'tt%%' AND (DELETED IS NULL OR DELETED = 0)
    UNION ALL
    SELECT ID_IMDB, IMDB_VOTES FROM T_WC_T2S_SERIE WHERE ID_IMDB LIKE 'tt%%' AND (DELETED IS NULL OR DELETED = 0)
  ) u GROUP BY ID_IMDB
) c
LEFT JOIN {STR_TABLE} o ON o.ID_IMDB = c.ID_IMDB
WHERE o.ID_IMDB IS NULL OR o.TIM_OMDB_FETCHED < %s
ORDER BY (o.ID_IMDB IS NULL) DESC, CASE WHEN o.ID_IMDB IS NULL THEN -COALESCE(c.VOTES, 0) ELSE 0 END, o.TIM_OMDB_FETCHED, c.ID_IMDB
LIMIT %s """
    cursor.execute(strsql, (strrefresh, lnglimit))
    return [row["ID_IMDB"] for row in cursor.fetchall()]


def main():
    if not STR_API_KEY:
        print("❌ OMDB_API_KEY is not set in .env: nothing to do.")
        return
    strtoday = datetime.now(cp.paris_tz).strftime("%Y-%m-%d")
    strstart = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")
    cp.f_setservervariable("stromdbcrawlerstartdatetime", strstart, "Date and time of the last start of the OMDb crawler", 0)
    cp.f_setservervariable("stromdbcrawlertotalruntime", "RUNNING", "Total runtime of the OMDb crawler", 0)
    start_time = time.time()

    # daily budget, shared by every run of the same Paris day
    if cp.f_getservervariable("stromdbcrawlerrequestday", 0) != strtoday:
        cp.f_setservervariable("stromdbcrawlerrequestday", strtoday, "Paris day the OMDb request count refers to", 0)
        cp.f_setservervariable("stromdbcrawlerrequestcount", "0", "OMDb requests made on that day", 0)
    lngused = int(cp.f_getservervariable("stromdbcrawlerrequestcount", 0) or 0)
    lngbudget = max(LNG_DAILY_LIMIT - lngused, 0)
    print(f"OMDb budget today: {lngbudget} of {LNG_DAILY_LIMIT} ({lngused} used)")

    connection = cp.f_getconnection()
    cursor = connection.cursor()
    cursor.execute(STR_DDL)
    connection.commit()

    lngok = 0
    lngnotfound = 0
    lngfailed = 0
    strstop = ""
    arrids = f_candidates(cursor, lngbudget) if lngbudget > 0 else []
    print(f"Candidates: {len(arrids)}")
    for intindex, strimdbid in enumerate(arrids, start=1):
        objjson = f_omdbfetch(strimdbid)
        lngused += 1
        cp.f_setservervariable("stromdbcrawlerrequestcount", str(lngused), "OMDb requests made on that day", 0)
        if objjson is None:
            lngfailed += 1
            continue
        strerror = str(objjson.get("Error", ""))
        if str(objjson.get("Response", "")).lower() != "true" and ("limit" in strerror.lower() or "api key" in strerror.lower()):
            strstop = strerror
            print(f"❌ OMDb refused the request ({strerror}): stopping.")
            break
        cp.f_sqlupdatearray(STR_TABLE, f_omdbrow(strimdbid, objjson), f"ID_IMDB = {cp.f_stringtosql(strimdbid)}", 1)
        if str(objjson.get("Response", "")).lower() == "true":
            lngok += 1
        else:
            lngnotfound += 1
        if intindex % 100 == 0:
            print(f"{intindex}/{len(arrids)}: {lngok} ok, {lngnotfound} not found, {lngfailed} failed")
            cp.f_setservervariable("stromdbcrawlercurrentprocess", f"{intindex}/{len(arrids)} ids", "Current position of the OMDb crawler", 0)
        time.sleep(DBL_REQUEST_DELAY)

    strsummary = f"{lngok} ok, {lngnotfound} not found, {lngfailed} failed" + (f", stopped: {strstop}" if strstop else "")
    print(f"=== OMDb run complete: {strsummary} ===")
    cp.f_setservervariable("stromdbcrawlerlastresult", strsummary, "Result of the last OMDb crawler run", 0)
    cp.f_setservervariable("stromdbcrawlertotalruntime", cp.convert_seconds_to_duration(time.time() - start_time), "Total runtime of the OMDb crawler", 0)
    cp.f_setservervariable("stromdbcrawlerenddatetime", datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S"), "Date and time of the last end of the OMDb crawler", 0)


if __name__ == "__main__":
    main()
