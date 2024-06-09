## This script https://github.com/Sunlight-Rim/FTPSearcher/tree/main?tab=readme-ov-file
# but without useless printing shit and with useful database shit
# https://github.com/rethyxyz/FTPAutomator/blob/main/FTPAutomator.py
import ast
import asyncio
import ftplib
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
import aioftp
from sqlalchemy import or_
import sys
import threading
import async_timeout
from socket import gaierror
from ftplib import FTP, error_perm
from colorama import Fore, Style, init
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import ftp_db
from ftp_db import *
import argparse
from asyncio import Queue


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
    return parser.parse_args()


def print_e(string, condition=True):
    print(Fore.RED + string + Fore.RESET, file=sys.stderr) if condition else None


def print_d(msg):
    print(Fore.GREEN + msg + Fore.RESET, file=sys.stderr)


def print_ok(msg):
    print(Fore.YELLOW + Style.BRIGHT + msg + Fore.RESET, file=sys.stderr)


def print_s(msg):
    print(Fore.YELLOW + Style.BRIGHT + msg + Fore.RESET, file=sys.stderr)


def connect_and_update(session, ftp_conn: FTPConn, user, password):
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
        ftp_conn.status = f"failedd"
        print_e(f"{ftp_conn} failed")
    finally:
        ftp_conn.check_date = datetime.now()
        try:
            session.commit()
        except Exception as db_e:
            session.rollback()
            print_e(f"Database error: {db_e}")


def scan_all(user="anonymous", password=""):
    with Session() as session:
        try:
            result = session.execute(select(FTPConn))
            ftp_conns = result.scalars().all()
            for ftp_conn in ftp_conns:
                connect_and_update(session, ftp_conn, user, password)
        except KeyboardInterrupt:
            print_e("\nYou have interrupted the FTP Searcher.")
        except NameError:
            pass

async def print_tree(client, ftp_conn, directory, output_file, indent=0):
    try:
        async with async_timeout.timeout(15):
            files = await client.list(directory)
            for file in files:
                posix_path, file_info = file
                await output_file.write(f"{ftp_conn} {'\t' * indent} {posix_path.stem}{posix_path.suffix}\n")
                if file_info['type'] == 'dir':
                    await print_tree(client, ftp_conn, f"{directory}/{posix_path.name}", output_file, indent + 1)
    except asyncio.TimeoutError:
        print(f"Timeout while listing directory {directory} for {ftp_conn.ip}")

async def connect_async(session, ftp_conn: FTPConn, user, password):
    try:
        client = aioftp.Client(encoding='iso-8859-2')

        async with async_timeout.timeout(60):
            await client.connect(ftp_conn.ip, ftp_conn.port)
            await client.login(user, password)
            output_folder = Path("./output/tree")
            output_folder.mkdir(parents=True, exist_ok=True)
            output_file_path = output_folder / f"{ftp_conn.ip}_{ftp_conn.port}_{user}_{password}.txt"
            ftp_conn.path = f"{output_file_path}"
            try:
                async with aiofiles.open(output_file_path, mode="w") as output_file:
                    await asyncio.wait_for(print_tree(client, ftp_conn,"/", output_file), timeout=30)
            finally:
                ftp_conn.status = "connected"
                ftp_conn.user = user
                ftp_conn.password = password
    except Exception as e:
        print_e(f"{ftp_conn}: {type(e).__name__}: {e}")
        ftp_conn.error = f"{e}"
        ftp_conn.status = "failed"
    finally:
        ftp_conn.check_date = datetime.now()
        try:
            async with session.begin():
                ftp_local = await session.get(FTPConn, ftp_conn.id)
                if ftp_local:
                    ftp_local.status = ftp_conn.status
                    ftp_local.error = ftp_conn.error
                    ftp_local.user = ftp_conn.user
                    ftp_local.password = ftp_conn.password
                    ftp_local.check_date = datetime.now()
                else:
                    print_e("Entry not found in the database.")
        except Exception as db_e:
            await session.rollback()
            print_e(f"Database error: {db_e}")

async def worker(queue):
    async with get_session() as session:
        while True:
            task = await queue.get()
            if task is None:
                break
            await connect_async(session, *task)
            queue.task_done()


@asynccontextmanager
async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def scan_all_async(user="anonymous", password="", max_workers=500, after_days=7):
    async with AsyncSessionLocal() as session:
        seven_days_ago = datetime.now() - timedelta(days=after_days)
        result = await session.execute(
            select(FTPConn).filter(or_(
                FTPConn.check_date < seven_days_ago,
                FTPConn.check_date == None
            ))
        )
        ftp_conns = result.scalars().all()

    queue = Queue()
    for ftp_conn in ftp_conns:
        await queue.put((ftp_conn, user, password))

    workers = [asyncio.create_task(worker(queue)) for _ in range(max_workers)]
    await queue.join()

    for _ in range(max_workers):
        await queue.put(None)

    await asyncio.gather(*workers, return_exceptions=True)


if __name__ == '__main__':
    ARGS = get_args()
    thread_list = []
    tasks_list = []
    if ARGS.anon_all:
        scan_all()
    if ARGS.anon_all_async:
        try:
            asyncio.run(scan_all_async())
        except KeyboardInterrupt:
            print_e("\n You have interrupted scan_all_async")
