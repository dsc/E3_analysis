
__author__ = "Ryan Faulkner"
__email__ = "rfaulkner@wikimedia.org"
__date__ = "January 6th, 2013"
__license__ = "GPL (version 2 or later)"

import user_metric as um
import src.utils.multiprocessing_wrapper as mpw
from src.etl.data_loader import Connector
from collections import namedtuple
from config import logging
from os import getpid
from dateutil.parser import parse as date_parse
from src.etl.aggregator import decorator_builder, boolean_rate
from query_calls import live_account_query

# Definition of persistent state for RevertRate objects
LiveAccountArgsClass = namedtuple('LiveAccountArgs',
                                    'project namespace log '
                                    'date_start date_end t')

class LiveAccount(um.UserMetric):
    """
        Skeleton class for "live account" metric:

            `https://meta.wikimedia.org/wiki/Research:Metrics/live_account`

        As a UserMetric type this class utilizes the process() function
        attribute to produce an internal list of metrics by user handle
        (typically ID but user names may also be specified). The execution
        of process() produces a nested list that
        stores in each element:

            * user ID
            * boolean value indicating whether the account is considered
                "live" given the parameters

        For example to produce the above datapoint for a user id one could
        call: ::

            >>> from src.metrics.live_account import LiveAccount
            >>> users = ['17792132', '17797320', '17792130', '17792131',
                        '17792136', 13234584, 156171]
            >>> la = LiveAccount(date_start='20110101000000')
            >>> for r in r.process(users,log=True): print r
            ('17792130', -1)
            ('17792131', -1)
            ('17792132', -1)
            ('17797320', -1)
            ('156171', -1)
            ('17792136', 1)
            ('13234584', -1)

        Here the follow outcomes may follow: ::

            -1  - The edit button was not clicked after registration
            0   - The edit button was clicked more than `t` minutes
                    after registration
            1   - The edit button was clicked `t` minutes within registration
    """

    # Structure that defines parameters for RevertRate class
    _param_types = {
        'init' : {
            't' : ['int', 'The time in minutes until the threshold.', 60],
        },
        'process' : {
            'log' : ['bool', 'Enable logging for processing.',False],
            'num_threads' : ['int', 'Number of worker processes over users.',1],
            }
    }

    # Define the metrics data model meta
    _data_model_meta = {
        'id_fields' : [0],
        'date_fields' : [],
        'float_fields' : [],
        'integer_fields' : [],
        'boolean_fields' : [1],
        }

    _agg_indices = {}

    @um.pre_metrics_init
    def __init__(self, **kwargs):
        um.UserMetric.__init__(self, **kwargs)
        self._t_ = int(kwargs['t']) if 't' in kwargs else \
            self._param_types['init']['t'][2]

    @staticmethod
    def header(): return ['user_id', 'is_active_account', ]

    @um.UserMetric.pre_process_users
    def process(self, user_handle, **kwargs):

        self.apply_default_kwargs(kwargs,'process')

        # ensure the handles are iterable
        if not hasattr(user_handle, '__iter__'): user_handle = [user_handle]
        k = int(kwargs['num_threads'])
        log = bool(kwargs['log'])

        if log: logging.info(__name__ + "::parameters = " + str(kwargs))

        # Multiprocessing vs. single processing execution
        args = [self._project_, self._namespace_, log, self._start_ts_,
                self._end_ts_, self._t_]
        self._results = mpw.build_thread_pool(user_handle,_process_help,k,args)

        return self

def _process_help(args):

    # Unpack args
    state = args[1]
    thread_args = LiveAccountArgsClass(state[0],state[1],state[2],state[3],
                                        state[4],state[5])
    user_data = args[0]
    conn = Connector(instance='slave')

    # Log progress
    if thread_args.log:
        logging.info(__name__ + '::Computing live account. (PID = %s)' %
                                getpid())
        logging.info(__name__ + '::From %s to %s. (PID = %s)' % (
            str(thread_args.date_start), str(thread_args.date_end), getpid()))

    # Extract edit button click from edit_page_tracking table (namespace,
    # article title, timestamp) of first click and registration timestamps
    # (join on logging table)
    #
    # Query will return: (user id, time of registration, time of first
    # edit button click)
    la_query = live_account_query(user_data, thread_args.namespace,
                                thread_args.project)
    conn._cur_.execute(la_query)

    # Iterate over results to determine boolean indicating whether
    # account is "live"
    results = { long(user) : -1 for user in user_data}
    for row in conn._cur_:
        try:
            diff = (date_parse(row[2]) - date_parse(row[1])).total_seconds()
            diff /= 60 # get the difference in minutes
        except Exception:
            continue

        if diff <= thread_args.t:
            results[row[0]] = 1
        else:
            results[row[0]] = 0

    return [(str(key), results[key]) for key in results]

@decorator_builder(LiveAccount.header())
def live_accounts_agg(metric):
    """ Computes the fraction of editors that have "live" accounts """
    total=0
    pos=0
    for r in metric.__iter__():
        try:
            if r[1]: pos+=1
            total+=1
        except IndexError: continue
        except TypeError: continue
    if total:
        return [total, pos, float(pos) / total]
    else:
        return [total, pos, 0.0]

# Build "rate" decorator
live_accounts_agg = boolean_rate
live_accounts_agg = decorator_builder(LiveAccount.header())(live_accounts_agg)

setattr(live_accounts_agg, um.METRIC_AGG_METHOD_FLAG, True)
setattr(live_accounts_agg, um.METRIC_AGG_METHOD_NAME, 'live_accounts_agg')
setattr(live_accounts_agg, um.METRIC_AGG_METHOD_HEAD, ['total_users',
                                                        'is_live','rate'])
setattr(live_accounts_agg, um.METRIC_AGG_METHOD_KWARGS, {'val_idx' : 1})

if __name__ == "__main__":
    users = ['17792132', '17797320', '17792130', '17792131', '17792136',
             13234584, 156171]
    la = LiveAccount()
    for r in la.process(users,log=True): print r