"""
    The engine for the metrics API.  Stores definitions an backend
    API operations.
"""
__author__ = "ryan faulkner"
__email__ = "rfaulkner@wikimedia.org"
__date__ = "january 11 2012"
__license__ = "GPL (version 2 or later)"

from flask import escape, redirect, url_for
from src.utils.record_type import *
from dateutil.parser import parse as date_parse
from datetime import timedelta, datetime
from re import search
from collections import OrderedDict, namedtuple

import src.etl.data_loader as dl
import src.metrics.metrics_manager as mm

from config import logging

# Regex that matches a MediaWiki user ID
MW_UID_REGEX = r'^[0-9]{5}[0-9]*$'
MW_UNAME_REGEX = r'[a-zA-Z_\.\+ ]'

# Define standard variable names in the query string - store in named tuple
RequestMeta = recordtype('RequestMeta',
    'cohort_expr cohort_gen_timestamp metric time_series aggregator '
    'restrict project namespace date_start date_end interval t n')

def RequestMetaFactory(cohort_expr, cohort_gen_timestamp, metric):
    """
        Dynamically builds a record type given a metric handle

        All args must be strings representing a cohort, last updated
        timestamp, and metric respectively.
    """
    default_params = 'cohort_expr cohort_gen_timestamp metric '
    additional_params = ''
    for val in QUERY_PARAMS_BY_METRIC[metric]:
        additional_params += val.query_var + ' '
    additional_params = additional_params[:-1]
    params = default_params + additional_params

    arg_list = ['cohort_expr', 'cohort_gen_timestamp', 'metric'] + \
               ['None'] * len(QUERY_PARAMS_BY_METRIC[metric])
    arg_str = "(" + ",".join(arg_list) + ")"

    rt = recordtype("RequestMeta", params)
    return eval('rt' + arg_str)


REQUEST_META_QUERY_STR = ['aggregator', 'time_series', 'project', 'namespace',
                          'date_start', 'date_end', 'interval', 't', 'n',
                          'time_unit','time_unit_count', 'look_ahead',
                          'look_back', 'threshold_type', 'restrict',
                          ]
REQUEST_META_BASE = ['cohort_expr', 'metric']


# Using the MEDIATOR model :: Defines the query parameters accepted by each
# metric request.  This is a dict keyed on
# metric that stores a list of tuples.  Each tuple defines:
#
#       (<name of allowable query string var>, <name of corresponding metric param>)

# defines a tuple for mapped variable names
varMapping = namedtuple("VarMapping", "query_var metric_var")

common_params = [varMapping('date_start','date_start'),
                 varMapping('date_end','date_end'),
                 varMapping('project','project'),
                 varMapping('namespace','namespace'),
                 varMapping('interval','interval'),
                 varMapping('time_series','time_series'),
                 varMapping('aggregator','aggregator')]

QUERY_PARAMS_BY_METRIC = {
    'blocks' : common_params,
    'bytes_added' : common_params,
    'edit_count' : common_params,
    'edit_rate' : common_params + [varMapping('time_unit','time_unit'),
                                   varMapping('time_unit_count',
                                       'time_unit_count'),],
    'live_account' : common_params + [varMapping('t','t'),],
    'namespace_edits' : common_params,
    'revert_rate' : common_params + [varMapping('look_back','look_back'),
                                     varMapping('look_ahead','look_ahead'),],
    'survival' : common_params + [varMapping('restrict','restrict'),
                                    varMapping('t','t'),],
    'threshold' : common_params + [varMapping('restrict','restrict'),
                                    varMapping('t','t'),
                                    varMapping('n','n'),],
    'time_to_threshold' : common_params + [varMapping('threshold_type',
        'threshold_type_class'),],
    }

# This is used to separate key meta and key strings for hash table data
# e.g. "metric <==> blocks"
HASH_KEY_DELIMETER = " <==> "

# Datetime string format to be used throughout the API
DATETIME_STR_FORMAT = "%Y%m%d%H%M%S"

