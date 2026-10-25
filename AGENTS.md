# AGENTS.md - Agent Guide for OMDb Crawler

This file gives you the agentic context you need to work on this codebase safely. For overview, configuration and deployment, read @README.md, which is canonical and not duplicated here.

This is the single canonical guide for autonomous coding agents in this repository. Assistant-specific files such as @CLAUDE.md should only point here.

Deeper specs live in their own files:
- @doc/sql/T_WC_OMDB_TITLE.sql: reference DDL of the only table this crawler writes; keep it in step with `STR_DDL` in `omdb-crawler.py`.
- @doc/sql/T_WC_SERVER_VARIABLE.sql: the server variables table used for the daily budget and run telemetry.

For any project update, keep `README.md` aligned (behavior, configuration, deployment); update this file only when agent workflow or safety context changes.

---

## Related repositories (project ecosystem)

`omdb-crawler` is one stage of **Agent BBB**, a multi-repository movie/TV database system owned by GitHub user `vaugouin`. Sibling repos live under `%USERPROFILE%/Code/<repo>` and at `github.com/vaugouin/<repo>`; they converge on a shared MariaDB database (`T_WC_*` tables) and a ChromaDB vector store. The canonical roster is `%USERPROFILE%/Nestor/projets/t2s-backlog/topics/related-repositories.txt`.

**This repository's role:** Acquisition stage. Calls the OMDb API, one request per IMDb id, for the movies and series of `T_WC_T2S_MOVIE` and `T_WC_T2S_SERIE`, and upserts one row per id into `T_WC_OMDB_TITLE` (Rotten Tomatoes and Metacritic scores, Metascore, awards text, US box office, raw JSON). It was split from `imdb-crawler` on 2026-10-21 before its first commit: that repo bulk-imports the IMDb TSV datasets into `T_WC_IMDB_*`, a different source, mode and licence. Readers: `tmdb-front` (`f_omdbdisplay` on the movie and series pages, TMDB-FRONT-108).

---

## Code conventions

- Hungarian notation (legacy style of the stack): `str`, `lng`, `dbl`, `arr`, `int`, `bln`, `obj` prefixes.
- Public helpers use `f_`; constants are uppercase with a type prefix (`STR_TABLE`, `LNG_DAILY_LIMIT`).
- Database access goes through `citizenphil.py` (copied from the sibling crawlers): `f_getconnection`, `f_sqlupdatearray` (upsert by condition, adds the audit columns), `f_getservervariable` / `f_setservervariable`.

## SQL naming

- Tables of this source use `T_WC_OMDB_*` (the prefix names the source of the data, not the key: the rows are keyed by IMDb id but their content comes from OMDb).
- Uppercase snake case columns, `TIM_*` for datetimes, `DAT_*` for dates, house audit columns (`DELETED`, `ID_CREATOR`, `DAT_CREAT`, `ID_OWNER`, `TIM_UPDATED`, `ID_USER_UPDATED`).

## Safety

- The API key lives in `.env` only (never in the image, never committed).
- Respect the daily quota: never raise `OMDB_DAILY_LIMIT` above the key's allowance; the free key allows 1,000 requests a day.
- OMDb content is CC BY-NC 4.0: no commercial use of the stored data.

## Build & deployment (Docker)

`Dockerfile` (base `python:3.10.5-slim-buster`) installs `requirements.txt`, copies the repo and runs `python -u ./omdb-crawler.py`. `omdb-crawler.sh` builds the image `omdb-crawler-python-app` and runs the container `omdb-crawler` with `--network=host` and `--env-file ~/docker/omdb-crawler/.env`. No ports, no volumes.

---

**Last Updated**: 2026-10-25
**Current Version**: 1.0.4

## Backlog (Nestor second-brain)

The backlog for this repo lives in the **Nestor** knowledge repo:

- This repo: `C:\Users\vaugo\Nestor\projets\t2s-backlog\repos\omdb-crawler.md`
- Cross-repo dashboard: `C:\Users\vaugo\Nestor\projets\t2s-backlog\index.md`

Tasks are `OMDB-CRAWLER-NNN`. These are local paths on Philippe's PC and do not resolve on the VPS or on cloud agents.
