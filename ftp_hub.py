# this is compilation of some scripts, because i wante work with sqite


# https://github.com/rethyxyz/FTPAutomator/blob/main/FTPAutomator.py
# https://github.com/Sunlight-Rim/FTPSearcher/tree/main?tab=readme-ov-file
#
import asyncio
import logging
from sqlalchemy import or_
import argparse
import ftp_forest

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from ftp_db import *


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save_ranges", type=str, nargs='?', const="./ranges.txt", default=None,
                        help="ranges.txt file with ranges in format <ip_start>\t<ip_stop>\t<count>\t<date>\tcompany")
    parser.add_argument("--scan_all_ranges", type=int, nargs='?', const=7, default=None,
                        help="-scan_all <n> : Scan all RANGE in the database, rescan older than n days, default 7")
    parser.add_argument("--last", type=int, default=7,
                        help="-anon_all <n> : Try anonymous: login for all FTP_con, retry older than n days, default 7")
    parser.add_argument("--anon_all", type=str, nargs='?', const=7, default=None,
                        help="-anon_all <n> : Try anonymous: login for all FTP_con, retry older than n days, default 7")
    parser.add_argument("--print_ftp_list", type=bool, default=False,
                        help="Print ftp list to stdout")
    return parser.parse_args()


def save_range(ip_a, ip_b):
    with Session() as session:
        existing_record = session.query(Range).filter_by(ip_a=ip_a, ip_b=ip_b).first()
        if existing_record:
            return False
        session.add(Range(ip_a=ip_a, ip_b=ip_b))
        session.commit()
        return True


def save_range_from_file(path):
    with open(path, 'r') as ip_list:
        for line in ip_list:
            ip_a = line.rstrip('\n').split('\t')[0].strip(' ')
            ip_b = line.rstrip('\n').split('\t')[1].strip(' ')
            save_range(ip_a, ip_b)


def scan_all_ranges(port, after_days):
    with Session() as session:
        days_ago = datetime.now() - timedelta(days=after_days)
        range_list = session.execute(
            select(Range).filter(or_(
                Range.save_date < days_ago,
                Range.save_date == None
            )).limit(100)
        )
        if not range_list:
            logging.error("RANGE table is empty\n\tYou can use --save_ranges for load to RANGE")
        for range_row in range_list:
            range_obj = range_row[0]
            range_obj.scan(session=session, port=port)


def check_all_ftp_anon(after_days=7):
    asyncio.run(ftp_forest.scan_all_async(after_days=after_days))


def print_ftp_list():
    with Session() as session:
        [print(ftp) for ftp in session.query(FTPConn)]


if __name__ == '__main__':
    Base.metadata.create_all(sync_engine)

    args = get_args()
    if args.save_ranges is not None:
        print(f"save_range_from_file() {args.save_ranges}")
        save_range_from_file(args.save_ranges)
    if args.scan_all_ranges is not None:
        print("scan_all_ranges()")
        scan_all_ranges(port=21, after_days=args.last)
    if args.anon_all is not None:
        print(f"check_all_ftp_anon() last {args.anon_all} days")
        check_all_ftp_anon(after_days=args.anon_all)
    if args.print_ftp_list:
        print_ftp_list()
