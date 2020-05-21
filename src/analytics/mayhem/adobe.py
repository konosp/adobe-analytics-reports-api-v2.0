from datetime import datetime
from datetime import timedelta
import time
import json
import jwt
import os
import requests
import pandas as pd


class analytics_client:

    def __init__(self, adobe_org_id, subject_account, client_id, client_secret, account_id, private_key_location='.ssh/private.key'):
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

        client_secret : string
            Client Secret

        account_id : string
            Account ID
        
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

        self.experience_cloud_metascope = 'https://ims-na1.adobelogin.com/s/ent_analytics_bulk_ingest_sdk'

        self.analytics_url = "https://analytics.adobe.io/api/{}/reports".format(self.account_id)

        self.report_object = self._generate_empty_report_object()
        self.dimensions = []

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
    def _format_date_range(date_start, date_end):
        '''
        Format start and ending date.

        The starting date and the ending date for the reporting period are formated in an API-compatible format.
        The final value is saved in the JSON report object.
        Note: The end-date provided is inclusive. For that reason it is converted to the start of the next day. 

        Example: If the report needs to end on 1st of March 2020, then the value is convered into 2020-03-02T00:00:00.000
        
        Parameters
        ----------
        date_start : string
            Reporting period start date. Format: YYYY-MM-DD i.e. 2017-12-31. The value is converted to 2017-12-31T00:00:00.000

        date_end : string
            Reporting period start date. Format: YYYY-MM-DD i.e. 2018-01-31. The value is converted to 2018-02-01T00:00:00.000

        Returns
        -------
        string
            The final formated value i.e. 2017-12-31T00:00:00.000/2018-02-01T00:00:00.000        
        '''
        date_start = datetime.strptime(date_start, '%Y-%m-%d')
        date_start = date_start + timedelta(microseconds=1)
        date_start = date_start.isoformat('T')

        date_end = datetime.strptime(date_end, '%Y-%m-%d')
        # date_end = date_end + \
        #     timedelta(hours=23, minutes=59, seconds=59, milliseconds=999)
        date_end = date_end + timedelta(hours=24, minutes=00, seconds=00, milliseconds=999)
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
                data=json.dumps(report_object)
            )

            if (page.status_code == 429):
                print('Response code error: {}'.format(page.text))
                print('Delaying for next request')
                time.sleep(time_delay)
                time_delay = time_delay * 2
            elif (page.status_code != 200):
                raise ValueError('Response code error', page.text)

            status_code = page.status_code
            
        return page

    def get_report(self, custom_report_object = None):
        self._set_page_number(0)
        # Get initial page
        data = self._get_page(custom_report_object)
        json_obj = json.loads(data.text)
        total_pages = json_obj['totalPages']
        current_page = 1
        is_last_page = False
        df_data = self.format_output(data)

        # Download additional data if more than 1 pages are available
        while (total_pages > 1 and not is_last_page):
            self._set_page_number(current_page)
            data = self._get_page(custom_report_object)
            json_obj = json.loads(data.text)
            is_last_page = json_obj['lastPage']
            current_page = current_page + 1
            df_current_page = self.format_output(data)

            df_data = df_data.append(df_current_page, ignore_index=True)

        return df_data

    def get_report_multiple_breakdowns(self):
        
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
                columns = {'itemId' : 'itemId_lvl_{}'.format(level),'value' : 'value_lvl_{}'.format(level)})    
        
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
        
        tmp_report_object = self.report_object
        
        item_ids = df_page.filter(regex='^itemId').sort_values().array
        
        for idx in range(len(dimensions)):
            dimension = dimensions[idx]
            parent_itemId = item_ids[idx]
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
        # Convert to DF to easily obtain the data column
        df_response_data = pd.DataFrame(data.json()['rows'])
        # Convert metrics to DF into dedicated columns. Column header is the metric ID
        if data.json()['totalPages'] > 0:
            metrics_column = df_response_data.data.tolist()
            df_metrics_data = pd.DataFrame(metrics_column, index=df_response_data.index)
        else:
            
            metrics_column = []
            
            idx = data.json()['columns']['columnIds']
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

    def set_date_range(self, date_start, date_end):
        '''
        Set the start and end date.

        The starting date and the ending date for the reporting period is saved into the JSON report object.
        The values are first formated in an API-compatible format using _format_date_range function.
        The final value is saved in the JSON report object.
        
        Parameters
        ----------
        date_start : string
            Reporting period start date. Format: YYYY-MM-DD i.e. 2017-12-31

        date_end : string
            Reporting period start date. Format: YYYY-MM-DD i.e. 2018-01-31.   
        '''

        formated_date_range = self._format_date_range(date_start=date_start, date_end=date_end)
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