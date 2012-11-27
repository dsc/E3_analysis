
"""
    Format data representation for Wikipedia feedback solicited via the article feedback tool (AFT).

    The results of the AFT feedback is logged in three tables described below.

    s1-analytics-slave.eqiad.wmnet.enwiki.aft_article_feedback: ::
        +--------------------------+------------------+------+-----+----------------+----------------+
        | Field                    | Type             | Null | Key | Default        | Extra          |
        +--------------------------+------------------+------+-----+----------------+----------------+
        | af_id                    | int(10) unsigned | NO   | PRI | NULL           | auto_increment |
        | af_page_id               | int(10) unsigned | NO   | MUL | NULL           |                |
        | af_user_id               | int(11)          | NO   | MUL | NULL           |                |
        | af_user_ip               | varbinary(32)    | YES  |     | NULL           |                |
        | af_user_anon_token       | varbinary(32)    | NO   |     |                |                |
        | af_revision_id           | int(10) unsigned | NO   | MUL | NULL           |                |
        | af_bucket_id             | int(10) unsigned | NO   |     | 0              |                |
        | af_cta_id                | int(10) unsigned | NO   |     | 0              |                |
        | af_link_id               | int(10) unsigned | NO   |     | 0              |                |
        | af_created               | binary(14)       | NO   | MUL |                |                |
        | af_abuse_count           | int(10) unsigned | NO   |     | 0              |                |
        | af_helpful_count         | int(10) unsigned | NO   |     | 0              |                |
        | af_unhelpful_count       | int(10) unsigned | NO   |     | 0              |                |
        | af_oversight_count       | int(10) unsigned | NO   |     | 0              |                |
        | af_is_deleted            | tinyint(1)       | NO   |     | 0              |                |
        | af_is_hidden             | tinyint(1)       | NO   |     | 0              |                |
        | af_net_helpfulness       | int(11)          | NO   |     | 0              |                |
        | af_has_comment           | tinyint(1)       | NO   |     | 0              |                |
        | af_is_unhidden           | tinyint(1)       | NO   |     | 0              |                |
        | af_is_undeleted          | tinyint(1)       | NO   |     | 0              |                |
        | af_is_declined           | tinyint(1)       | NO   |     | 0              |                |
        | af_activity_count        | int(10) unsigned | NO   |     | 0              |                |
        | af_form_id               | int(10) unsigned | NO   |     | 0              |                |
        | af_experiment            | varbinary(32)    | YES  | MUL | NULL           |                |
        | af_suppress_count        | int(10) unsigned | NO   |     | 0              |                |
        | af_last_status           | varbinary(16)    | YES  |     | NULL           |                |
        | af_last_status_user_id   | int(10) unsigned | NO   |     | 0              |                |
        | af_last_status_timestamp | binary(14)       | YES  |     |                |                |
        | af_is_autohide           | tinyint(1)       | NO   |     | 0              |                |
        | af_is_unrequested        | tinyint(1)       | NO   |     | 0              |                |
        | af_is_featured           | tinyint(1)       | NO   |     | 0              |                |
        | af_is_unfeatured         | tinyint(1)       | NO   |     | 0              |                |
        | af_is_resolved           | tinyint(1)       | NO   |     | 0              |                |
        | af_is_unresolved         | tinyint(1)       | NO   |     | 0              |                |
        | af_relevance_score       | int(11)          | NO   |     | 0              |                |
        | af_relevance_sort        | int(11)          | NO   | MUL | 0              |                |
        | af_last_status_notes     | varbinary(255)   | YES  |     | NULL           |                |
        +--------------------------+------------------+------+-----+----------------+----------------+

    s1-analytics-slave.eqiad.wmnet.enwiki.aft_article_answer_text: ::
        +-------------------+------------------+------+-----+---------+----------------+
        | Field             | Type             | Null | Key | Default | Extra          |
        +-------------------+------------------+------+-----+---------+----------------+
        | aat_id            | int(10) unsigned | NO   | PRI | NULL    | auto_increment |
        | aat_response_text | blob             | NO   |     | NULL    |                |
        +-------------------+------------------+------+-----+---------+----------------+

    s1-analytics-slave.eqiad.wmnet.enwiki.logging: ::
        +---------------+---------------------+------+-----+----------------+----------------+
        | Field         | Type                | Null | Key | Default        | Extra          |
        +---------------+---------------------+------+-----+----------------+----------------+
        | log_id        | int(10) unsigned    | NO   | PRI | NULL           | auto_increment |
        | log_type      | varbinary(32)       | NO   | MUL |                |                |
        | log_action    | varbinary(32)       | NO   | MUL |                |                |
        | log_timestamp | varbinary(14)       | NO   | MUL | 19700101000000 |                |
        | log_user      | int(10) unsigned    | NO   | MUL | 0              |                |
        | log_namespace | int(11)             | NO   | MUL | 0              |                |
        | log_title     | varbinary(255)      | NO   | MUL |                |                |
        | log_comment   | varbinary(255)      | NO   |     |                |                |
        | log_params    | blob                | NO   |     | NULL           |                |
        | log_deleted   | tinyint(3) unsigned | NO   |     | 0              |                |
        | log_user_text | varbinary(255)      | NO   |     |                |                |
        | log_page      | int(10) unsigned    | YES  | MUL | NULL           |                |
        +---------------+---------------------+------+-----+----------------+----------------+


    With each feedback event is associated a answer text

    FEATURES:

        * answer feedback length
        * is featured (af_is_featured)
        * is hidden (af_is_hidden)
        * is unhidden (af_is_unhidden)
        * times tagged as helpful (af_helpful_count)


    EXAMPLES: ::

        >>> f = aft.AFTFeedbackFactory().__iter__()
        >>> d = f.next()
        2012-11-27 14:18:50.191411 - SFT Feedback - start = "2012-11-26 14:18:50.191386", end = "2012-11-27 14:18:50.191386"
        >>>
        >>> d.feedback_length
        545L
        >>> d
        AFT_feedback(is_featured=0, is_hidden=0, is_unhidden=0, helpful_count=0L, feedback_length=545L)
        >>> for d in f: print d
        ...
        AFT_feedback(is_featured=0, is_hidden=0, is_unhidden=0, helpful_count=0L, feedback_length=327L)
        AFT_feedback(is_featured=0, is_hidden=0, is_unhidden=0, helpful_count=0L, feedback_length=445L)
        AFT_feedback(is_featured=0, is_hidden=0, is_unhidden=0, helpful_count=0L, feedback_length=278L)
        AFT_feedback(is_featured=0, is_hidden=0, is_unhidden=0, helpful_count=0L, feedback_length=344L)
        AFT_feedback(is_featured=0, is_hidden=0, is_unhidden=0, helpful_count=0L, feedback_length=328L)
        ...

"""

