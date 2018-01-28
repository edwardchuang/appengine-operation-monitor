# appengine-operation-monitor
A cron on GAE to monitor and notify any compute.instances.migrateOnHostMaintenance and/or compute.instances.hostError operation events

# pre-requirement(s)

% mkdir vendor ; pip install -t vendor/ -r requirements.txt

# configurations

* setup your project_id and notification emails in app.yaml
* adjust monitor interval in cron.yaml
* add email sender address "PROJECT_ID@appspot.gserviceaccount.com" in https://console.cloud.google.com/appengine/settings/emailsenders

# deploy

% gcloud app deploy
% gcloud app deploy cron.yaml

# local test

% dev_appserver.py app.yaml --enable_sendmail
