#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
	PEF-1_analysis.py - Script used to produce filtered PEF-1 users and to generate volume metrics tables

	Usage:

	Example:
"""

__author__ = "Ryan Faulkner <rfaulkner@wikimedia.org>"
__license__ = "GPL (version 2 or later)"

import sys
import settings
sys.path.append(settings.__project_home__)

import logging
import datetime
import src.etl.data_loader as dl
import src.etl.experiments_loader as el
import src.metrics.bytes_added as b
from dateutil.parser import *

# CONFIGURE THE LOGGER
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%b-%d %H:%M:%S')

def main(args):

    # initialize dataloader objects
    data_loader = dl.DataLoader(db='slave')
    exp_loader = el.ExperimentsLoader()

    # Loop through each user and get byte count data two weeks ahead of registration

    more_excluded_users = data_loader.get_elem_from_nested_list(data_loader.execute_SQL('SELECT DISTINCT user_id FROM dartar.e3_pef_iter1_global WHERE gudiff < -7;'),0)
    more_excluded_users = data_loader.cast_elems_to_string(more_excluded_users)
    exclude_users = data_loader.get_elem_from_nested_list(data_loader.execute_SQL('select distinct ns.user_id from halfak.pef1_blocked as b join rfaulk.e3_pef_iter1_ns as ns on ns.user_id = b.user_id;'),0)
    exclude_users.extend(more_excluded_users)
    exclude_users_str = data_loader.format_comma_separated_list(exclude_users)

    sql_reg_date = 'select user_registration from enwiki.user where user_id = %s;'
    sql = 'select distinct user_id from rfaulk.e3_pef_iter1_ns where not(user_id in (%s))' % exclude_users_str
    eligible_users = data_loader.get_elem_from_nested_list(data_loader.execute_SQL(sql),0)

    logging.info('There are %s eligible user.  Processing ...' % len(eligible_users))

    experiment_start_date = datetime.datetime(year=2012,month=07,day=30)
    bytes_added = list()
    for user in eligible_users:

        # logging.debug('Processing user %s' % user)

        try:

            reg_date = parse(data_loader.execute_SQL(sql_reg_date % user)[0][0])
            end_date = reg_date + datetime.timedelta(days=14)

            # logging.debug('Reg date = %s' % str(reg_date))

            r = b.BytesAdded(date_start=reg_date, date_end=end_date, raw_count=False).process([user])
            key = r.keys()[0]

            entry = list()
            entry.append(key)
            entry.append(str((reg_date-experiment_start_date).seconds / 3600))
            entry.extend(r[key])

            bytes_added.append(entry)

        except Exception as e:
            logging.error('Could not : %s' % str(e))

    logging.info('Writing results to table.')

    data_loader.list_to_xsv(bytes_added)
    data_loader.create_table_from_xsv('list_to_xsv.out', exp_loader.E3_PEF_BA_TABLE, 'e3_pef_iter1_bytesadded', create_table=True)
    data_loader.create_xsv_from_SQL('select r.user_id, d.bucket, r.hour_offset, r.bytes_added_net, r.bytes_added_abs, r.bytes_added_pos, r.bytes_added_neg, r.edit_count from rfaulk.e3_pef_iter1_bytesadded as r join dartar.e3_pef_iter1_users as d on d.user_id = r.user_id;')

# Call Main
if __name__ == "__main__":
    sys.exit(main([]))
