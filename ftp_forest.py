import hashlib

import yappi
from line_profiler import LineProfiler
profile = LineProfiler()
import argparse
import asyncio
import traceback
from pathlib import Path
import os
import aiofiles
import aioftp
import async_timeout

from ftp_db import *
from ftp_log import *

conf = CONFIG["ftp_forest"]


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--anon_all", action="store_true",
                        help="--anon_all <n> : Try anonymous: login for all FTP_con, retry older than n days")
    parser.add_argument('--user', help='Username')
    parser.add_argument('--password', help='Password')
    parser.add_argument('--crack', action="store_true", help='File containing user and password separated by : ')

    args, unknown = parser.parse_known_args()
    return parser, args


async def print_tree(client, ftp_conn, directory, output_file, indent=0, level=0):
    if level > conf['max_tree_level']:
        return
    try:
        files = await client.list(directory)
        for file in files:
            posix_path, file_info = file
            file_line = ("\t" * indent) + f"{posix_path.stem}{posix_path.suffix}\n"
            await output_file.write(file_line)
            if file_info['type'] == 'dir':
                await print_tree(client, ftp_conn, f"{directory}/{posix_path.name}", output_file, indent + 1, level=1)
    except (aioftp.errors.StatusCodeError, ConnectionRefusedError):
        pass

error_counts = {}
async def handle_error(e, ftp_conn):
    error_type = type(e).__name__
    error_counts[error_type] = error_counts.get(error_type, 0) + 1

    if not conf['quiet']:
        ftp_conn.error = f"{e}"
        ftp_conn.status = "failed"
        print_e(f"{ftp_conn.ip} Error counts: {error_counts}")

async def get_file_hash(file_path):
    BUF_SIZE = 8192  # Read file in chunks
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()

async def connect_async(ftp_id: int, user, password, login_info_id=None):
    success = False
    new_file_path = None

    async with get_session() as session:
        ftp_conn: FTPConn = await ftp_by_id(ftp_id, session)

    try:
        client = aioftp.Client(encoding='iso-8859-2')

        async with async_timeout.timeout(conf['connect_timeout']):
            await client.connect(ftp_conn.ip, ftp_conn.port)
            await client.login(user, password)
            ftp_conn.status = "connected"
            success = True
            print_ok(f"{ftp_conn} connected")

        output_folder = Path(f"./output/tree/")
        output_folder.mkdir(parents=True, exist_ok=True)
        file = f"tmp_{ftp_conn.ip}_{ftp_conn.port}.txt"
        output_file_path = f"{output_folder}/{file}"
        new_file_path = "failed"

        try:
            async with async_timeout.timeout(conf['forest_timeout']):
                async with aiofiles.open(output_file_path, mode="w") as output_file:
                    await print_tree(client, ftp_conn, "/", output_file)
        except (TimeoutError, ConnectionResetError) as e:
            print_e(f"{e.__class__.__name__}")
            await output_file.write(f"{e.__class__.__name__}")
        except ValueError:
            print_e(f"{ftp_conn} ValueError (probably stupid encoding)")
            await output_file.write("ValueError: stupid encoding")
        except Exception as e:
            print(f"Tree Error: {e.__class__.__name__}")
            traceback.print_exc()
        finally:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, os.sync)
            file_hash = await get_file_hash(output_file_path)

            new_file_path = os.path.dirname(output_file_path) + '/' + file_hash + '.txt'
            if os.path.exists(new_file_path):
                os.remove(output_file_path)
                print_ok(f"{ftp_conn} tree detected - {new_file_path}")
            else:
                os.rename(output_file_path, new_file_path)
                print_s(f"{ftp_conn} new tree - {new_file_path}")
    except Exception as e:
        await handle_error(e, ftp_conn)
    finally:
        ftp_conn.check_date = datetime.now()
        try:
            async with get_session() as session:
                await add_login(
                    ftp_conn.id,
                    session,
                    user, password,
                    success=success,
                    login_info_id=login_info_id,
                    file_path=new_file_path
                )
                session.add(ftp_conn)
                await session.commit()
        except Exception as db_e:
            traceback.print_exc()
            print_e(f"Database error: {db_e}")


class Scanner:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def worker(self, login_info_id=None):
        try:
            while True:
                try:
                    ftp_id, user, password = await self.queue.get()
                    await connect_async(ftp_id, user, password, login_info_id=login_info_id)
                    self.queue.task_done()
                except Exception as e:
                    print_e(f"Error processing task {e}")
        except KeyboardInterrupt:
            print_e("\n You have interrupted scan_all_async")

    async def scan_ftp(self, ftp_ids=None, user="anonymous", password="", max_workers=conf['max_workers']):
        if ftp_ids is None:
            ftp_ids = []
        print_ok(f"Scan {user}:{password}")
        async with get_session() as session:
            login_info_id = await create_login(session, user, password)

        for ftp_id in ftp_ids:
            await self.queue.put((ftp_id, user, password))

        workers = [
            asyncio.create_task(self.worker(login_info_id=login_info_id))
            for _ in range(max_workers)
        ]
        try:
            await self.queue.join()
        except Exception as e:
            print_e(f"An error occurred: {e}")
        finally:
            for worker in workers:
                worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            print_ok("All workers have been cancelled.")


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
    yappi.set_clock_type("cpu")
    yappi.start()
    parser, ARGS = get_args()
    try:
        if ARGS.anon_all:
            ftp_ids = await FTP_Conns_after()
            await Scanner().scan_ftp(ftp_ids)
        if ARGS.user and ARGS.password:
            await crack(user=ARGS.user, password=ARGS.password)
        elif ARGS.user or ARGS.password:
            print(f"You need user and password, not only {ARGS.user} {ARGS.password}", file=sys.stderr)
            return False
        elif ARGS.crack:
            await crack(file=f"{CONFIG['ftp_hub']['input_folder']}{CONFIG['ftp_hub']['crack_file']}")
        return any((ARGS.anon_all, ARGS.user, ARGS.password, ARGS.crack))
    except KeyboardInterrupt:
        yappi.stop()
        threads = yappi.get_thread_stats()
        for thread in threads:
            print(
                "Function stats for (%s) (%d)" % (thread.name, thread.id)
            )  # it is the Thread.__class__.__name__
            yappi.get_func_stats(ctx_id=thread.id).print_all()

        print_e("\n You have interrupted ftp_forest")


if __name__ == '__main__':
    asyncio.run(main())

