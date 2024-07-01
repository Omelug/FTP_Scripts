import argparse
import sys

import nmap3

import ftp_db
import asyncio

from ftp_log import print_ok


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan_all_versions", action="store_true", help="-scan_all_versions : Try versions of all FTP_conns")
    args, unknown = parser.parse_known_args()
    return parser, args


def get_ftp_version(ip, port):
    try:
        nm = nmap3.Nmap()
        results = nm.nmap_version_detection(f"{ip}", args=f"-p {port}", timeout=10)
        for result in results:
            service = results[result]['ports'][0]['service']
            print_ok(f"{service}")
            if service['name'] == 'ftp':
                print_ok(f"{ip}:{port}\t{service['product']}")

                return str(service['product']), service.get('version', None), service.get('ostype', None)
        return None, None, None
    except Exception as e:
        print(f"Error {e}")
        return f"Error {e}", None, None

async def scan_version(ftp_id):
    async with ftp_db.get_session() as session:
        ftp = await ftp_db.ftp_by_id(ftp_id, session)
        product,version, os_type = get_ftp_version(ftp.ip, ftp.port)
        ftp.product = product
        ftp.version = version
        ftp.os_type = os_type
        session.add(ftp)
        await session.commit()

async def scan_all_versions():
    ftp_list = await ftp_db.FTP_Conns_with_null_version()
    tasks = [scan_version(ftp_id) for ftp_id in ftp_list]
    await asyncio.gather(*tasks)


async def main():
    parser, args = get_args()
    if args.scan_all_versions:
        await scan_all_versions()
    return any((args.scan_all_versions,))
