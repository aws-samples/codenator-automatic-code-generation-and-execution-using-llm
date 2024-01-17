#!/bin/bash

set -x

S3_BUCKET=${1:-"codenator-dev-00"}
S3_PREFIX=${2:-"codenator/CFN"}

echo "Uploading data..."
aws s3 sync data/ s3://$S3_BUCKET/$S3_PREFIX/data/
echo "Uploading templates..."
aws s3 sync CloudFormation/ s3://$S3_BUCKET/$S3_PREFIX/