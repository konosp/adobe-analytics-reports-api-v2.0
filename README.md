# Adobe Analytics Python package 
Download Reports data utilising the Adobe.io version 2.0 API.

![](https://github.com/konosp/adobe-analytics-reports-api-v2.0/workflows/Package%20Testing/badge.svg)

For more Digital Analytics related reading, check https://analyticsmayhem.com

# Authentication methods supported by the package:
1. JWT
2. OAuth (tested only through Jupyter Notebook!)

## JWT Requirements & Adobe.io access
In order to run the package, first you need to gain access to a service account from Adobe.io. The method used is JWT authentication. More instructions on how to create the integration at: https://www.adobe.io/authentication/auth-methods.html#!AdobeDocs/adobeio-auth/master/JWT/JWT.md. After you have completed the integration, you will need to have available the following information:
- Organization ID (issuer): It is in the format of < organisation id >@AdobeOrg
- Technical Account ID: < tech account id >@techacct.adobe.com 
- Client ID: Information is available on the completion of the Service Account integration
- Client Secret: Information is available on the completion of the Service Account integration
- Account ID: Instructions on how to obtain it at https://youtu.be/lrg1MuVi0Fo?t=96
- Report suite: Report suite ID from which you want to download the data.

Make sure that the integration is associated with an Adobe Analytics product profile that is granted access to the necessary metrics and dimensions.

## OAuth Requirements
To perform an OAuth authentication you need to create an integration at the Adobe I/O Console as described in the guide by Adobe at https://github.com/AdobeDocs/analytics-2.0-apis/blob/master/create-oauth-client.md. The result of the integration provides the following information:
- Client ID (API Key)
- Client Secret

### Package installation
```
pip install analytics-mayhem-adobe
```

### Samples

#### Initial setup - JWT
After you have configured the integration and downloaded the package, the following setup is needed:
```
from analytics.mayhem.adobe import analytics_client
import os

ADOBE_ORG_ID = os.environ['ADOBE_ORG_ID']
SUBJECT_ACCOUNT = os.environ['SUBJECT_ACCOUNT']
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
PRIVATE_KEY_LOCATION = os.environ['PRIVATE_KEY_LOCATION']
GLOBAL_COMPANY_ID = os.environ['GLOBAL_COMPANY_ID']
REPORT_SUITE_ID = os.environ['REPORT_SUITE_ID']
```
Next initialise the Adobe client:
```
aa = analytics_client(
        adobe_org_id = ADOBE_ORG_ID, 
        subject_account = SUBJECT_ACCOUNT, 
        client_id = CLIENT_ID, 
        client_secret = CLIENT_SECRET,
        account_id = GLOBAL_COMPANY_ID, 
        private_key_location = PRIVATE_KEY_LOCATION
)

aa.set_report_suite(report_suite_id = REPORT_SUITE_ID)
```
#### Initial setup - OAuth

Import the package and initiate the required parameters
```
from analytics.mayhem.adobe import analytics_client

client_id = '<client id>'
client_secret = '<client secret>'
global_company_id = '<global company id>'
```
Initialise the Adobe client:
```
aa = analytics_client(
        auth_client_id = client_id, 
        client_secret = client_secret,
        account_id = global_company_id
)
```
Perform the authentication
```
aa._authenticate()
```
This will open a new window and will request you to login to Adobe. After you complete the login process, you will be redirect to the URL you configured as redirect URI during the Adobe Integration creation process. If everything is done correctly, final URL will have a URL query string parameter in the format of `www.adobe.com/?code=eyJ....`. Copy the full URL and paste it in the input text.
For a demo notebook, please refer to the [Jupyter Notebook - OAuth example](examples/OAuth%20Demo.ipynb)


### Report Configurations
Set the date range of the report (format: YYYY-MM-DD)
```
aa.set_date_range(date_start = '2019-12-01', date_end= '2019-12-31')
```
To configure specific hours for the start and end date:
```
aa.set_date_range(date_start='2020-12-01', date_end='2020-12-01', hour_start= 4, hour_end= 5 )
```
If `hour_end` is set, then only up to that hour in the last day data will be retrieved instead of the full day.
#### Request with 3 metrics and 1 dimension
```
aa.add_metric(metric_name= 'metrics/visits')
aa.add_metric(metric_name= 'metrics/orders')
aa.add_metric(metric_name= 'metrics/event1')
aa.add_dimension(dimension_name = 'variables/mobiledevicetype')
data = aa.get_report()
```
Output:

|itemId_lvl_1   |  value_lvl_1 | metrics/visits | metrics/orders | metrics/event1
| --- | --- | --- | --- | --- |
|         0     |      Other    |  5000    |    3    | 100
|  1728229488   |       Tablet  |     200   |   45    |  30
|  2163986270   | Mobile Phone  |    49   |    23   |  31
|  ...    | ...  |       ...   |        ...   |      ...

#### Request with 3 metrics and 2 dimensions:
```
aa.add_metric(metric_name= 'metrics/visits')
aa.add_metric(metric_name= 'metrics/orders')
aa.add_metric(metric_name= 'metrics/event1')
aa.add_dimension(dimension_name = 'variables/mobiledevicetype')
aa.add_dimension(dimension_name = 'variables/lasttouchchannel')
data = aa.get_report_multiple_breakdowns()
```
Output:
Each item in level 1 (i.e. Tablet) is broken down by the dimension in level 2 (i.e. Last Touch Channel). The package downloads all possible combinations. In a similar fashion more dimensions can be added.

| itemId_lvl_1 | value_lvl_1 | itemId_lvl_2 |  value_lvl_2 | metrics/visits | metrics/orders  | metrics/event1 |
| --- | --- | --- | --- | --- | --- | --- |
|0 |Other |1 |Paid Search| 233| 39|10 |
|0 |Other |2 |Natural Search| 424| 12  |412 |
|0 |Other |3 |Display| 840| 41  |31 |
| ... | ... | ... | ... | ... | ... | ... |
| 1728229488 |Tablet |1 | Paid Search| 80| 12  |41 |
| 1728229488 |Tablet |2 |Natural Search| 50| 41  |21 |
| ... | ... | ... | ... | ... | ... | ... |

#### Global segments
To add a segment, you need the segment ID (currently only this option is supported). To obtain the ID, you need to activate the Adobe Analytics Workspace debugger (https://github.com/AdobeDocs/analytics-2.0-apis/blob/master/reporting-tricks.md). Then inspect the JSON request window and locate the segment ID under the 'globalFilters' object.

To apply the segment:
```
aa.add_global_segment(segment_id = "s1689_5ea0ca222b1c1747636dc970")
```
# Issues, Bugs and Suggestions:
https://github.com/konosp/adobe-analytics-reports-api-v2.0/issues

Known missing features:
- No support for filtering
- No support for custom sorting
