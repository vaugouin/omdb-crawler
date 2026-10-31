# AGENTS.md - Agent Guide for OMDb Crawler

Single canonical guide for autonomous coding agents in this repository; @CLAUDE.md only points here. What is stored, order of work, budget, configuration and deployment: @README.md (canonical, not duplicated here). Keep `README.md` aligned with every behavior, configuration or deployment change; update this file only when agent workflow or safety context changes.

Reference DDL: @doc/sql/T_WC_OMDB_TITLE.sql, the only table this crawler writes; **keep it in step with `STR_DDL` in `omdb-crawler.py`**.

---

## Related repositories (project ecosystem)

One stage of **Agent BBB** (owner `vaugouin`, siblings under `%USERPROFILE%/Code/<repo>`), converging on a shared MariaDB (`T_WC_*`) and ChromaDB. Canonical roster: `%USERPROFILE%/Nestor/projets/t2s-backlog/topics/related-repositories.txt`.

**This repository's role:** Acquisition. One OMDb request per IMDb id of `T_WC_T2S_MOVIE` / `T_WC_T2S_SERIE`, upserted into `T_WC_OMDB_TITLE`. Split from `imdb-crawler` on 2026-10-21 (IMDb TSV bulk import: different source, mode and licence). Reader: `tmdb-front` (`f_omdbdisplay`, TMDB-FRONT-108).

---

## Code conventions

- Hungarian notation (legacy): `str`, `lng`, `dbl`, `arr`, `int`, `bln`, `obj` prefixes; functions `f_`; constants uppercase with a type prefix (`STR_TABLE`, `LNG_DAILY_LIMIT`).
- Database access goes through `citizenphil.py` (copied from the sibling crawlers): `f_getconnection`, `f_sqlupdatearray` (upsert by condition, adds the audit columns), `f_getservervariable` / `f_setservervariable`.
- Tables of this source use `T_WC_OMDB_*`: the prefix names the source of the data, not the key (rows are keyed by IMDb id). Uppercase snake case, `TIM_*` / `DAT_*`, house audit columns (`DELETED`, `ID_CREATOR`, `DAT_CREAT`, `ID_OWNER`, `TIM_UPDATED`, `ID_USER_UPDATED`).

## Safety

- The API key lives in `.env` only (never in the image, never committed).
- Never raise `OMDB_DAILY_LIMIT` above the key's allowance (free key: 1,000 a day).
- OMDb content is CC BY-NC 4.0: no commercial use of the stored data.

---

**Last Updated**: 2026-10-31
**Current Version**: 1.0.5

## Backlog (Nestor second-brain)

Backlog: `C:\Users\vaugo\Nestor\projets\t2s-backlog\repos\omdb-crawler.md` (tasks `OMDB-CRAWLER-NNN`); dashboard `C:\Users\vaugo\Nestor\projets\t2s-backlog\index.md`. Local paths on Philippe's PC, absent on the VPS and on cloud agents.
