# Copyright 2018 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import webapp2
import httplib2
import os
from pprint import pprint
from datetime import datetime
from datetime import timedelta
from googleapiclient import discovery
from google.appengine.api import mail
from google.appengine.api import app_identity
from google.appengine.api import memcache

class CronJob(webapp2.RequestHandler):
    def sendNotification(self, instances, project):
        body = """<html><head><body><table><tr><th>instance</th><th>zone</th><th>operation</th><th>time (UTC)</th><th>duration</th></tr>%%ROWS%%</table>
<br><br>check more information on <a href="https://console.cloud.google.com/compute/operations?project=%%PROJECT%%">https://console.cloud.google.com/compute/operations?project=%%PROJECT%%</a>
"""
        rows = ""
        for instance in instances:
            tmp = ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                instance['instance'],
                instance['zone'], 
                instance['operationType'],
                instance['startTime'],
                instance['duration']))
            rows += tmp
        body = body.replace('%%ROWS%%', rows).replace("%%PROJECT%%", project)
        message = mail.EmailMessage(
            sender='{}@appspot.gserviceaccount.com'.format(app_identity.get_application_id()), 
            subject="Instance Operations Detected")
        message.to = os.environ.get('NOTIFICATION_RECEIVER')
        message.html = body
        message.send()

    def getOperationList(self, project):
        ret = []
        filter = ['compute.instances.migrateOnHostMaintenance', 'compute.instances.hostError']
        http = httplib2.Http()
        service = discovery.build("compute", "v1")
        request = service.globalOperations().aggregatedList(project=project, orderBy='creationTimestamp desc')
        while request is not None:
            response = request.execute()

            if 'items' not in response.keys():
                break

            for zone in response['items']:
                # no operations in this zone
                if 'operations' not in response['items'][zone].keys():
                    continue

                for operation in response['items'][zone]['operations']:
                    if operation['operationType'] not in filter:
                        continue

                    if memcache.get('__OperationId{}'.format(operation['id'])):
                        # found in memcache, duplicated
                        continue

                    instance = operation['targetLink'].split('/')[-1]
                    operationType = operation['operationType']
                    endTime = datetime.strptime(operation['endTime'][:-6][:19], '%Y-%m-%dT%H:%M:%S')
                    startTime = datetime.strptime(operation['startTime'][:-6][:19], '%Y-%m-%dT%H:%M:%S')
                    duration = endTime - startTime

                    ret.append({
                        'instance': instance, 
                        'operationType': operationType.split('.')[-1], 
                        'startTime': str(startTime),
                        'endTime': str(endTime),
                        'zone': zone.split('/')[-1],
                        'duration': str(duration)
                    })
                    memcache.set('__OperationId{}'.format(operation['id']), 1)

                request = service.globalOperations().list_next(previous_request=request, previous_response=response)
        if len(ret) is not 0:
            self.sendNotification(ret, project)
        return len(ret)

    def get(self):
        events = self.getOperationList(os.environ.get('PROJECT_ID') or app_identity.get_application_id())
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('OK, {} events detected'.format(events))

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('OK')

app = webapp2.WSGIApplication([
    ('/cron', CronJob),
    ('/.*', MainPage),
], debug=False)