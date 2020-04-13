from src.adobe_api.adobe_api import aa_client


aa = aa_client(adobe_org_id = adobe_org_id, subject_account = subject_account, 
    client_id = client_id, client_secret = client_secret, account_id = account_id, private_key_location = private_key_location)

aa.set_report_suite(report_suite_id = 'vodafonegroupukprod')
aa.add_metric(metric_name= 'metrics/visits')
aa.add_metric(metric_name= 'metrics/orders')
aa.add_metric(metric_name= 'metrics/event3')
aa.add_metric(metric_name= 'metrics/event4')
aa.add_metric(metric_name= 'metrics/event5')
aa.add_metric(metric_name= 'metrics/event6')
aa.set_dimension(dimension_name = 'variables/evar65')
aa.set_date_range(date_start = '2019-12-01', date_end= '2019-12-3')
data = aa.get_report()
