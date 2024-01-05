#!/bin/bash

cd /var/lib/list_to_sheets || exit
/bin/docker build -t list_to_sheets .