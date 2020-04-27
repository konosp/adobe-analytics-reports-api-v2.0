# Adobe Analytics Python package 
Download Reports data utilising the Adobe.io version 2.0 API.

# Requirements

## Adobe.io access
In order to run the package, first you need to gain access to a service account from Adobe.io. The method used is JWT authentication. More instructions on how to create the integration at: https://www.adobe.io/authentication/auth-methods.html#!AdobeDocs/adobeio-auth/master/JWT/JWT.md. After you have completed the integration, you will need to have available the following information:
- Organization ID (issuer): It is in the format of < organisation id >@AdobeOrg
- Technical Account ID: < tech account id >@techacct.adobe.com 
- Client ID: Information is available on the completion of the Service Account integration
- Client Secret: Information is available on the completion of the Service Account integration
- Account ID: Instructions on how to obtain it at https://youtu.be/lrg1MuVi0Fo?t=96
- Report suite: Report suite ID from which you want to download the data.

Make sure that the integration is associated with an Adobe Analytics product profile that is granted access to the necessary metrics and dimensions.

## Package installation
```
pip install analytics-mayhem-adobe
```

# Samples

## Initial setup

After you have configured the integration and downloaded the package, the following setup is needed:
```
from analytics.mayhem.adobe import analytics_client

adobe_org_id = '<adobe org id>@AdobeOrg'
subject_account = '<technical account id>@techacct.adobe.com'
client_id = '<client id>'
client_secret = '<client secret>'
private_key_location = '.ssh/adobe-auth/private.key'
account_id = '<account id>'
report_suite_id = '<report suite>'
```
Next initialise the Adobe client:
```
aa = analytics_client( \
    adobe_org_id = adobe_org_id, \
    subject_account = subject_account, \
    client_id = client_id, client_secret = client_secret, \
    account_id = account_id, \
    private_key_location = private_key_location)
```
Simple request:

```
aa.set_report_suite(report_suite_id = report_suite_id)
aa.add_metric(metric_name= 'metrics/visits')
aa.add_metric(metric_name= 'metrics/orders')
aa.add_metric(metric_name= 'metrics/event3')
aa.set_dimension(dimension_name = 'variables/lasttouchchannel')
aa.set_date_range(date_start = '2019-12-01', date_end= '2019-12-31')
data = aa.get_report()
```

## Issues, Bugs and Suggestions:
https://github.com/konosp/adobe-analytics-reports-api-v2.0/issues

# Reading
If you are interested to read more, have a look at http://analyticsmayhem.com