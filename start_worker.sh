#!/bin/sh
export REDIS_URL=redis://$OPAC_RQ_REDIS_HOST:$OPAC_RQ_REDIS_PORT/0
export WORKER_NAME=$HOSTNAME-$(cat /proc/sys/kernel/random/uuid)
export WORKER_PATH="/app/opac/"
QUEUES="${OPAC_RQ_WORKER_QUEUES:-mailing}"

rq worker \
    --url=$REDIS_URL \
    --sentry-dsn=$OPAC_SENTRY_DSN \
    --path=$WORKER_PATH \
    --name=$WORKER_NAME \
    $QUEUES
