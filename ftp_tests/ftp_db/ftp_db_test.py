import asyncio
import os
import sys
import unittest

from sqlalchemy import text

#clean before init
db_path = './ftp_hub.db'
if os.path.exists(db_path):
    os.remove(db_path)

old_path = sys.path.copy()
script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..')
sys.path.append(script_dir)
#import ftp_db

from ftp_db import *

sys.path = old_path


class Init(unittest.IsolatedAsyncioTestCase):

    async def test_sync_connection(self):
        async with get_session() as session:
            result = await session.execute(text("SELECT 1"))
            self.assertIsNotNone(result)

    def test_async_connection(self):
        async def async_test():
            async with get_session() as session:
                result = await session.execute(text("SELECT 1"))
                self.assertIsNotNone(result)

        asyncio.run(async_test())


class TestFTPConn(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ftp_conn = FTPConn(ip="192.168.1.1", port=21)

    def test_tuple_returns_ip_and_port(self):
        self.assertEqual(self.ftp_conn.tuple(), ("192.168.1.1", 21))

    def test_str_returns_formatted_string(self):
        self.assertEqual(str(self.ftp_conn), "192.168.1.1:21")

    async def test_db_add(self):
        #Tohle jsou testy na přidání do databáze,
        # unit testy na knihovnu, což je v podstatě na hovno,
        # budď předělat na integrační nebo zničit
        async with get_session() as session:

            ftp_local = FTPConn(ip="192.168.1.1", port=21)
            session.add(ftp_local)

            #search added ftp before commit
            ftp = await get_ftp_by_ip(ftp_local.ip, session)
            self.assertIsNone(ftp)

            await session.commit()

            ftp = await get_ftp_by_ip(ftp_local.ip, session)
            self.assertIsNotNone(ftp)
            self.assertEqual(ftp.ip, ftp_local.ip)
            self.assertEqual(ftp.port, ftp_local.port)

    async def test_add_login_info(self):
        async with get_session() as session:
            ftp_local = FTPConn(ip="192.168.1.2", port=21)
            session.add(ftp_local)
            await ftp_local.crack_failed_login_info(session, "user", "password")
            await session.commit()

            ftp = await get_ftp_by_ip(ftp_local.ip, session)
            self.assertEqual(ftp.login_infos[0].user, "user")
            self.assertEqual(ftp.login_infos[0].password, "password")


if __name__ == '__main__':
    TestFTPConn().test_db_add()
