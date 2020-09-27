from analytics.mayhem.adobe import analytics_client
import os

REPORT_SUITE_ID = os.getenv('aa_report_suite_id')
CLIENT_ID = os.getenv('aa_client_id')
CLIENT_SECRET = os.getenv('aa_client_secret')
GLOBAL_COMPANY_ID = os.getenv('aa_global_company_id')
ADOBE_ORG_ID = os.getenv('aa_adobe_org_id')
SUBJECT_ACCOUNT = os.getenv('aa_subject_account')
PRIV_KEY_LOCATION = '.ssh/adobe-auth/private.key'

aa = analytics_client(
    adobe_org_id = ADOBE_ORG_ID,
    subject_account = SUBJECT_ACCOUNT,
    client_id = CLIENT_ID,
    client_secret = CLIENT_SECRET,
    account_id = GLOBAL_COMPANY_ID,
    private_key_location = PRIV_KEY_LOCATION
)

aa.set_report_suite(report_suite_id = REPORT_SUITE_ID )
aa.add_metric(metric_name = 'metrics/visits')
aa.add_metric(metric_name = 'metrics/orders')
aa.add_metric(metric_name = 'metrics/event3')
aa.add_dimension(dimension_name = 'variables/mobiledevicetype')
aa.add_dimension(dimension_name = 'variables/lasttouchchannel')

aa.set_date_range(date_start='2019-12-01', date_end='2020-03-31')

data = aa.get_report_multiple_breakdowns()
print(data)
