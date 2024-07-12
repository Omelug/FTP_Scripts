import ftp_forest
import ftp_nmap
from ftp_forest import *
import logging
import logging

import ftp_forest
import ftp_nmap
from ftp_forest import *

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from ftp_db import *
from ftp_config import CONFIG

conf = CONFIG["ftp_hub"]

def get_args():
    parser = argparse.ArgumentParser(usage="Example: save_ranges -> scan_all_ranges -> check_all_ftp_anon")
    parser.add_argument("--save_ranges", action="store_true",
                        help="Saved from ./inpu/ranges.txt with ranges in format <ip_start>\t<ip_stop>...")
    parser.add_argument("--scan_all_ranges", action="store_true",
                        help="--scan_all: Scan all RANGE in the database, rescan older than old_delay_days")
    parser.add_argument("--scan_all_versions", action="store_true",
                        help="Scan version of all with null version")
    parser.add_argument("--print_ftp_list", action="store_true",
                        help="Print ftp list to stdout")
    args, unknown = parser.parse_known_args()
    return parser, args

async def save_range_from_file(path=conf['ranges']):
    ranges_to_save = [] #all ranges from file
    async with aiofiles.open(conf['input_folder'] + path, 'r') as ip_list:
        async for line in ip_list:
            ip_a, ip_b = line.strip().split('\t')[:2]
            ranges_to_save.append((ip_a.strip(), ip_b.strip()))

    # insert all ranges to db (fast)
    async with get_session() as session:
        query = insert(Range).values([{"ip_a": ip_a, "ip_b": ip_b} for ip_a, ip_b in ranges_to_save])
        do_nothing_stmt = query.on_conflict_do_nothing(index_elements=['ip_a', 'ip_b'])
        await session.execute(do_nothing_stmt)
        await session.commit()

    print_ok(f"New ranges were saved to database")

async def scan_all_ranges(port, after_days=conf["old_delay_days"]):
    async with get_session() as session:
        days_ago = datetime.now() - timedelta(days=after_days)
        range_list = await session.execute(
            select(Range).filter(or_(
                Range.scan_date < days_ago,
                Range.scan_date == None
            ))
        ).scalars().all()
        if not range_list:
            logging.error("RANGE table is empty\n\tYou can use --save_ranges for load to RANGE")
        for range_obj in range_list:
            await range_obj.scan(session=session, port=port)

async def print_ftp_list():
    async with get_session() as session:
        result = await session.execute(select(FTPConn))
        [print(ftp) for ftp in result.scalars()]

async def main():
    parser, args = get_args()
    if '-h' in sys.argv or '--help' in sys.argv:
        parser.print_help()
    if args.save_ranges:
        print(f"save_range_from_file()")
        await save_range_from_file()
    if args.scan_all_ranges:
        print("scan_all_ranges()")
        await scan_all_ranges(port=21)
    if args.scan_all_versions:
        print("scan_all_versions()")
        await ftp_nmap.scan_all_versions()
    if args.print_ftp_list:
        await print_ftp_list()
    return any((args.save_ranges, args.scan_all_ranges, args.print_ftp_list, args.scan_all_versions))

if __name__ == '__main__':
    if asyncio.run(main()):
        exit(0)
    print(f"Invalid arguments for ftp_hub")
    print(f"Try running ftp_forest")
    if asyncio.run(ftp_forest.main()):
        exit(0)
    print(f"Invalid arguments for ftp_forest")
    print(f"Try running ftp_nmap")
    if asyncio.run(ftp_nmap.main()):
        exit(0)
    print(f"Invalid argument for all scripts")