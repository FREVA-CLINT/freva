#!/bin/bash
VARIABLE=$1
SEPERATOR="="
CONF=evaluation_system.conf

if [[ -z $VARIABLE ]]; then
    echo "USAGE ./getvar_conf.sh <VARIABLE>"
    echo "<VARIBALE> should be variable"
    echo "in the evaluation_system.conf"
    echo "with seperator '='"
else
    IFS="$SEPERATOR" read -r RAW_VAR OUTPUT <<< "$(cat $CONF | grep ${VARIABLE})"
    echo $OUTPUT
fi