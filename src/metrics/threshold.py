
__author__ = "Ryan Faulkner"
__date__ = "December 6th, 2012"
__license__ = "GPL (version 2 or later)"

import datetime
import math
import collections
import os

import multiprocessing as mp
import user_metric as um

class Threshold(um.UserMetric):
    """
        Boolean measure: Did an editor reach some threshold of activity (e.g. n edits, words added, pages created,
        etc.) within t time.

            `https://meta.wikimedia.org/wiki/Research:Metrics/threshold(t,n)`

        As a UserMetric type this class utilizes the process() function attribute to produce an internal list of metrics by
        user handle (typically ID but user names may also be specified). The execution of process() produces a nested list that
        stores in each element:

            * User ID
            * boolean flag to indicate whether edit threshold was reached in time given

        usage e.g.: ::

            >>> import src.etl.threshold as t
            >>> for r in t.Threshold().process([13234584]).__iter__(): print r
            (13234584L, 1)
    """

    def __init__(self,
                 date_start='2001-01-01 00:00:00',
                 date_end=datetime.datetime.now(),
                 t=1440,
                 n=1,
                 **kwargs):

        """
            - Parameters:
                - **date_start**: string or datetime.datetime. start date of edit interval
                - **date_end**: string or datetime.datetime. end date of edit interval
        """
        self._start_ts_ = self._get_timestamp(date_start)
        self._end_ts_ = self._get_timestamp(date_end)
        self._t_ = t
        self._n_ = n

        um.UserMetric.__init__(self, **kwargs)

    @staticmethod
    def header():
        return ['user_id', 'has_reached_threshold']

    def process(self, user_handle, is_id=True, **kwargs):
        """
            - Parameters:
                - **user_handle** - String or Integer (optionally lists).  Value or list of values representing user handle(s).
                - **is_id** - Boolean.  Flag indicating whether user_handle stores user names or user ids
        """

        k = kwargs['num_threads'] if 'num_threads' in kwargs else 0
        log_progress = bool(kwargs['log_progress']) if 'log_progress' in kwargs else False

        # Format condition on user ids.  if no user handle exists there is no condition.
        if user_handle:
            if not hasattr(user_handle, '__iter__'): user_handle = [user_handle]
            user_id_str = um.dl.DataLoader().format_comma_separated_list(
                um.dl.DataLoader().cast_elems_to_string(user_handle), include_quotes=False)
            user_id_cond = "and user_id in (%s)" % user_id_str
        else:
            user_id_cond = ''

        # get all registrations in the time period
        sql = """
            select
                user_id,
                user_registration
            from %(project)s.user
            where user.user_registration >= %(date_start)s and user.user_registration <= %(date_end)s
                %(uid_str)s
        """ % {
            'project' : self._project_,
            'date_start' : self._start_ts_,
            'date_end' : self._end_ts_,
            'uid_str' : user_id_cond
        }

        self._data_source_._cur_.execute(" ".join(sql.strip().split('\n')))

        # Multiprocessing vs. single processing execution
        user_data = [r for r in self._data_source_._cur_]

        if k:
            n = int(math.ceil(float(len(user_data)) / k))

            arg_list = list()
            for i in xrange(k):
                arg_list.append([self._project_, self._namespace_, self._n_, self._t_, user_data[i * n : (i + 1) * n],
                    log_progress])
            pool = mp.Pool(processes=len(arg_list))

            self._results = list()
            for elem in pool.map(_process_help, arg_list): self._results.extend(elem)

            try:
                pool.close()
            except RuntimeError:
                pass

        else:
            self._results = _process_help([self._project_, self._namespace_,
                self._n_, self._t_, user_data])

        return self


def _process_help(args):
    """ Used by Threshold::process() for forking.  Should not be called externally. """

    ThresholdArgsClass = collections.namedtuple('ThresholdArgs', 'project namespace n t user_data log_progress')
    args = ThresholdArgsClass(args[0],args[1],args[2],args[3],args[4],args[5])

    if args.log_progress: print str(datetime.datetime.now()) + ' - Processing revision data ' + \
        '(%s users) by user... (PID = %s)' % (len(args.user_data), os.getpid())

    # only proceed if there is user data
    if not len(args.user_data): return []

    sql = """
            select
                count(*) as revs
            from %(project)s.revision as r
                join %(project)s.page as p
                on r.rev_page = p.page_id
            where p.page_namespace = %(ns)s and rev_timestamp <= %(ts)s and rev_user = %(id)s
        """
    sql = " ".join(sql.strip().split('\n'))

    conn = um.dl.Connector(instance='slave')
    results = list()
    for r in args.user_data:
        try:
            ts = um.UserMetric._get_timestamp(um.date_parse(r[1]) + datetime.timedelta(minutes=args.t))
            id = long(r[0])

            conn._cur_.execute(sql % {'project' : args.project, 'ts' : ts,
                                      'ns' : args.namespace, 'id' : id})
            count = int(conn._cur_.fetchone()[0])
        except IndexError: continue
        except ValueError: continue

        if count < args.n:
            results.append((r[0],0))
        else:
            results.append((r[0],1))

    if args.log_progress: print str(datetime.datetime.now()) + ' - Processed PID = %s.' % os.getpid()

    return results

# testing
if __name__ == "__main__":
    for r in Threshold().process([13234584, 156171], num_threads=2, log_progress=True).__iter__(): print r