def process_request_params(request_meta):
    """
        Applies defaults and consistency to RequestMeta data

            request_meta - RequestMeta recordtype.  Stores the request data.
    """

    DEFAULT_INTERVAL = 14
    TIME_STR = '000000'

    end = datetime.now()
    start= end + timedelta(days=-DEFAULT_INTERVAL)

    # Handle any datetime fields passed - raise an exception if the
    # formatting is incorrect
    if request_meta.date_start:
        try:
            request_meta.date_start = date_parse(
                request_meta.date_start).strftime(
                DATETIME_STR_FORMAT)[:8] + TIME_STR
        except ValueError:
            # Pass the value of the error code in `error_codes`
            raise MetricsAPIError('1')
    else:
        request_meta.date_start = start.strftime(
            DATETIME_STR_FORMAT)[:8] + TIME_STR

    if request_meta.date_end:
        try:
            request_meta.date_end = date_parse(
                request_meta.date_end).strftime(
                DATETIME_STR_FORMAT)[:8] + TIME_STR
        except ValueError:
            # Pass the value of the error code in `error_codes`
            raise MetricsAPIError('1')
    else:
        request_meta.date_end = end.strftime(
            DATETIME_STR_FORMAT)[:8] + TIME_STR

    # set the aggregator if there is one
    agg_key = mm.get_agg_key(request_meta.aggregator, request_meta.metric)
    request_meta.aggregator = request_meta.aggregator if agg_key else None


def get_users(cohort_expr):
    """ get users from cohort """

    if search(COHORT_REGEX, cohort_expr):
        logging.info(__name__ + '::Processing cohort by expression.')
        users = [user for user in parse_cohorts(cohort_expr)]
    else:
        logging.info(__name__ + '::Processing cohort by tag name.')
        conn = dl.Connector(instance='slave')
        try:
            conn._cur_.execute('select utm_id from usertags_meta '
                               'WHERE utm_name = "%s"' % str(cohort_expr))
            res = conn._cur_.fetchone()[0]
            conn._cur_.execute('select ut_user from usertags '
                               'WHERE ut_tag = "%s"' % res)
        except IndexError:
            redirect(url_for('cohorts'))
        users = [r[0] for r in conn._cur_]
        del conn
    return users

def get_cohort_id(utm_name):
    """ Pull cohort ids from cohort handles """
    conn = dl.Connector(instance='slave')
    conn._cur_.execute('SELECT utm_id FROM usertags_meta '
                       'WHERE utm_name = "%s"' % str(escape(utm_name)))

    utm_id = None
    try: utm_id = conn._cur_.fetchone()[0]
    except ValueError: pass

    # Ensure the field was retrieved
    if not utm_id:
        logging.error(__name__ + '::Missing utm_id for cohort %s.' %
                                 str(utm_name))
        utm_id = -1

    del conn
    return utm_id

def get_cohort_refresh_datetime(utm_id):
    """
        Get the latest refresh datetime of a cohort.  Returns current time
        formatted as a string if the field is not found.
    """
    conn = dl.Connector(instance='slave')
    conn._cur_.execute('SELECT utm_touched FROM usertags_meta '
                       'WHERE utm_id = %s' % str(escape(utm_id)))

    utm_touched = None
    try: utm_touched = conn._cur_.fetchone()[0]
    except ValueError: pass

    # Ensure the field was retrieved
    if not utm_touched:
        logging.error(__name__ + '::Missing utm_touched for cohort %s.' %
                                 str(utm_id))
        utm_touched = datetime.now()

    del conn
    return utm_touched.strftime(DATETIME_STR_FORMAT)

def get_data(request_meta, hash_table_ref):
    """ Extract data from the global hash given a request object """

    # Traverse the hash key structure to find data
    # @TODO rather than iterate through REQUEST_META_BASE &
    #   REQUEST_META_QUERY_STR look only at existing attributes

    logging.debug(__name__ + "::Attempting to pull data for request {0}".
        format(str(request_meta)))
    for key_name in REQUEST_META_BASE + REQUEST_META_QUERY_STR:
        if hasattr(request_meta, key_name) and getattr(request_meta, key_name):
            key = getattr(request_meta, key_name)
        else:
            continue

        full_key = key_name + HASH_KEY_DELIMETER + key
        if hasattr(hash_table_ref, 'has_key') and hash_table_ref.has_key(
            full_key):
            hash_table_ref = hash_table_ref[full_key]
        else:
            return None

    # Ensure that an interface that does not rely on keyed values is returned
    # all data must be in interfaces resembling lists
    if not hasattr(hash_table_ref, '__iter__'):
        return hash_table_ref
    else:
        return None

