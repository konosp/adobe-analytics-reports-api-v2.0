from src.analytics.mayhem.adobe import analytics_client
import os

ADOBE_ORG_ID = os.environ['ADOBE_ORG_ID']
SUBJECT_ACCOUNT = os.environ['SUBJECT_ACCOUNT']
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
PRIVATE_KEY_LOCATION = os.environ['PRIVATE_KEY_LOCATION']
ACCOUNT_ID = os.environ['ACCOUNT_ID']
REPORT_SUITE_ID = os.environ['REPORT_SUITE_ID']

aa = analytics_client(
        adobe_org_id = ADOBE_ORG_ID, 
        subject_account = SUBJECT_ACCOUNT, 
        client_id = CLIENT_ID, 
        client_secret = CLIENT_SECRET,
        account_id = ACCOUNT_ID, 
        private_key_location = PRIVATE_KEY_LOCATION
    )

aa.set_report_suite(report_suite_id = REPORT_SUITE_ID)
aa.add_metric(metric_name= 'metrics/visits')
aa.add_metric(metric_name= 'metrics/orders')
aa.add_metric(metric_name= 'metrics/event3')
aa.add_dimension(dimension_name = 'variables/mobiledevicetype')
aa.add_dimension(dimension_name= 'variables/lasttouchchannel')

aa.set_date_range(date_start = '2019-12-01', date_end= '2020-03-31')

data = aa.get_report_multiple_breakdowns()
print(data)
