from line_profiler import LineProfiler

profile = LineProfiler()
import argparse
import re
import asyncio
import traceback
from pathlib import Path
import os
import aiofiles
import aioftp
import async_timeout

import ftp_db
from ftp_db import *
from ftp_log import *

conf = CONFIG["ftp_forest"]
quite = False


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--anon_all", action="store_true",
                        help="-anon_all <n> : Try anonymous: login for all FTP_con, retry older than n days")
    parser.add_argument("-d", type=str, dest="list", default=ftp_db.DATABASE_URL_ASYNC,
                        help=f"Path to database file ({ftp_db.DATABASE_URL_ASYNC} by default).")
    parser.add_argument("-lvl", type=int, dest="max_lvl", default=0,
                        help="Set up the maximum file tree level on FTP servers.")
    parser.add_argument("--quite", action="store_true",
                        help="Do not display servers that are not responding in the terminal log.")
    parser.add_argument('--user', help='Username')
    parser.add_argument('--password', help='Password')
    parser.add_argument('--crack', action="store_true", help='File containing user and password separated by :')

    args, unknown = parser.parse_known_args()
    return args


async def print_tree(client, ftp_conn, directory, output_file, indent=0):
    try:
        files = await client.list(directory)
        for file in files:
            posix_path, file_info = file
            file_line = ("\t" * indent) + f"{posix_path.stem}{posix_path.suffix}\n"
            await output_file.write(file_line)
            if file_info['type'] == 'dir':
                await print_tree(client, ftp_conn, f"{directory}/{posix_path.name}", output_file, indent + 1)
    except aioftp.errors.StatusCodeError:
        pass

error_counts = {}


async def handle_error(e, ftp_conn):
    error_type = type(e).__name__
    error_counts[error_type] = error_counts.get(error_type, 0) + 1
    ftp_conn.error = f"{e}"
    ftp_conn.status = "failed"
    if not quite:
        print_e(f"{ftp_conn.ip} Error counts: {error_counts}")


async def connect_async(ftp_id: int, user, password, login_info_id=None):
    async with get_session() as session:
        ftp_conn: FTPConn = await ftp_by_id(ftp_id, session)
        success = False

        try:
            client = aioftp.Client(encoding='iso-8859-2')

            async with async_timeout.timeout(conf['connect_timeout']):
                await client.connect(ftp_conn.ip, ftp_conn.port)
                await client.login(user, password)
                ftp_conn.status = "connected"
                success = True
                print_ok(f"{ftp_conn} connected")
            try:
                async with async_timeout.timeout(conf['forest_timeout']):
                    subfolder = f"{user}_{password}"
                    output_folder = Path(f"./output/tree/{subfolder}")
                    output_folder.mkdir(parents=True, exist_ok=True)
                    file = f"{ftp_conn.ip}_{ftp_conn.port}.txt"
                    output_file_path = f"{output_folder}/{file}"
                    ftp_conn.path = f"failed"
                    async with aiofiles.open(output_file_path, mode="w") as output_file:
                        await print_tree(client, ftp_conn, "/", output_file)
                    ftp_conn.path = f"{output_file_path}"
            except TimeoutError:
                print_e(f"{ftp_conn} TimeoutError")
                await output_file.write("TimeoutError")
            except ConnectionResetError:
                print_e(f"{ftp_conn} ConnectionResetError")
                await output_file.write("TimeoutError")
            except ValueError:
                print_e(f"{ftp_conn} ValueError (probably stupid encoding)")
                await output_file.write("ValueError: stupid encoding")
            except Exception as e:
                print(f"Tree Error: {e.__class__.__name__}")
                traceback.print_exc()
            finally:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, os.sync)
                with open(output_file_path, 'r') as file:
                    content = file.read()
                if not content.strip():
                    Path(output_file_path).unlink()
                    ftp_conn.path = "empty"
                    print_ok(f"{ftp_conn} is empty")
                else:
                    ftp_conn.path = str(file)
                    print_ok(f"{ftp_conn} tree saved to {output_file_path}")
        except Exception as e:
            await handle_error(e, ftp_conn)
        finally:
            ftp_conn.check_date = datetime.now()
            try:
                #print(f"{ftp_conn.ip} awdwadaw {ftp_conn.status}")
                await add_login(
                    ftp_conn.id,
                    session,
                    user, password,
                    success=success,
                    login_info_id=login_info_id
                )
                session.add(ftp_conn)
                await session.commit()
            except Exception as db_e:
                traceback.print_exc()
                print_e(f"Database error: {db_e}")


class Scanner():
    def __init__(self):
        self.queue = asyncio.Queue()

    async def worker(self, login_info_id=None):
        while True:
            try:
                ftp_id, user, password = await self.queue.get()
                await connect_async(ftp_id, user, password, login_info_id=login_info_id)
                self.queue.task_done()
            except KeyboardInterrupt:
                print_e("\n You have interrupted scan_all_async")
            except Exception as e:
                print_e(f"Error processing task {e}")

    async def scan_ftp(self, ftp_ids=[], user="anonymous", password="", max_workers=conf['max_workers'],
                       after_days=CONFIG['ftp_hub']["old_delay_days"]):  #TODO
        print_ok(f"Scan {user}:{password}")
        async with get_session() as session:
            login_info_id = await create_login(session, user, password)

        for ftp_id in ftp_ids:
            await self.queue.put((ftp_id, user, password))

        workers = [
            asyncio.create_task(self.worker(login_info_id=login_info_id))
            for _ in range(max_workers)
        ]
        await self.queue.join()

        for worker in workers:
            worker.cancel()


async def crack(user=None, password=None, file=None):
    if file is not None:
        with open(file, 'r') as f:
            for line in f:
                if ':' in line:
                    user, password = line.strip().split(':', 1)
                    await crack(user=user, password=password)
                else:
                    print_e(f"Ignoring invalid line: {line.strip()}")
    elif user is not None and password is not None:
        ftp_ids = await FTP_Conns_for_LogInfo(user=user, password=password)
        await Scanner().scan_ftp(ftp_ids, user=user, password=password)
    else:
        raise ValueError("You need to provide user and password or file with user:password pairs")


async def main():
    ARGS = get_args()
    global quite
    quite = ARGS.quite
    try:
        if ARGS.anon_all:
            ftp_ids = asyncio.run(FTP_Conns_after())
            await Scanner().scan_ftp(ftp_ids)
        if ARGS.user and ARGS.password:
            await crack(user=ARGS.user, password=ARGS.password)
        elif ARGS.user or ARGS.password:
            print(f"You need user and password, not only {ARGS.user} {ARGS.password}", file=sys.stderr)
            exit(1)
        elif ARGS.crack:
            await crack(file=f"{CONFIG['ftp_hub']['input_folder']}{CONFIG['ftp_hub']['crack_file']}")
    except KeyboardInterrupt:
        print_e("\n You have interrupted scan_all_async")


if __name__ == '__main__':
    asyncio.run(main())

