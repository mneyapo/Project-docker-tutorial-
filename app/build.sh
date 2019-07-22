#!/bin/bash

TIME=`date +%Y%m%d_%H%M%S`

docker build $1 $2 $3 $4 -t "tutorialapp_2" .

echo -e "\nHint: Ignore cache with --no-cache"
