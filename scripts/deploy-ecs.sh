#!/usr/bin/env bash
# http://stackoverflow.com/questions/821396/aborting-a-shell-script-if-any-command-returns-a-non-zero-value
set -e
BRANCH=$1

case "$BRANCH" in
'master') cluster=testing ;;
'staging') cluster=staging ;;
'production') cluster=production ;;
*) cluster= ;;
esac

if [ -z "$cluster" ]; then
    echo "Not deploying branch $BRANCH."
    exit 0
else    
  aws ecs update-service --cluster=$cluster --service="tuulboxchat-$cluster-web" --force-new-deployment
  ./scripts/create-migration-task.sh $cluster
#wait for deployments to complete
  echo "Waiting for scrapper $cluster deployments to complete..."
  aws ecs wait services-stable --cluster=$cluster --services "tuulboxchat-$cluster-web"
  echo "scrapper $cluster deployments complete..."
fi