from datetime import datetime
from datetime import timedelta
import json
import jwt
import os
import requests
import pandas as pd


class analytics_client:

    def __init__(self, adobe_org_id, subject_account, client_id, client_secret, account_id, private_key_location='.ssh/private.key'):
        self.adobe_auth_host = 'https://ims-na1.adobelogin.com'
        self.adobe_auth_url = os.path.join(
            self.adobe_auth_host, 'ims/exchange/jwt')
        self.adobe_org_id = adobe_org_id
        self.subject_account = subject_account

        self.client_id = client_id
        self.client_secret = client_secret
        self.private_key_location = os.path.join(
            os.path.expanduser('~'), private_key_location)
        self.account_id = account_id

        self.experience_cloud_metascope = 'https://ims-na1.adobelogin.com/s/ent_analytics_bulk_ingest_sdk'

        self.analytics_url = "https://analytics.adobe.io/api/{}/reports".format(
            self.account_id)

        self.report_object = self._generate_empty_report_object()

    def _read_private_key(self):
        # Request Access Key
        # This Needs to point at where your private key is on the file system
        keyfile = open(self.private_key_location, 'r')
        private_key = keyfile.read()
        return private_key

    def _get_jwtPayload(self, expiration=datetime.utcnow()):
        jwtPayloadJson = {}
        jwtPayloadJson['iss'] = self.adobe_org_id
        jwtPayloadJson['sub'] = self.subject_account
        jwtPayloadJson[self.experience_cloud_metascope] = True
        jwtPayloadJson['aud'] = os.path.join(
            self.adobe_auth_host, 'c', self.client_id)
        jwtPayloadJson["exp"] = expiration + timedelta(minutes=30)

        return jwtPayloadJson

    def _renew_access_token(self):

        private_key = self._read_private_key()

        jwtPayloadJson = self._get_jwtPayload()
        # Encode the jwt Token
        jwttoken = jwt.encode(jwtPayloadJson, private_key, algorithm='RS256')

        accessTokenRequestPayload = {
            'client_id': self.client_id, 'client_secret': self.client_secret, 'jwt_token': jwttoken
        }
        result = requests.post(self.adobe_auth_url,
                               data=accessTokenRequestPayload)
        resultjson = json.loads(result.text)

        if (result.status_code != 200):
            raise ValueError('Response code error', result.text)

        return resultjson['access_token']

    def _get_request_headers(self):

        self.access_token = self._renew_access_token()

        analytics_header = {
            "X-Api-Key": self.client_id,
            "x-proxy-global-company-id": self.account_id,
            "Authorization": "Bearer " + self.access_token,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        return analytics_header

    @staticmethod
    def _generate_empty_report_object():
        report = {
            "rsid": "",
            "globalFilters": [
                {
                    "type": "dateRange",
                    "dateRange": ""
                }
            ],
            "metricContainer": {
                "metrics": []
            },
            "dimension": ""
        }
        return report

    @staticmethod
    def _generate_metric_structure():
        metric = {
            "columnId": "",
            "id": ""
        }
        return metric

    @staticmethod
    def _format_date_range(date_start, date_end):
        '''Format date range into an API-compatible.
        2017-12-31T00:00:00.000/2018-01-06T23:59:59.999
        '''
        date_start = datetime.strptime(date_start, '%Y-%m-%d')
        date_start = date_start + timedelta(microseconds=1)
        date_start = date_start.isoformat('T')

        date_end = datetime.strptime(date_end, '%Y-%m-%d')
        date_end = date_end + \
            timedelta(hours=23, minutes=59, seconds=59, milliseconds=999)
        date_end = date_end.isoformat('T')
        final_date = '{}/{}'.format(date_start[:-7], date_end[:-7])
        return final_date

    def set_report_suite(self, report_suite_id):
        self.report_object['rsid'] = report_suite_id

    def _get_page(self):
        '''
        Performs post request to the reporting API.
        Returns a standard response object.
        '''
        analytics_header = self._get_request_headers()
        page = requests.post(
            self.analytics_url,
            headers=analytics_header,
            data=json.dumps(self.report_object),
        )

        if (page.status_code != 200):
            raise ValueError('Response code error', page.text)

        return page

    def get_report(self):
        self.set_page_number(0)
        # Get initial page
        data = self._get_page()
        json_obj = json.loads(data.text)
        total_pages = json_obj['totalPages']
        current_page = 1
        is_last_page = False
        df_data = self.format_output(data)
        while (total_pages > 1 and not is_last_page):
            self.set_page_number(current_page)
            data = self._get_page()
            json_obj = json.loads(data.text)
            is_last_page = json_obj['lastPage']
            current_page = current_page + 1
            df_current_page = self.format_output(data)

            df_data = df_data.append(df_current_page, ignore_index=True)

        return df_data

    def _get_metrics(self):
        '''
            Return Metric names as Data frame. The index is the same as 
            the id used during the add_metric function.
        '''
        # Obtain Metrics Name - start
        index = []
        metricName = []
        for metric in self.report_object['metricContainer']['metrics']:
            index.append(metric['columnId'])
            metricName.append(metric['id'])
        metricNames = pd.DataFrame(index=index, data=metricName)
        # metricNames.columns = ['metrics']
        # Obtain Metrics Name - end
        return metricNames

    def format_output(self, data):
        '''
        Input: Response object from POST request to the reporting API.
        Returns: Pandas Data frame. As metrics' columns names the original metrics from the request are used.
        '''

        metricNames = self._get_metrics()
        # Convert to DF to easily obtain the data column
        df_response_data = pd.DataFrame(data.json()['rows'])
        # Convert metrics to DF into dedicated columns. Column header is the metric ID
        df_metrics_data = pd.DataFrame(
            df_response_data.data.tolist(), index=df_response_data.index)
        # Rename metrics' column headers into the metric name, based on the metric ID
        df_metrics_data.rename(columns=lambda x: metricNames[metricNames.index == '{}'.format(
            x)].iloc[0][0], inplace=True)

        return pd.merge(df_response_data, df_metrics_data, left_index=True, right_index=True).drop(columns=['itemId', 'data'])

    def add_metric(self, metric_name):
        metric = self._generate_metric_structure()
        existing_number_of_metrics = len(
            self.report_object['metricContainer']['metrics'])

        metric['columnId'] = '{}'.format(existing_number_of_metrics)
        metric['id'] = metric_name

        self.report_object['metricContainer']['metrics'].append(metric)

    def set_dimension(self, dimension_name, sort='asc'):
        self.report_object['dimension'] = dimension_name
        self._set_report_setting('dimensionSort', sort)

    def set_date_range(self, date_start, date_end):
        formated_date_range = self._format_date_range(
            date_start=date_start, date_end=date_end)
        self.report_object['globalFilters'][0]['dateRange'] = formated_date_range

    def set_limit(self, rows_limit):
        self._set_report_setting('limit', rows_limit)

    def set_page_number(self, page_no):
        self._set_report_setting('page', page_no)

    def _set_report_setting(self, setting_item, value):
        self.report_object = self._add_key_to_dict(
            self.report_object, 'settings')
        self.report_object['settings'] = self._add_key_to_dict(
            self.report_object['settings'], setting_item)
        self.report_object['settings'][setting_item] = '{}'.format(value)

    @staticmethod
    def _add_key_to_dict(dict_obj, key):
        if (key not in dict_obj):
            dict_obj[key] = {}
        return dict_obj
