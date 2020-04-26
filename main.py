from src.analytics.mayhem.adobe import analytics_client


aa = analytics_client(adobe_org_id = adobe_org_id, subject_account = subject_account, 
    client_id = client_id, client_secret = client_secret, account_id = account_id, private_key_location = private_key_location)

aa.set_report_suite(report_suite_id = report_suite_id)
aa.add_metric(metric_name= 'metrics/visits')
aa.add_metric(metric_name= 'metrics/orders')
aa.add_metric(metric_name= 'metrics/event3')
# aa.add_metric(metric_name= 'metrics/event4')
# aa.add_metric(metric_name= 'metrics/event5')
# aa.add_metric(metric_name= 'metrics/event6')
aa.set_dimension(dimension_name = 'variables/mobiledevicetype')
aa.set_date_range(date_start = '2019-12-01', date_end= '2019-12-3')
# data = aa.get_report()
# print(data)

page = aa._get_page()
df_page = aa.format_output(page)

def add_breakdown_report_object(report_object, breakdown, item_id):
    report_object = json.loads(json.dumps(report_object))
    original_breakdown = report_object['dimension']
    metrics_num = len(report_object['metricContainer']['metrics'])
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
    # report_object['metricContainer']['metricFilters'] = metric_filter
    return report_object

def get_report_breakdown(df_page, dimensions, current_level = None):
    
    # import pdb; pdb.set_trace()
    tmp_report_object = aa.report_object
    parent_itemId = df_page['itemId_lvl_{}'.format(current_level - 1)]
    for dimension in dimensions:
        tmp_report_object = add_breakdown_report_object(tmp_report_object, dimension, parent_itemId)
    
    page = aa._get_page(tmp_report_object)
    results = aa.format_output(page)
    # The itemId in the results is set to minus 1 to match with the parent ID during the merge
    
    for key in df_page.keys():
        if ('_lvl_' in key):
            results[key] = df_page[key]

    # if (len(dimensions) > 1):
    #    import pdb; pdb.set_trace()
    
    # results['itemId_lvl_{}'.format(current_level - 1)] = parent_itemId
    results = results.rename(columns = {
            'itemId' : 'itemId_lvl_{}'.format(current_level),
            'value' : 'value_lvl_{}'.format(current_level)
        })
    return results

def get_all_breakdowns(df_page):
    import pdb; pdb.set_trace()  
    multi_breakdown = ['variables/lasttouchchannel', 'variables/evar29']
    #multi_breakdown = ['variables/lasttouchchannel']
    current_dimensions = []
    level = 1
    dim_index = 0

    df_page = df_page.filter(regex='^itemId|^value', axis = 'columns').rename(columns = {'itemId' : 'itemId_lvl_{}'.format(level),'value' : 'value_lvl_{}'.format(level)})
    level = 2
    for breakdown in multi_breakdown:
        current_dimensions.append(multi_breakdown[dim_index])
        dim_index = dim_index + 1
        print('Current Dimension: {}'.format(current_dimensions))
        
        results_broken_down = df_page.apply(get_report_breakdown, axis = 1 , \
                                                    dimensions = current_dimensions, current_level = level)
        print('returned from breakdown')
        dl = []
        for i in results_broken_down:
            dl.append(i)
        
        # import pdb; pdb.set_trace()
        results_broken_down = pd.concat(dl, ignore_index=True)
        import pdb; pdb.set_trace()  
        # df_page = df_page.filter(regex='^itemId|^value', axis = 'columns').rename(columns = {'itemId' : 'itemId_lvl_{}'.format(level),'value' : 'value_lvl_{}'.format(level)})
        

        df_page = pd.merge(df_page, results_broken_down, how = 'right')
        # df_page = pd.merge(df_page, results_broken_down, left_on = 'itemId_lvl_{}'.format(level), right_on = 'parentId', how = 'right')
        # df_page = df_page.rename(columns = {'parentId' : 'parentId_lvl_{}'.format(level)})
        # df_page = df_page.drop(columns=['parentId'])
        
        level = level + 1
        
        print('Level: {}'.format(level))
        
    # import pdb; pdb.set_trace()  
    return df_page

result = get_all_breakdowns(df_page)

print(result)