__author__ = "Ryan Faulkner <rfaulkner@wikimedia.org>"
__date__ = "November 27th, 2012"
__license__ = "GPL (version 2 or later)"

import collections
import datetime
import src.etl.data_loader as dl
import src.metrics.user_metric as um

TBL_ANSWER_TEXT = "aft_article_feedback"
TBL_ANSWER_TEXT = "aft_article_answer_text"


class AFTFeedbackFactory(object):

    __instance = None

    def __init__(self, *args, **kwargs):

        self.__feature_list = ['is_featured', 'is_hidden', 'is_unhidden', 'helpful_count', 'feedback_length']
        self.__tuple_cls = collections.namedtuple("AFT_feedback", " ".join(self.__feature_list))

        super(AFTFeedbackFactory, self).__init__()

    def __new__(cls, *args, **kwargs):
        """ This class is Singleton, return only one instance """
        if not cls.__instance:
            cls.__instance = super(AFTFeedbackFactory, cls).__new__(cls, *args, **kwargs)
        return cls.__instance

    def __iter__(self, **kwargs):

        conn = dl.Connector(instance='slave')
        is_gen, start_date, end_date =  self.process_kwargs(**kwargs)

        sql =\
        """
            select
                af_is_featured,
                af_is_hidden,
                af_is_unhidden,
                af_helpful_count,
                length(aat_response_text) as text_len
            from enwiki.aft_article_feedback as af
                join enwiki.aft_article_answer as aa
                on af.af_id = aa.aa_feedback_id
                join enwiki.aft_article_answer_text as aat
                on aa.aat_id = aat.aat_id
            where af_created > "%(start)s" and af_created < "%(end)s"
        """ % {
            'start' : start_date,
            'end' : end_date
        }


        # compose feature vectors
        conn._cur_.execute(" ".join(sql.strip().split('\n')))
        if is_gen:
            for r in conn._cur_:
                try:
                    yield self.__tuple_cls(r[0],r[1],r[2],r[3],r[4])
                except IndexError:
                    continue

    def __doc__(self): raise NotImplementedError

    def process_kwargs(self, **kwargs):

        td = datetime.timedelta(days=-1)
        now = datetime.datetime.now()

        is_gen = bool(kwargs['is_gen']) if 'is_gen' in kwargs else True
        start_date = str(kwargs['start_date']) if 'start_date' in kwargs else str((now + td))
        end_date = str(kwargs['end_date']) if 'end_date' in kwargs else str(now)

        print str(datetime.datetime.now()) + ' - AFT Feedback - start = "%s", end = "%s" ' % (start_date, end_date)

        return is_gen, um.UserMetric._get_timestamp(start_date), um.UserMetric._get_timestamp(end_date)


# Testing
if __name__ == "__main__":
    f = AFTFeedbackFactory().__iter__()
