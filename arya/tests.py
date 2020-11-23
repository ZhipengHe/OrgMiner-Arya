from flask import *
from os.path import join
import pandas as pd

from . import app, APP_STATIC

bp = Blueprint('tests', __name__,
    url_prefix='/tests', template_folder='templates/tests'
)

'''Chart rendering handlers
'''
def _bar_chart(spec, title, data_url, data_attrs):
    spec['title'] = title
    spec['data'] = {'url': data_url}

    # rect layer
    spec['encoding']['x'] = data_attrs['x']
    spec['encoding']['y'] = data_attrs['y']
    spec['encoding']['color'] = data_attrs['x']
    # text layer
    spec['layer'][1]['encoding']['text']['field'] = data_attrs['y']['field']
    
    return spec

def _reorderable_matrix(spec, title, 
    data_url, data_attrs, color_scheme):
    spec['title'] = title
    spec['data'] = {'url': data_url}

    spec['encoding']['x'] = data_attrs['x']
    spec['encoding']['y'] = data_attrs['y']

    # rect layer
    spec['layer'][0]['encoding']['color']['field'] = \
        data_attrs['c']['field']

    # text layer
    spec['layer'][1]['encoding']['text']['field'] = data_attrs['c']['field']

    # text layer - text contrast
    spec['transform'].append({
        'joinaggregate': [{
            'op': 'max',
            'field': data_attrs['c']['field'],
            'as': 'max_aggregate_c'
        }]
    })
    spec['transform'].append({
        'calculate': (
            '0.5 * datum.max_aggregate_c < datum.' +
            '{}'.format(data_attrs['c']['field'])
        ),
        'as': 'threshold_aggregate_c'
    })

    spec['config']['range']['heatmap']['scheme'] = color_scheme

    return spec

def _reorderable_matrix_facet(spec, title, 
    data_url, data_attrs, color_scheme):
    spec['title'] = title
    spec['data'] = {'url': data_url}

    spec['spec']['encoding']['x'] = data_attrs['x']
    spec['spec']['encoding']['y'] = data_attrs['y']

    # rect layer
    spec['spec']['layer'][0]['encoding']['color']['field'] = \
        data_attrs['c']['field']

    # text layer
    spec['spec']['layer'][1]['encoding']['text']['field'] = \
        data_attrs['c']['field']

    # text layer - text contrast
    spec['transform'].append({
        'joinaggregate': [{
            'op': 'max',
            'field': data_attrs['c']['field'],
            'as': 'max_aggregate_c'
        }]
    })
    spec['transform'].append({
        'calculate': (
            '0.5 * datum.max_aggregate_c < datum.' +
            '{}'.format(data_attrs['c']['field'])
        ),
        'as': 'threshold_aggregate_c'
    })

    spec['config']['range']['heatmap']['scheme'] = color_scheme

    return spec

def _stack_area_chart(spec, title, data_url, data_attrs):
    spec['title'] = title
    spec['data'] = {'url': data_url}

    # transform time units
    spec['transform'][0]['timeUnit'] = data_attrs['datetime']['timeUnit']
    spec['transform'][0]['field'] = data_attrs['datetime']['field']

    # stack area layer
    spec['layer'][0]['encoding']['y'] = data_attrs['y']
    spec['layer'][0]['encoding']['color'] = data_attrs['c']
    spec['layer'][0]['selection']['category']['fields'].append(
        data_attrs['c']['field']
    )

    # ruler layer
    spec['layer'][1]['transform'][0]['pivot'] = data_attrs['c']['field']
    spec['layer'][1]['transform'][0]['value'] = data_attrs['y']['field']
    # ruler layer - tooltip
    category_values = list(str(v) for v in data_attrs['category_values']) 
    for cat in sorted(category_values):
        spec['layer'][1]['encoding']['tooltip'].append({
            'field': cat,
            'type': 'quantitative',
            'title': ' {}'.format(cat)
        })

    return spec

'''Request handlers
'''

@bp.route('/')
def index():
    return render_template('toc.html')

