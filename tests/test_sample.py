from datetime import datetime
from datetime import timedelta
import requests
import requests_mock
import json
import jwt
import os
from src.adobe_api.adobe_api import aa_client

test_adobe_org_id= 'fake_org_id'
test_subject_account = 'fake_subject_account'
test_client_id = 'fake_client_id' 
test_client_secret = 'fake_client_secret'
test_account_id= 'fake_account_id'
test_access_token = 'fake_access_token'
test_report_suite_id = 'fake_rsid'

def _generate_adobe_client():
    client = aa_client(
        adobe_org_id= test_adobe_org_id, 
        subject_account = test_subject_account, 
        client_id = test_client_id ,
        client_secret = test_client_secret,
        account_id= test_account_id)
    return client

def test_client_constructor():

    client = _generate_adobe_client()
    
    assert client.adobe_auth_host == 'https://ims-na1.adobelogin.com'
    assert client.adobe_auth_url == os.path.join(client.adobe_auth_host, 'ims/exchange/jwt')
    assert client.adobe_org_id == test_adobe_org_id
    assert client.subject_account == test_subject_account

    assert client.client_id == test_client_id
    assert client.client_secret == test_client_secret
    assert client.private_key_location == '/Users/konos/.ssh/private.key'
    assert client.account_id == test_account_id

    assert client.experience_cloud_metascope == 'https://ims-na1.adobelogin.com/s/ent_analytics_bulk_ingest_sdk'

    assert client.analytics_url == "https://analytics.adobe.io/api/{}/reports".format(test_account_id)

def test_empty_report_object():
    expected_report_object = {
            "rsid": "vodafonegroupukprod",
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
    actual_report_object = aa_client._generate_empty_report_object()
    assert actual_report_object == expected_report_object

def test_jwtPayload():
    client = _generate_adobe_client()

    jwt_expiration = datetime(2020, 4, 8, 20, 30, 30, 107868)

    expected_jwt = {
        'iss': test_adobe_org_id, 
        'sub': test_subject_account, 
        'https://ims-na1.adobelogin.com/s/ent_analytics_bulk_ingest_sdk': True, 
        'aud': 'https://ims-na1.adobelogin.com/c/{}'.format(test_client_id), 
        'exp': jwt_expiration + timedelta(minutes = 30)
        }

    assert client._get_jwtPayload(jwt_expiration) == expected_jwt

def test_renew_access_token(mocker):
    ACCESS_TOKEN_VALUE = 'test token value'
    # adapter = requests_mock.Adapter()
    # mock reading private key
    client = _generate_adobe_client()

    client._read_private_key = mocker.Mock(return_value = 'test_key')
    jwt.encode = mocker.Mock(return_value = 'jwt_encoded')
    assert client._read_private_key() == 'test_key'

    test_response_text = json.dumps({"token_type":"bearer","access_token":ACCESS_TOKEN_VALUE,"expires_in":86399995})
    
    # Generate fake response
    adapter = requests_mock.Adapter()
    adapter.register_uri('GET', 'mock://test.com/path', text=test_response_text)
    session = requests.Session()
    session.mount('mock', adapter)
    test_response = session.get('mock://test.com/path')
    
    # Patch request and fake response
    mocker.patch("requests.post", return_value = test_response)
    
    assert ACCESS_TOKEN_VALUE == client._renew_access_token()

def test_failed_access_token(mocker):
    error_message = {'error_description': 'JWT token is incorrectly formatted, and can not be decoded.',
                    'error': 'invalid_token'}
    # TODO: write test case
    assert 1 == 2

def test_incorrect_api_response(mocker):

    assert 1 == 2

def test_get_request_headers(mocker):
    
    client = _generate_adobe_client()
    client._renew_access_token = mocker.Mock(return_value = test_access_token)

    expected_analytics_header = {           
            "X-Api-Key": test_client_id,
            "x-proxy-global-company-id": test_account_id,
            "Authorization" : "Bearer " + test_access_token,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    assert client._get_request_headers() == expected_analytics_header

def test_format_date_range():
    client = _generate_adobe_client()
    
    #Case 1: different dates
    start_date ='2017-01-31'
    end_date = '2020-12-31'
    expected_date_format = '2017-01-31T00:00:00/2020-12-31T23:59:59'

    assert expected_date_format == client._format_date_range(date_start = start_date, date_end = end_date)
    
    client.set_date_range(start_date, end_date)
    assert client.report_object['globalFilters'][0]['dateRange'] == expected_date_format

    #Case 2: Same dates
    start_date = '2017-01-31'
    end_date = '2020-01-31'
    expected_date_format = '2017-01-31T00:00:00/2020-01-31T23:59:59'

    assert expected_date_format == client._format_date_range(date_start = start_date, date_end = end_date)

    client.set_date_range(start_date, end_date)
    assert client.report_object['globalFilters'][0]['dateRange'] == expected_date_format

def test_set_report_suite():
    client = _generate_adobe_client()

    client.set_report_suite(test_report_suite_id)

    assert client.report_object['rsid'] == test_report_suite_id

def test_metric_add():
    client = _generate_adobe_client()

    test_metric_name = "metrics/pageviews"
    expected_metric = {
            "columnId":"0",
            "id": test_metric_name
        }
    client.add_metric(test_metric_name)

    assert expected_metric == client.report_object['metricContainer']['metrics'][0]

    test_metric_name = "metrics/visits"
    expected_metric = {
            "columnId":"1",
            "id": test_metric_name
        }
    client.add_metric(test_metric_name)
    assert expected_metric == client.report_object['metricContainer']['metrics'][1]

def test_dimension_set():
    client = _generate_adobe_client()
    test_dimension_name = 'variables/daterangeday'

    client.set_dimension(test_dimension_name)

    assert test_dimension_name == client.report_object['dimension']

def test_get_page():
    
    assert False

def test_get_report():

    assert False

def test_get_metrics():

    assert False

def test_format_output():

    assert False