def set_data(request_meta, data, hash_table_ref):
    """
        Given request meta-data and a dataset create a key path in the global
        hash to store the data
    """

    key_sig = list()

    # Build the key signature
    for key_name in REQUEST_META_BASE: # These keys must exist
        key = getattr(request_meta, key_name)
        if key:
            key_sig.append(key_name + HASH_KEY_DELIMETER + key)
        else:
            logging.error(__name__ + '::Request must include %s. '
                                     'Cannot set data %s.' % (
                key_name, str(request_meta)))
            return

    for key_name in REQUEST_META_QUERY_STR: # These keys may optionally exist
        if hasattr(request_meta,key_name):
            key = getattr(request_meta, key_name)
            if key: key_sig.append(key_name + HASH_KEY_DELIMETER + key)

    logging.debug(__name__ + "::Adding data to hash @ key signature = {0}".
        format(str(key_sig)))
    # For each key in the key signature add a nested key to the hash
    last_item = key_sig[len(key_sig) - 1]
    for key in key_sig:
        if key != last_item:
            if not (hasattr(hash_table_ref, 'has_key') and
                    hash_table_ref.has_key(key) and
                    hasattr(hash_table_ref[key], 'has_key')):
                hash_table_ref[key] = OrderedDict()

            hash_table_ref = hash_table_ref[key]
        else:
            hash_table_ref[key] = data

def get_url_from_keys(keys, path_root):
    """ Compose a url from a set of keys """
    query_str = ''
    for key in keys:
        parts = key.split(HASH_KEY_DELIMETER)
        if parts[0] in REQUEST_META_BASE:
            path_root += '/' + parts[1]
        elif parts[0] in REQUEST_META_QUERY_STR:
            query_str += parts[0] + '=' + parts[1] + '&'

    if not path_root: raise MetricsAPIError
    if query_str:
        url = path_root + '?' + query_str[:-1]
    else:
        url = path_root
    return url

def build_key_tree(nested_dict):
    """ Builds a tree of key values from a nested dict. """
    if hasattr(nested_dict, 'keys'):
        for key in nested_dict.keys(): yield (key, build_key_tree(
            nested_dict[key]))
    else:
        yield None

#
# Cohort parsing methods
#
# ======================

# This regex must be matched to parse cohorts
COHORT_REGEX = r'^([0-9]+[&~])*[0-9]+$'

COHORT_OP_AND = '&'
COHORT_OP_OR = '~'
# COHORT_OP_NOT = '^'

def parse_cohorts(expression):
    """
        Defines and parses boolean expressions of cohorts and returns a list
        of user ids corresponding to the expression argument.

            Parameters:
                - **expression**: str. Boolean expression built of
                    cohort labels.

            Return:
                - List(str).  user ids corresponding to cohort expression.
    """

    # match expression
    if not search(COHORT_REGEX, expression):
        raise MetricsAPIError()

    # parse expression
    return parse(expression)


def parse(expression):
    """ Top level parsing. Splits expression by OR then sub-expressions by
        AND. returns a generator of ids included in the evaluated expression
    """
    user_ids_seen = set()
    for sub_exp_1 in expression.split(COHORT_OP_OR):
        for user_id in intersect_ids(sub_exp_1.split(COHORT_OP_AND)):
            if not user_ids_seen.__contains__(user_id):
                user_ids_seen.add(user_id)
                yield user_id


def get_cohort_ids(conn, cohort_id):
    """ Returns string valued ids corresponding to a cohort """
    sql = """
        SELECT ut_user
        FROM staging.usertags
        WHERE ut_tag = %(id)s
    """ % {
        'id' : str(cohort_id)
    }
    conn._cur_.execute(sql)
    for row in conn._cur_:
        yield str(row[0])

def intersect_ids(cohort_id_list):

    conn = dl.Connector(instance='slave')

    user_ids = dict()
    # only a single cohort id in the expression - return all users of this
    # cohort
    if len(cohort_id_list) == 1:
        for id in get_cohort_ids(conn, cohort_id_list[0]):
            yield id
    else:
        for cid in cohort_id_list:
            for id in get_cohort_ids(conn, cid):
                if user_ids.has_key(id):
                    user_ids[id] += 1
                else:
                    user_ids[id] = 1
            # Executes only in the case that there was more than one cohort
            # id in the expression
        for key in user_ids:
            if user_ids[key] > 1: yield key
    del conn

class MetricsAPIError(Exception):
    """ Basic exception class for UserMetric types """
    def __init__(self, message="Error processing API request."):
        Exception.__init__(self, message)