@bp.route('/profiles/workload/<path:indicator>')
def show_profiles_workload(indicator):
    import json
    dirpath = 'tests/profiles/'
    logfpath = join(dirpath, 'data', 'bpic15_combined.csv')
    analysis_name = (
        'Analyze workload of resource groups over year 2011-2014 ' +
        '(Note: cases are non-atomic)'
    )

    if indicator == 'stake':
        with open(join(APP_STATIC, dirpath, 'vlspec/bar_chart.vl.json')) as f:
            spec = json.load(f)

        spec['transform'].append({
            'joinaggregate': [{
                'op': 'count',
                'as': 'stake'
            }],
            'groupby': ['group']
        })
        spec['transform'].append({
            'joinaggregate': [{
                'op': 'count',
                'as': 'total'
            }]
        })
        spec['transform'].append({
            'calculate': 'datum.stake / datum.total',
            'as': 'stake'
        })
        
        spec = _bar_chart(
            spec=spec,
            title='allocation of all work (# events) to groups',
            data_url=url_for('static', filename=logfpath),
            data_attrs={
                'x': {'field': 'group', 'title': 'resource group'},
                'y': {
                    # min/max as there is only 1 unique value
                    'aggregate': 'min',
                    'field': 'stake', 'title': '% events',
                    'type': 'quantitative',
                    'scale': {'domain': [0, 1]}
                }
            }
        )
        
        return render_template('profiles.html',
            name=analysis_name,
            spec=spec,
            rel_views=[
                {
                    'name': 'allocation of all work (# events) to groups over time',
                    'link': url_for(
                        'tests.track_profiles_workload',
                        indicator='stake'
                    )
                }
            ]
        )
    
    if indicator in ['assignment', 'relative_focus', 'relative_stake']:
        exec_mode_dim = request.args.get('dim', 'tt')

        with open(join(APP_STATIC, dirpath, 'vlspec/matrix.vl.json')) as f:
            spec = json.load(f)
        
        # aggregate on a selected dimension of execution modes
        if exec_mode_dim == 'ct':
            spec['transform'].append({
                'aggregate': [{
                    'op': 'distinct',
                    'field': 'case_id',
                    'as': 'aggregate_assignment'
                }],
                'groupby': ['group', exec_mode_dim]
            })
        else:
            spec['transform'].append({
                'aggregate': [{
                    'op': 'count',
                    'as': 'aggregate_assignment'
                }],
                'groupby': ['group', exec_mode_dim]
            })

        if indicator == 'assignment':
            spec = _reorderable_matrix(
                spec=spec,
                title=(
                    'assignment: distribution of work by groups ' +
                    'over different "{}"'.format(exec_mode_dim)
                ),
                data_url=url_for('static', filename=logfpath),
                data_attrs={
                    'x': {'field': 'group', 'title': 'resource group'},
                    'y': {'field': exec_mode_dim, 'title': ''},
                    'c': {'field': 'aggregate_assignment'}
                },
                color_scheme='yellowgreenblue'
            )
            spec['layer'][0]['encoding']['color']['legend']['title'] = \
                '# cases' if exec_mode_dim == 'ct' else '# events'
            spec['layer'][0]['encoding']['color']['legend']['format'] = \
                'd'
            spec['layer'][1]['encoding']['text']['format'] = \
                'd'
        if indicator == 'relative_focus':
            spec['transform'].append({
                'joinaggregate': [{
                    'op': 'sum',
                    'field': 'aggregate_assignment',
                    'as': 'total_group'
                }],
                'groupby': ['group']
            })
            spec['transform'].append({
                'calculate': \
                    'datum.aggregate_assignment / datum.total_group',
                'as': 'relative_focus'
            })
            spec = _reorderable_matrix(
                spec=spec,
                title=(
                    'relative focus: how groups manage their own workload ' +
                    'over different "{}"'.format(exec_mode_dim)
                ),
                data_url=url_for('static', filename=logfpath),
                data_attrs={
                    'x': {'field': 'group', 'title': 'resource group'},
                    'y': {'field': exec_mode_dim, 'title': ''},
                    'c': {'field': 'relative_focus'}
                },
                color_scheme='yellowgreenblue'
            )
            spec['layer'][0]['encoding']['color']['legend']['title'] = \
                '% executions'
            spec['layer'][0]['encoding']['color']['legend']['format'] = \
                '.0%'
            spec['layer'][1]['encoding']['text']['format'] = \
                '.2%'
        elif indicator == 'relative_stake':
            spec['transform'].append({
                'joinaggregate': [{
                    'op': 'sum',
                    'field': 'aggregate_assignment',
                    'as': 'total_mode'
                }],
                'groupby': [exec_mode_dim]
            })
            spec['transform'].append({
                'calculate': \
                    'datum.aggregate_assignment / datum.total_mode',
                'as': 'relative_stake'
            })
            spec = _reorderable_matrix(
                spec=spec,
                title=(
                    'relative stake: how groups contribute to ' +
                    'different "{}"'.format(exec_mode_dim)
                ),
                data_url=url_for('static', filename=logfpath),
                data_attrs={
                    'x': {'field': 'group', 'title': 'resource group'},
                    'y': {'field': exec_mode_dim, 'title': ''},
                    'c': {'field': 'relative_stake'}
                },
                color_scheme='warmgreys'
            )
            spec['layer'][0]['encoding']['color']['legend']['title'] = \
                '% contribution'
            spec['layer'][0]['encoding']['color']['legend']['format'] = \
                '.0%'
            spec['layer'][1]['encoding']['text']['format'] = \
                '.2%'
        else:
            pass
            
        return render_template('profiles.html',
            name=analysis_name,
            spec=spec,
            rel_views=[
                {
                    'name': 'assignment: distribution of work by groups',
                    'link': url_for(
                        'tests.show_profiles_workload',
                        indicator='assignment'
                    )
                },
                {
                    'name': 'relative focus: how groups manage their workload',
                    'link': url_for(
                        'tests.show_profiles_workload',
                        indicator='relative_focus'
                    )
                },
                {
                    'name': 'relative stake: how groups contribute',
                    'link': url_for(
                        'tests.show_profiles_workload',
                        indicator='relative_stake'
                    )
                },
            ]
        )
    
    return '<h2> No valid option specified </h2>'

