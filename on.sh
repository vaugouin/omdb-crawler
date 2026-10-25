#!/bin/bash
# Switch omdb-crawler.sh back on: removes the flag file CRON_OFF that off.sh wrote.
cd "$(dirname "$(readlink -f "$0")")" || exit 1
# A launcher renamed by the old off.sh (<name>-off.sh, before 2026-10-25) is put back,
# or dropped when git has already restored the tracked one.
[ -f omdb-crawler-off.sh ] && { [ -f omdb-crawler.sh ] && rm -f omdb-crawler-off.sh || mv omdb-crawler-off.sh omdb-crawler.sh; }
rm -f CRON_OFF && echo "omdb-crawler: on (CRON_OFF removed)"
