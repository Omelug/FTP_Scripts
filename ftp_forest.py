import argparse
import asyncio
import ftplib
import traceback
from pathlib import Path

import aiofiles
import aioftp
import async_timeout

import ftp_db
from ftp_db import *
from ftp_log import *

conf = CONFIG["ftp_forest"]

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--anon_all", type=str, nargs='?', const=7, default=None,
                        help="-anon_all <n> : Try anonymous: login for all FTP_con, retry older than n days, default 7")
    parser.add_argument("--anon_all_async", type=str, nargs='?', const=7, default=None,
                        help="-anon_all asynchronize ")
    parser.add_argument("-d", type=str, dest="list", default=ftp_db.DATABASE_URL_ASYNC,
                        help=f"Path to database file ({ftp_db.DATABASE_URL_ASYNC} by default).")
    parser.add_argument("-lvl", type=int, dest="max_lvl", default=0,
                        help="Set up the maximum file tree level on FTP servers.")
    parser.add_argument("-q", "--quite", dest="display", action="store_false", default=True,
                        help="Do not display servers that are not responding in the terminal log.")
    parser.add_argument('--user', help='Username')
    parser.add_argument('--password', help='Password')
    parser.add_argument('--crack', help='File containing user and password separated by :')

    return parser.parse_args()

"""async def connect_and_update(session, ftp_conn: FTPConn, user, password):
    try:
        ftp = ftplib.FTP(timeout=10)
        print(f"{ftp_conn}")
        ftp.connect(ftp_conn.ip, ftp_conn.port)
        ftp.login(user, password)
        ftp_conn.status = "connected"
        print_ok(f"{ftp_conn} connected")
    except Exception as e:
        print_e(f"{ftp_conn}: {type(e).__name__}: {e}")
        ftp_conn.error = f"{e}"
        ftp_conn.status = "failed"
        print_e(f"{ftp_conn} failed")
    finally:
        ftp_conn.check_date = datetime.now()
        try:
            await session.commit()
        except Exception as db_e:
            await session.rollback()
            print_e(f"Database error : {db_e}")"""

async def print_tree(client, ftp_conn, directory, output_file, indent=0):
    try:
        async with async_timeout.timeout(15):
            files = await client.list(directory)
            for file in files:
                posix_path, file_info = file
                file_line=f"{ftp_conn}" + ("\t" * indent) + f"{posix_path.stem}{posix_path.suffix}\n"
                await output_file.write(file_line)
                if file_info['type'] == 'dir':
                    await print_tree(client, ftp_conn, f"{directory}/{posix_path.name}", output_file, indent + 1)
    except asyncio.TimeoutError:
        print(f"Timeout while listing directory {directory} for {ftp_conn.ip}")

error_counts = {}

async def handle_error(e, ftp_conn):
    error_type = type(e).__name__

    error_counts[error_type] = error_counts.get(error_type, 0) + 1
    #print_e(f"Async {ftp_conn}: {error_type}: {e}")

    ftp_conn.error = f"{e}"
    ftp_conn.status = "failed"
    print_e(f"Error counts: {error_counts}")


async def connect_async(ftp_id: int, user, password):
    async with get_session() as session:
        ftp_conn : FTPConn = await ftp_by_id(ftp_id, session)
        await create_login(session, user, password)
        try:
            client = aioftp.Client(encoding='iso-8859-2')
            success = False
            async with async_timeout.timeout(conf['connect_timeout']):
                await client.connect(ftp_conn.ip, ftp_conn.port)
                await client.login(user, password)
                ftp_conn.status = "connected"
                success = True
                print_ok(f"{ftp_conn} connected")

            try:
                async with async_timeout.timeout(conf['forest_timeout']):
                    output_folder = Path("./output/tree")
                    output_folder.mkdir(parents=True, exist_ok=True)
                    file = f"{ftp_conn.ip}_{ftp_conn.port}_{user}_{password}.txt"
                    output_file_path = f"{output_folder}/{file}"
                    ftp_conn.path = f"{output_file_path}"
                    async with aiofiles.open(output_file_path, mode="w") as output_file:
                        await print_tree(client, ftp_conn, "/", output_file)
                        ftp_conn.path = f"{file}"
            finally:
                pass

        except Exception as e:
            await handle_error(e, ftp_conn)
        finally:
            ftp_conn.check_date = datetime.now()
            try:
                print(f"{ftp_conn.ip} awdwadaw {ftp_conn.status}")
                await add_login(
                    ftp_conn.id,
                    session,
                    user, password,
                    success=success
                )
                if success:
                    print(f"Connected to {ftp_conn}")
                session.add(ftp_conn)
                await session.commit()
            except Exception as db_e:
                traceback.print_exc()
                print_e(f"Database error: {db_e}")

class Scanner():
    def __init__(self):
        self.queue = asyncio.Queue()

    async def worker(self):
        while True:
            try:
                ftp_id, user, password = await self.queue.get()
                #print_d(f"{ftp_conn} {user} {password}")
                await connect_async(ftp_id, user, password)
            except asyncio.CancelledError:
                return
            except KeyboardInterrupt:
                print_e("\n You have interrupted scan_all_async")
            except Exception as e:
                print_e(f"Error processing task {e}")  # Log the error
            finally:
                self.queue.task_done()

    async def scan(self, ftp_conns , user="anonymous", password="", max_workers=25, after_days=CONFIG['ftp_hub']["old_delay_days"]): #TODO
        print_ok(f"Scan {user}:{password}")

        for ftp in ftp_conns:
            await self.queue.put((ftp.id, user, password))

        workers = [
            asyncio.create_task(self.worker())
            for _ in range(max_workers)
        ]
        await self.queue.join()

        for worker in workers:
            worker.cancel()

def crack(user=None, password=None, file=None):
    if file is not None:
        with open(ARGS.crack, 'r') as f:
            for line in f:
                if ':' in line:
                    user, password = line.strip().split(':', 1)
                    crack(user=user, password=password)
                else:
                    print_e(f"Ignoring invalid line: {line.strip()}")
    elif user is not None and password is not None:
        ftp_conns = FTP_Conns_for_LogInfo(user=user, password=password)
        asyncio.run(Scanner().scan(ftp_conns, user=user, password=password))
    else:
        raise ValueError("You need to provide user and password or file with user:password pairs")

if __name__ == '__main__':
    ARGS = get_args()
    thread_list = []
    tasks_list = []
    scanner = Scanner()
    if ARGS.anon_all:
        ftp_conns = asyncio.run(FTP_Conns_after(after_days=7))
        Scanner().scan(ftp_conns)
    try:
        if ARGS.anon_all_async:
            ftp_conns = asyncio.run(FTP_Conns_after(after_days=7))
            asyncio.run(scanner.scan(ftp_conns=ftp_conns))
        if ARGS.user and ARGS.password:
            crack(user=ARGS.user, password=ARGS.password)
        elif ARGS.user or ARGS.password:
            print(f"You need user and password, not only {ARGS.user} {ARGS.password}",file=sys.stderr)
            exit(1)
        elif ARGS.crack:
            crack(file=ARGS.crack)
    except KeyboardInterrupt:
        print_e("\n You have interrupted scan_all_async")