@bp.route('/profiles/participation/<path:indicator>')
def show_profiles_participation(indicator):
    import json
    dirpath = 'tests/profiles/'
    logfpath = join(dirpath, 'data', 'bpic15_combined.csv')
    analysis_name = 'Analyze participation of resource group members over year 2011-2014'

    if indicator == 'attendance':
        exec_mode_dim = request.args.get('dim', 'tt')

        with open(join(APP_STATIC, dirpath, 'vlspec/matrix.vl.json')) as f:
            spec = json.load(f)

        spec['transform'].append({
            'joinaggregate': [{
                'op': 'distinct',
                'field': 'resource',
                'as': 'group_size'
            }],
            'groupby': ['group']
        })
        spec['transform'].append({
            'joinaggregate': [{
                'op': 'distinct',
                'field': 'resource',
                'as': 'aggregate_resource_count'
            }],
            'groupby': ['group', exec_mode_dim]
        })
        spec['transform'].append({
            'calculate': 'datum.aggregate_resource_count / datum.group_size',
            'as': 'attendance'
        })
        spec['transform'].append({
            'aggregate': [{
                # min/max as there is only 1 unique value
                'op': 'max',
                'field': 'attendance',
                'as': 'attendance'
            }],
            'groupby': ['group', exec_mode_dim]
        })

        spec = _reorderable_matrix(
            spec=spec,
            title=(
                'attendance: involvement of resource group members ' +
                'on work taken by a group ' +
                'over different "{}"'.format(exec_mode_dim)
            ),
            data_url=url_for('static', filename=logfpath),
            data_attrs={
                'x': {'field': 'group', 'title': 'resource group'},
                'y': {'field': exec_mode_dim, 'title': ''},
                'c': {'field': 'attendance'}
            },
            color_scheme='greens'
        )
        spec['layer'][0]['encoding']['color']['legend']['title'] = \
            '% group'
        spec['layer'][0]['encoding']['color']['legend']['format'] = \
            '.0%'
        spec['layer'][1]['encoding']['text']['format'] = \
            '.0%'

        return render_template('profiles.html',
            name=analysis_name,
            spec=spec
        )
    return '<h2> No valid option specified </h2>'



@bp.route('/profiles/distribution/<path:indicator>')
def show_profiles_distribution(indicator):
    import json
    dirpath = 'tests/profiles/'
    logfpath = join(dirpath, 'data', 'bpic15_combined.csv')
    analysis_name = 'Analyze distribution within resource groups over year 2011-2014'

    group = request.args.get('group')
    filter_group_selection = {
        'filter': 'datum.group == "{}"'.format(group)
    }

    if indicator == 'member_load':
        with open(join(APP_STATIC, dirpath, 'vlspec/bar_chart.vl.json')) as f:
            spec = json.load(f)

        spec['transform'].append(filter_group_selection)
        spec['transform'].append({
            'joinaggregate': [{
                'op': 'count',
                'as': 'member_load'
            }],
            'groupby': ['resource']
        })
        spec['transform'].append({
            'joinaggregate': [{
                'op': 'count',
                'as': 'total'
            }]
        })
        spec['transform'].append({
            'calculate': 'datum.member_load / datum.total',
            'as': 'member_load'
        })
        
        spec = _bar_chart(
            spec=spec,
            title=(
                'member load: allocation of all work (#events)' 
                + ' taken by a group, to its members'
            ),
            data_url=url_for('static', filename=logfpath),
            data_attrs={
                'x': {
                    'field': 'resource', 
                    'title': 'group member of {}'.format(group)
                },
                'y': {
                    # min/max as there is only 1 unique value
                    'aggregate': 'min',
                    'field': 'member_load', 'title': '',
                    'type': 'quantitative',
                    'scale': {'domain': [0, 1]}
                }
            }
        )
        
        return render_template('profiles.html',
            name=analysis_name,
            spec=spec,
            rel_views=[
                {
                    'name': 'Analyze the change of distribution within resource groups',
                    'link': '{}?group={}'.format(
                        url_for(
                            'tests.track_profiles_distribution',
                            indicator='member_load'
                        ),
                        group
                    )
                }
            ]
        )
    
    if indicator == 'member_assignment':
        exec_mode_dim = request.args.get('dim', 'tt')

        with open(join(APP_STATIC, dirpath, 'vlspec/matrix_facet.vl.json')) as f:
            spec = json.load(f)
        
        # aggregate on a selected dimension of execution modes
        if exec_mode_dim == 'ct':
            return 'undefined'

        spec['transform'].append({
            'joinaggregate': [{
                'op': 'count',
                'as': 'member_assignment',
            }],
            'groupby': ['resource', exec_mode_dim]
        })
        spec = _reorderable_matrix_facet(
            spec=spec,
            title=(
                'assignment: distribution of work to group members ' +
                'over different "{}"'.format(exec_mode_dim)
            ),
            data_url=url_for('static', filename=logfpath),
            data_attrs={
                'x': {
                    'field': 'resource', 'title': 'group member'
                },
                'y': {
                    'field': exec_mode_dim, 'title': ''
                },
                'c': {
                    'field': 'member_assignment'
                }
            },
            color_scheme='yellowgreenblue'
        )
        spec['spec']['layer'][0]['encoding']['color']['legend']['title'] = \
            '# events'
        spec['spec']['layer'][0]['encoding']['color']['legend']['format'] = \
            'd'
        spec['spec']['layer'][1]['encoding']['text']['format'] = \
            'd'

        return render_template('profiles.html',
            name=analysis_name,
            spec=spec
        )

    return '<h2> No valid option specified </h2>'

