#!/usr/bin/env bash
set -e
BRANCH=$1

case "$BRANCH" in
'master') TAG=testing ;;
'staging') TAG=staging ;;
'production') TAG=production ;;
*) TAG=latest ;;
esac

REGION='us-west-1'
AWS_ACCOUNT=459784935938
REPOSITORY=tuulboxchat

aws ecr get-login-password --region $REGION | \
docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com
docker tag $REPOSITORY:latest $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY:$TAG &&
docker push $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY:$TAG