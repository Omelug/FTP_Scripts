import argparse
import asyncio

import nmap3

import ftp_db
from ftp_log import print_ok, print_e


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan_all_versions", action="store_true", help="--scan_all_versions : Try versions of all FTP_conns")
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

                #print(f"{ip}  {str(service['product'])} ")
                #print(f"{ip}  {service.get('version', None)}")
                #print(f"{ip}  {service.get('ostype', None)}")
                return str(service['product']), service.get('version', None), service.get('ostype', None)
        return None, None, None
    except Exception as e:
        print(f"Error {e}")
        return f"Error {e}", None, None

async def scan_version(session, ftp_id, ip, port):
    try:
        ftp = await ftp_db.ftp_by_id(ftp_id, session)
        product, version, os_type = get_ftp_version(ip, port)
        ftp.product = product
        ftp.version = version
        ftp.os_type = os_type
        session.add(ftp)
        await session.commit()
    except Exception as e:
        print(f"Error {e}")

class Scanner:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def worker(self):
        try:
            async with ftp_db.get_session() as session:
                while True:
                    try:
                        ftp_id, ip, port = await self.queue.get()
                        await scan_version(session, ftp_id, ip, port)
                        self.queue.task_done()
                    except Exception as e:
                        print_e(f"Error processing task {e}")
        except KeyboardInterrupt:
                print_e("\n You have interrupted scan_all_async")

    async def scan_all_versions(self, max_workers=10):
        ids_ips_ports = await ftp_db.FTP_Conns_with_null_version()

        for ftp_id, ip, port in ids_ips_ports:
            await self.queue.put((ftp_id, ip, port))

        workers = [
            asyncio.create_task(self.worker())
            for _ in range(max_workers)
        ]
        await self.queue.join()

        for worker in workers:
            worker.cancel()


async def scan_all_versions():
        await Scanner().scan_all_versions()

async def main():
    parser, args = get_args()
    if args.scan_all_versions:
        asyncio.run(scan_all_versions())
    return any((args.scan_all_versions,))
