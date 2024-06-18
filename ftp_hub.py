# this is compilation of some scripts, because i wante work with sqite


# https://github.com/rethyxyz/FTPAutomator/blob/main/FTPAutomator.py
# https://github.com/Sunlight-Rim/FTPSearcher/tree/main?tab=readme-ov-file
#
import asyncio
import logging
from sqlalchemy import or_
import argparse
from ftp_forest import *

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from ftp_db import *
from ftp_config import CONFIG

conf = CONFIG["ftp_hub"]

def get_args():
    parser = argparse.ArgumentParser(usage="Example: save_ranges -> scan_all_ranges -> check_all_ftp_anon")
    parser.add_argument("--save_ranges", action="store_true",
                        help="ranges.txt file with ranges in format <ip_start>\t<ip_stop>\t<count>\t<date>\tcompany")
    parser.add_argument("--scan_all_ranges", type=int, nargs='?', const=7, default=None,
                        help="-scan_all <n> : Scan all RANGE in the database, rescan older than n days, default 7")
    parser.add_argument("--last", type=int, default=7,
                        help="-anon_all <n> : Try anonymous: login for all FTP_con, retry older than n days, default 7")
    parser.add_argument("--anon_all", type=str, nargs='?', const=7, default=None,
                        help="-anon_all <n> : Try anonymous: login for all FTP_con, retry older than n days, default 7")
    parser.add_argument("--print_ftp_list", action="store_true",
                        help="Print ftp list to stdout")
    return parser.parse_args()


async def save_range(ip_a, ip_b):
    async with get_session() as session:
        stmt = select(Range).filter_by(ip_a=ip_a, ip_b=ip_b)
        result = await session.execute(stmt)
        existing_record = result.scalars().first()
        if existing_record:
            return False
        session.add(Range(ip_a=ip_a, ip_b=ip_b))
        await session.commit()
        return True


async def save_range_from_file(path=conf['ranges']):
    with open(conf['input_folder'] + path, 'r') as ip_list:
        for line in ip_list:
            ip_a, ip_b = line.strip().split('\t')[:2]
            if await save_range(ip_a.strip(), ip_b.strip()):
                print_ok(f"Saved new range|{ip_a.strip()}|-|{ip_b.strip()}|")


async def scan_all_ranges(port, after_days):
    async with get_session() as session:
        days_ago = datetime.now() - timedelta(days=after_days)
        result = await session.execute(
            select(Range).filter(or_(
                Range.save_date < days_ago,
                Range.save_date == None
            ))
        )
        range_list = result.scalars().all()
        if not range_list:
            logging.error("RANGE table is empty\n\tYou can use --save_ranges for load to RANGE")
        for range_obj in range_list:
            await range_obj.scan(session=session, port=port)

async def print_ftp_list():
    async with get_session() as session:
        result = await session.execute(select(FTPConn))
        [print(ftp) for ftp in result.scalars()]


if __name__ == '__main__':

    args = get_args()
    if args.save_ranges:
        print(f"save_range_from_file()")
        asyncio.run(save_range_from_file())
    if args.scan_all_ranges is not None:
        print("scan_all_ranges()")
        asyncio.run(scan_all_ranges(port=21, after_days=args.last))
    if args.anon_all is not None:
        print(f"check_all_ftp_anon() last {args.anon_all} days")
        ftp_conns = asyncio.run(FTP_Conns_after(after_days=7))
        scanner = Scanner()
        asyncio.run(scanner.scan(ftp_conns))
    if args.print_ftp_list:
        asyncio.run(print_ftp_list())
