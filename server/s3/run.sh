#!/bin/bash

export AWS_BUCKET_NAME=${S3_BUCKET_NAME}
export AWS_ACCESS_KEY_ID=${S3_ACCESS_KEY}
export AWS_SECRET_KEY=${S3_PRIVATE_KEY}

exec docker-entrypoint.sh $@