@bp.route('/profiles/track/workload/<path:indicator>')
def track_profiles_workload(indicator):
    import json
    dirpath = 'tests/profiles/'
    logfpath = join(dirpath, 'data', 'bpic15_combined.csv')
    with open(join(APP_STATIC, logfpath)) as flog:
        log = pd.read_csv(flog)

    analysis_name = 'Analyze the change of workload of resource groups'

    if indicator == 'stake':
        with open(join(APP_STATIC, dirpath, 'vlspec/stack_area_chart.vl.json')) as f:
            spec = json.load(f)
        spec['transform'].append({
            'aggregate': [{
                'op': 'count',
                'as': 'total_assignment'
            }],
            'groupby': ['datetime', 'group']
        })
        spec = _stack_area_chart(
            spec=spec,
            title='allocation of all work (# events) to groups over time',
            data_url=url_for('static', filename=logfpath),
            data_attrs={
                'datetime': {
                    'timeUnit': 'yearmonth',
                    'field': 'date',
                },
                'y': {
                    'field': 'total_assignment',
                    'title': '# events',
                    'type': 'quantitative'
                },
                'c': {
                    'field': 'group',
                    'type': 'nominal'
                },
                'category_values': log['group'].unique()
            }
        )
        
        return render_template('profiles.html',
            name=analysis_name,
            spec=spec
        )
    return '<h2> No valid option specified </h2>'

@bp.route('/profiles/track/distribution/<path:indicator>')
def track_profiles_distribution(indicator):
    import json
    dirpath = 'tests/profiles/'
    logfpath = join(dirpath, 'data', 'bpic15_combined.csv')
    analysis_name = 'Analyze the change of distribution within resource groups'

    group = request.args.get('group')
    filter_group_selection = {
        'filter': 'datum.group == "{}"'.format(group)
    }
    with open(join(APP_STATIC, logfpath)) as flog:
        log = pd.read_csv(flog)
    log = log[log['group'] == group]


    if indicator == 'member_load':
        with open(join(APP_STATIC, dirpath, 'vlspec/stack_area_chart.vl.json')) as f:
            spec = json.load(f)
        spec['transform'].append(filter_group_selection)

        spec['transform'].append({
            'aggregate': [{
                'op': 'count',
                'as': 'total_assignment'
            }],
            'groupby': ['datetime', 'resource']
        })

        spec = _stack_area_chart(
            spec=spec,
            title=(
                'member load: allocation of all work (#events)' 
                + ' taken by a group, to its members'
            ),
            data_url=url_for('static', filename=logfpath),
            data_attrs={
                'datetime': {
                    'timeUnit': 'yearmonth',
                    'field': 'date',
                },
                'y': {
                    'field': 'total_assignment',
                    'title': '# events',
                    'type': 'quantitative'
                },
                'c': {
                    'field': 'resource',
                    'type': 'nominal'
                },
                'category_values': log['resource'].unique()
            }
        )
        return render_template('profiles.html',
            name=analysis_name,
            spec=spec
        )
    return '<h2> No valid option specified </h2>'
