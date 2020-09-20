from src.analytics.mayhem.adobe import analytics_client
import os

report_suite_id = os.getenv('aa_report_suite_id')
client_id = os.getenv('aa_client_id')
client_secret = os.getenv('aa_client_secret')
global_company_id = os.getenv('aa_global_company_id')
adobe_org_id = os.getenv('aa_adobe_org_id')
subject_account = os.getenv('aa_subject_account')
account_id = os.getenv('aa_global_company_id')
private_key_location = '.ssh/adobe-auth/private.key'

aa = analytics_client(
    adobe_org_id=adobe_org_id,
    subject_account=subject_account,
    client_id=client_id,
    client_secret=client_secret,
    account_id=account_id,
    private_key_location=private_key_location
)

aa.set_report_suite(report_suite_id=report_suite_id)
aa.add_metric(metric_name='metrics/visits')
aa.add_metric(metric_name='metrics/orders')
aa.add_metric(metric_name='metrics/event3')
aa.add_dimension(dimension_name='variables/mobiledevicetype')
aa.add_dimension(dimension_name='variables/lasttouchchannel')

aa.set_date_range(date_start='2019-12-01', date_end='2020-03-31')

data = aa.get_report_multiple_breakdowns()
print(data)
