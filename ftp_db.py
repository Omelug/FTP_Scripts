import logging

import masscan
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from datetime import datetime, timedelta
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.future import select

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


DATABASE_URL_ASYNC = "sqlite+aiosqlite:///ftp_hub.db"
DATABASE_URL_SYNC = "sqlite:///ftp_hub.db"

async_engine = create_async_engine(DATABASE_URL_ASYNC, echo=False, future=True, connect_args={"timeout": 30})
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

sync_engine = create_engine(DATABASE_URL_SYNC, echo=False)
Session = sessionmaker(bind=sync_engine)

Base = declarative_base()
Base.metadata.create_all(sync_engine)


class Range(Base):
    __tablename__ = 'RANGE'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_a = Column(String, nullable=False)
    ip_b = Column(String, nullable=False)
    save_date = Column(DateTime, nullable=True)

    def scan(self, session, port):
        print(f"Scannning of  range {self.ip_a}-{self.ip_b} started | {datetime.now()}")
        mas = masscan.PortScanner()
        try:
            mas.scan(f"{self.ip_a}-{self.ip_b}", ports=f"{port}", arguments='--max-rate 2500', sudo=True)
        except Exception as e:
            logging.error(f" masscan error  {e}")
            exit(42)
        mas_res = json.loads(mas.scan_result)
        print(f"Scannning of  range {self.ip_a}-{self.ip_b} finished | {datetime.now()}")
        for ip, result in mas_res["scan"].items():
            for port_info in result:
                port = port_info['port']
                status = port_info['status']
                existing_record = session.query(FTPConn).filter_by(ip=ip, port=port).first()
                if existing_record is None:
                    new_record = FTPConn(ip=ip, port=port, status=status, scan_date=datetime.now())
                    session.add(new_record)
                else:
                    existing_record.status = status
                    existing_record.scan_date = datetime.now()
                session.commit()
        self.save_date = datetime.now()
        session.commit()
        print(f"Saving of  range {self.ip_a}-{self.ip_b} finished | {datetime.now()}")

class FTPConn(Base):
    __tablename__ = 'FTP_conn'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    status = Column(Integer, nullable=False)
    scan_date = Column(DateTime, nullable=True, default=datetime.now)

    check_date = Column(DateTime, nullable=True)
    error = Column(String, nullable=True)
    path = Column(String, nullable=True)

    user = Column(String, nullable=True)
    password = Column(String, nullable=True)

    def tuple(self):
        return self.ip, self.port

    def __str__(self):
        return f"{self.ip}:{self.port}"
