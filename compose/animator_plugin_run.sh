set -e
set -x

freva plugin animator project=observations variable=pr output_unit=mm/h vmin=0 vmax=5 cmap=Blues suffix=gif; echo 0
JOB_ID=$(freva history --limit 1 | grep animator |  sed "s/ .*//;s/)//g")
cp /tmp/eval_conf/work/$USER/freva-ces/output/animator/${JOB_ID}/*.gif docs/source/_static/animator_output.gif
