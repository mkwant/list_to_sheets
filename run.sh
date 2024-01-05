#!/bin/bash
arguments=( "$@" )

cd /var/lib/list_to_sheets || exit
/bin/docker run --rm -t --env-file .env -v "${PWD}"/client_secrets.json:/app/src/client_secrets.json -v "${PWD}"/mycreds.json:/app/src/mycreds.json list_to_sheets "${arguments[@]}"