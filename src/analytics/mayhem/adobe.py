from datetime import datetime
from datetime import timedelta
import time
import json
import jwt
import os
import requests
import pandas as pd

import webbrowser
from urllib.parse import urlparse
from urllib.parse import parse_qs
from urllib.parse import urlencode

class analytics_client:

    def __init__(self, adobe_org_id = None, subject_account = None, client_id = None, auth_client_id = None, client_secret = None, account_id = None, private_key_location='.ssh/private.key', debugging = False):
        '''
        Adobe Analytics Reports API client.

        An Adobe Analytics client is created that initiates the authentication process,
        handles the JWT token that is needed to perform the requests and
        constracts the request JSON object. The JSON object is send as an argument to the reporting API.
        
        Parameters
        ----------
        adobe_org_id : string
            Adobe Organisation ID

        subject_account : string
            Technical account ID

        client_id : string
            Client ID

        auth_client_id : string
            OAuth2 Client ID

        client_secret : string
            Client Secret

        account_id : string
            Account ID (Global Company ID)
        
        private_key_location : string - default: '.ssh/private.key'
            Private Key location

        Returns
        -------
        Instance of analytics_client
        '''


        self.adobe_auth_host = 'https://ims-na1.adobelogin.com'
        self.adobe_auth_url = '/'.join([self.adobe_auth_host, 'ims/exchange/jwt'])
        self.adobe_org_id = adobe_org_id
        self.subject_account = subject_account

        self.client_id = client_id
        self.client_secret = client_secret
        self.private_key_location = os.path.join(os.path.expanduser('~'), private_key_location)
        self.account_id = account_id

        self.auth_client_id = auth_client_id
        self.redirect_uri = 'https://www.adobe.com'
        self.adobe_auth_login_url = '{}/ims/token/v1'.format(self.adobe_auth_host)

        self.experience_cloud_metascope = 'https://ims-na1.adobelogin.com/s/ent_analytics_bulk_ingest_sdk'

        self.analytics_url = "https://analytics.adobe.io/api/{}/reports".format(self.account_id)

        self.report_object = self._generate_empty_report_object()
        self.dimensions = []
        self.debugging = debugging

    def _read_private_key(self):
        # Request Access Key
        # This Needs to point at where your private key is on the file system
        keyfile = open(self.private_key_location, 'r')
        private_key = keyfile.read()
        return private_key

    def _get_jwtPayload(self, expiration = None ):

        if expiration is None:
            expiration = datetime.utcnow()

        jwtPayloadJson = {}
        jwtPayloadJson['iss'] = self.adobe_org_id
        jwtPayloadJson['sub'] = self.subject_account
        jwtPayloadJson[self.experience_cloud_metascope] = True
        jwtPayloadJson['aud'] = '/'.join([self.adobe_auth_host, 'c', self.client_id])
        jwtPayloadJson["exp"] = expiration + timedelta(minutes=30)

        return jwtPayloadJson

    def _renew_access_token(self):

        private_key = self._read_private_key()

        jwtPayloadJson = self._get_jwtPayload()
        # Encode the jwt Token
        jwttoken = jwt.encode(jwtPayloadJson, private_key, algorithm='RS256')

        accessTokenRequestPayload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret, 
            'jwt_token': jwttoken
        }
        result = requests.post(self.adobe_auth_url,
                               data=accessTokenRequestPayload)
        resultjson = json.loads(result.text)

        if (result.status_code != 200):
            raise ValueError('Response code error', result.status_code)

        return resultjson['access_token']

    def _request_oauth_authorisation_code(self):
        url = '{}/ims/authorize?client_id={}&redirect_uri={}&scope=openid,AdobeID,read_organizations,additional_info.job_function,additional_info.projectedProductContext&response_type=code'.format(self.adobe_auth_host, self.auth_client_id, self.redirect_uri)
        webbrowser.open(url)

    def _obtain_oauth_code(self):
        self._request_oauth_authorisation_code()
        input_text = 'Paste the Adobe login URL that includes the Auth Code (starting with "eyJ...")'
        print(input_text)
        url_text = input()
        
        url_object = urlparse(url_text)
        auth_code = parse_qs(url_object.query)['code'][0]
        return auth_code

    def _obtain_oauth_access_token(self):
        payload_data = {
            'grant_type' : 'authorization_code',
            'client_id' : self.auth_client_id,
            'client_secret' : self.client_secret,
            'code' : self._obtain_oauth_code()
        }
        res = requests.request("POST", url = self.adobe_auth_login_url , data = payload_data)
        
        if (res.status_code != 200):
            raise ValueError('Response code error', res.status_code)

        return res.json()['access_token']

    def _get_request_headers(self):

        if (self.auth_client_id and not self.access_token):
            self.access_token = self._obtain_oauth_access_token()
        elif self.client_id:
            self.access_token = self._renew_access_token()

        analytics_header = {
            "X-Api-Key": (self.client_id or self.auth_client_id),
            "x-proxy-global-company-id": self.account_id,
            "Authorization": "Bearer " + self.access_token,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        return analytics_header

    def _authenticate(self):
        self.access_token = self._obtain_oauth_access_token()

    @staticmethod
    def _generate_empty_report_object():
        report = {
            "rsid": "",
            "globalFilters": [],
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
    def _format_date_range(date_start, date_end, hour_start, hour_end):
        '''
        Format start and ending date.

        The starting date and the ending date for the reporting period are formated in an API-compatible format.
        The final value is saved in the JSON report object.
        Note: The end-date provided is inclusive. For that reason it is converted to the start of the next day. 

        Example: If the report needs to end on 1st of March 2020, then the value is convered into 2020-03-02T00:00:00.000

        The hours are being added on top of the existing day. Examples:
        - If the starting date is 26/11/2020 and starting hour is 13, then the starting time point will be 2020-11-26T13:00:00.000 
        - (!) If the ending date is 29/11/2020 and ending hour is 17, then the ending time point will be 2020-11-29T17:00:00.000 
        - (!) If the ending date is 29/11/2020 and ending hour is 0, then the ending time point will be 2020-11-30T00:00:00.000 

        Note: If the ending hour is <> 0, then the full day is captured. Otherwise it captures only the portion of the day.

        Parameters
        ----------
        date_start : string
            Reporting period start date. Format: YYYY-MM-DD i.e. 2017-12-31. The value is converted to 2017-12-31T00:00:00.000

        date_end : string
            Reporting period start date. Format: YYYY-MM-DD i.e. 2018-01-31. The value is converted to 2018-02-01T00:00:00.000

        hour_start: int
            Reporting period start hour. Integer value from 0 to 24

        hour_end: int
            Reporting period start hour. Integer value from 0 to 24

        Returns
        -------
        string
            The final formated value i.e. 2017-12-31T00:00:00.000/2018-02-01T00:00:00.000        
        '''
        date_start = datetime.strptime(date_start, '%Y-%m-%d')
        date_start = date_start + timedelta(hours = hour_start, microseconds=1)
        date_start = date_start.isoformat('T')

        date_end = datetime.strptime(date_end, '%Y-%m-%d')
        
        if hour_end == 0:
            hour_end = 24
        date_end = date_end + timedelta(hours = hour_end, minutes=00, seconds=00, milliseconds=999)
        date_end = date_end.isoformat('T')
        final_date = '{}/{}'.format(date_start[:-7], date_end[:-7])
        return final_date

    def set_report_suite(self, report_suite_id):
        '''
        Set Adobe Analytics report suite.

        The report suite from which the data needs to be downloaded from.

        Parameters
        ----------
        report_suite_id : object - optional
            Report suite ID.
        '''

        self.report_object['rsid'] = report_suite_id

    def _get_page(self, report_object = None):
        '''
        Perform report request.

        A post request to the API endpoint is performed based on the report object. Either the main report object
        is used or a customised object can be passed as an argument.

        Parameters
        ----------
        report_object : object - optional
            Report object as specified in https://github.com/AdobeDocs/analytics-2.0-apis/blob/master/reporting-guide.md

        Returns
        -------
        response object
            Response object as returned from the post request performed.
        '''
        if report_object is None:
            report_object = self.report_object

        analytics_header = self._get_request_headers()
        
        status_code = None
        time_delay = 1
        while status_code != 200:
            
            page = requests.post(
                self.analytics_url,
                headers=analytics_header,
                data=json.dumps(report_object),
                timeout = 360
            )
            if (self.debugging):
                self.write_log('request_object', json.dumps(report_object))
                self.write_log('response', page.text)
                
            if (page.status_code == 429):
                # Response code 429
                # {"error_code":"429050","message":"Too many requests"}
                print('Response code error: {}'.format(page.status_code))
                
            elif (page.status_code != 200):
                page.raise_for_status()
                # raise ValueError('Response code error', page.status_code)

            status_code = page.status_code  
            time.sleep(time_delay)
            time_delay = time_delay * 2

        return page

    def get_report(self, custom_report_object = None):
        self._set_page_number(0)
        # Get initial page
        data = self._get_page(custom_report_object)
        self.logger(data.text)
        json_obj = json.loads(data.text)
        total_pages = json_obj['totalPages']
        current_page = 1
        is_last_page = False
        df_data = self.format_output(data)

        # Download additional data if more than 1 pages are available
        while (total_pages > 1 and not is_last_page):

            if (custom_report_object is not None):
                # Workaround - This is done because in multiple breakdowns, pagination does not work in sub-breakdowns.
                custom_report_object['settings']['page'] = '{}'.format(current_page)

            self.logger('Parsing page {}'.format(current_page)) 
            self._set_page_number(current_page)
            data = self._get_page(custom_report_object)
            self.logger(data.text)
            json_obj = json.loads(data.text)
            is_last_page = json_obj['lastPage']
            current_page = current_page + 1
            df_current_page = self.format_output(data)

            df_data = df_data.append(df_current_page, ignore_index=True)

        return df_data

    def get_report_multiple_breakdowns(self):
        '''
        Download report that contains multiple dimensions.

        Initial report (top-level dimension) is downloaded using get_report() method. Subsequent dimensions
        are downloaded using get_report_breakdown(). This is because sub-breakdowns rely on itemId.

        Per remaining (non-top) dimensions, get_report_breakdown() is invoked.

        Returns
        -------
        Pandas data frame object
            Data frame with columns:
            - itemId_lvl_*      : ID of the value per breakdown level
            - value_lvl_*       : The row value for the particular breakdown combination
            - metrics/{metric}  : Metric name is added in the API request i.e. metrics/visits
        '''
        
        current_dimensions = []
        # Download 1st level data
        df_page = self.get_report()
        level = 1

        dim_index = 1
        remaining_dimensions = list(self.dimensions)
        remaining_dimensions.pop(0)

        # Re-format column names
        if (len(remaining_dimensions) > 0):
            df_page = df_page.filter(regex='^itemId|^value', axis = 'columns')
        
        df_page = df_page.rename(
                columns = {
                    'itemId' : 'itemId_lvl_{}'.format(level),
                    'value' : 'value_lvl_{}'.format(level)}
                )    
        
        for breakdown in remaining_dimensions:
            level = level + 1
            dim_index = dim_index + 1
            current_dimensions.append(breakdown)
            
            results_broken_down = df_page.apply(self.get_report_breakdown, axis = 1 , dimensions = current_dimensions, current_level = level)
            dl = []
            for i in results_broken_down:
                dl.append(i)
            
            results_broken_down = pd.concat(dl, ignore_index=True)

            df_page = df_page.filter(regex='^itemId|^value', axis = 'columns')
            df_page = pd.merge(df_page, results_broken_down, how = 'right')
            
        return df_page

    def get_report_breakdown(self, df_page, dimensions, current_level = None):
        '''
        Download broken-down dimensions of a single report.

        For the existing dimensions in a data frame, iterate through all entries, generate a new report JSON object and
        download the new row values and metrics. 
        
        This function is invoked multiple times based on the number of dimensions. 
        Invoked once per dimension level. i.e. if 3 dimensions are added in the initalisation, it will be invoked twice; 
        once for the 2nd level and once for the 3rd level dimension. 

        Parameters
        ----------
        df_page : Pandas data frame
            Contains a previously downloaded report

        dimensions : array
            Array of dimensions that have already been requested before and data has been downloaded. This assists in constructing the new 
            JSON request object and apply the correct global filters

        current_level : str - optional
            The depth in the dimension tree. Populated only from level 2 and upwards

        Returns
        -------
        response object
            Response object as returned from the post request performed.
        '''

        self.logger('Downloading additional breakdown')
        self.logger(dimensions)
        
        tmp_report_object = self.report_object
        
        item_ids = df_page.filter(regex='^itemId').sort_values().array
        
        for idx in range(len(dimensions)):
            dimension = dimensions[idx]
            parent_itemId = item_ids[idx]
            self.logger('Dimension {}, Item ID: {}'.format(dimension,parent_itemId))
            tmp_report_object = self._add_breakdown_report_object(tmp_report_object, dimension, parent_itemId)

        results = self.get_report(custom_report_object=tmp_report_object)
        # The itemId in the results is set to minus 1 to match with the parent ID during the merge
        for key in df_page.keys():
            if ('_lvl_' in key):
                results[key] = df_page[key]
        results = results.rename(columns = {
                'itemId' : 'itemId_lvl_{}'.format(current_level),
                'value' : 'value_lvl_{}'.format(current_level)
        })
        return results

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
        Format the API repsonse.

        The post request returns a response object. The object is converted into a Pandas data frame.
        As metric names, the original values that were provided by the user are used.
        
        Parameters
        ----------
        data : response object
            Response object as returned from the post request performed.

        Returns
        -------
        Pandas data frame
            A data frame that contains returned data including the itemId.
        '''

        metricNames = self._get_metrics()
        data_json = data.json()
        # Convert to DF to easily obtain the data column
        df_response_data = pd.DataFrame(data_json['rows'])
        # Convert metrics to DF into dedicated columns. Column header is the metric ID
        if (data_json['totalPages'] > 0) and (df_response_data.shape != (0,0)):
            metrics_column = df_response_data.data.tolist()
            df_metrics_data = pd.DataFrame(metrics_column, index=df_response_data.index)
        else:
            
            metrics_column = []
            
            idx = data_json['columns']['columnIds']
            for i in idx:
                metrics_column.append(0)
            df_response_data = pd.DataFrame({'itemId': '0', 'value': 'Unspecified', 'data': metrics_column })
            
            metrics_column = [metrics_column]
            df_metrics_data = pd.DataFrame(metrics_column)
            
        # Rename metrics' column headers into the metric name, based on the metric ID
        df_metrics_data.rename(columns=lambda x: metricNames[metricNames.index == '{}'.format(x)].iloc[0][0], inplace=True)

        return pd.merge(df_response_data, df_metrics_data, left_index=True, right_index=True).drop(columns=['data'])

    def add_metric(self, metric_name):
        metric = self._generate_metric_structure()
        existing_number_of_metrics = len(self.report_object['metricContainer']['metrics'])

        metric['columnId'] = '{}'.format(existing_number_of_metrics)
        metric['id'] = metric_name

        self.report_object['metricContainer']['metrics'].append(metric)

    def add_dimension(self, dimension_name):
        '''
        Add a new dimension.

        Add an extra dimension that will be used in the final results.
        The order dimensions are added affect how results are reported.
        
        Parameters
        ----------
        dimension_name : string
            Dimension name as expected by the Adobe API.

        '''
        self.dimensions.append(dimension_name)
        if (len(self.report_object['dimension']) == 0):
            self.set_dimension(dimension_name)

    def set_dimension(self, dimension_name, sort='asc'):
        '''
        Configure main dimension.

        Configure the reporting dimension. Used for single dimension reports.
        This will be the top-level break down of the metrics.
        The value is added in the JSON report object used in the post request.
        
        Parameters
        ----------
        dimension_name : string
            Dimension name as expected by the Adobe API.

        '''
        self.report_object['dimension'] = dimension_name
        self._set_report_setting('dimensionSort', sort)

    def add_global_segment(self, segment_id = None):
        '''
        Add a global segment into the report request

        A global segment is equivalent of adding a segment in the root of the panel in Adobe Workspace.
        
        Parameters
        ----------

        segment_id : string
            Unique segment ID
        '''
        
        if segment_id is not None:
            segment_filter = {}
            segment_filter['type'] = 'segment'
            segment_filter['segmentId'] = segment_id
            self.report_object['globalFilters'].append(segment_filter)

    def set_date_range(self, date_start, date_end, hour_start = 00, hour_end = 24):
        '''
        Set the start and end date. Optional start/end hour.

        The starting date and the ending date for the reporting period is saved into the JSON report object.
        The values are first formated in an API-compatible format using _format_date_range function.
        The final value is saved in the JSON report object.

        Optionally the start hour of the start date and the end hour of the end date can be configured.
        - If the hour_start parameter is set greater than 0, then the date range will start from that time slot onwards.
        - If the hour_end parameter is not set, then only then the full day will be downloaded.
        - If the hour_end parameter is set greater than 0, then only the portion of the last day will be downloaded.
        
        Parameters
        ----------
        date_start : string
            Reporting period start date. Format: YYYY-MM-DD i.e. 2017-12-31

        date_end : string
            Reporting period start date. Format: YYYY-MM-DD i.e. 2018-01-31.  

        hour_start: int - optional
            Reporting period start hour. Integer value from 0 to 24

        hour_end: int - optional
            Reporting period start hour. Integer value from 0 to 24 
        '''

        formated_date_range = self._format_date_range(date_start=date_start, date_end=date_end, hour_start = hour_start, hour_end= hour_end)
        date_range_globabl_filter =  {
            "type": "dateRange",
            "dateRange": formated_date_range
        }
        self.report_object['globalFilters'].append(date_range_globabl_filter)
        # self.report_object['globalFilters'][0]['dateRange'] = formated_date_range

    def set_limit(self, rows_limit):
        self._set_report_setting('limit', rows_limit)

    def _set_page_number(self, page_no):
        self._set_report_setting('page', page_no)

    def _set_report_setting(self, setting_item, value):
        self.report_object = self._add_key_to_dict(
            self.report_object, 'settings')
        self.report_object['settings'] = self._add_key_to_dict(
            self.report_object['settings'], setting_item)
        self.report_object['settings'][setting_item] = '{}'.format(value)

    def clean_report_object(self):
        self.report_object = self._generate_empty_report_object()

    @staticmethod
    def _add_key_to_dict(dict_obj, key):
        if (key not in dict_obj):
            dict_obj[key] = {}
        return dict_obj

    @staticmethod
    def _add_breakdown_report_object(report_object, breakdown, item_id):
        '''
        When multiple breakdowns are added in a report, the JSON report object needs to be updated in each POST request.
        Everytime the metricFilters and the main dimension are updated dynamically based on the itemId's
        '''
        report_object = json.loads(json.dumps(report_object))
        original_breakdown = report_object['dimension']
        if ('metricFilters' in report_object['metricContainer']):
            metrics_filter_num = len(report_object['metricContainer']['metricFilters'])
        else:
            metrics_filter_num = 0
            report_object['metricContainer']['metricFilters'] = []
        
        for metric in report_object['metricContainer']['metrics']:
            metric_filter = {}
            metric_filter['id'] = '{}'.format(metrics_filter_num)
            metric_filter['type'] = 'breakdown'
            metric_filter['dimension'] = original_breakdown
            metric_filter['itemId'] = '{}'.format(item_id)
            metrics_filter_num = metrics_filter_num + 1
            
            report_object['metricContainer']['metricFilters'].append(metric_filter)
            
            if 'filters' not in metric:
                metric['filters'] = []
            
            metric['filters'].append(metric_filter['id'])
        
        report_object['dimension'] = breakdown
        return report_object

    def logger(self, message):
        if (self.debugging):
            print('Analytics Debugger Start')
            print(message)
            print('Analytics Debugger End')

    def write_log(self, filename, message):
        
        if (not os.path.exists('logs')):
            os.mkdir('logs')

        fil = open("logs/{}-{}.json".format(filename,datetime.now().isoformat()), "a")  # append mode 
        fil.write(message) 
        fil.close() 