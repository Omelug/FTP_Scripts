import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import masscan
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy import DateTime, ForeignKey, Table
from sqlalchemy import not_, exists, and_
from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import aliased
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from ftp_log import *

conf = CONFIG["ftp_db"]

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)

DATABASE_URL_ASYNC = "postgresql+asyncpg://postgres:heslo@localhost:5432/ftp_hub"


engine = create_async_engine(
        DATABASE_URL_ASYNC,
        echo=False,
        poolclass=NullPool
    )

SessionLocal = sessionmaker(
        class_=AsyncSession,
        bind=engine,
        expire_on_commit=False,
        autoflush=False
    )


@asynccontextmanager
async def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        await session.close()

Base = declarative_base()


class Range(Base):
    __tablename__ = 'RANGE'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_a = Column(String, nullable=False)
    ip_b = Column(String, nullable=False)
    save_date = Column(DateTime, nullable=True)

    async def scan(self, session, port):
        print(f"Scannning of  range {self.ip_a}-{self.ip_b} started | {datetime.now()}")
        mas = masscan.PortScanner()
        try:
            mas.scan(f"{self.ip_a}-{self.ip_b}", ports=f"{port}", arguments='--max-rate 2500', sudo=True)
        except Exception as e:
            logging.error(f" masscan error  {e}")
            return
        mas_res = json.loads(mas.scan_result)
        print(f"Scannning of  range {self.ip_a}-{self.ip_b} finished | {datetime.now()}")
        #print(mas_res["scan"])
        for ip, result in mas_res["scan"].items():
            for port_info in result:
                port = port_info['port']
                status = port_info['status']
                result = await session.execute(select(FTPConn).filter_by(ip=ip, port=port))
                existing_record = result.scalars().first()
                if existing_record is None:
                    new_record = FTPConn(ip=ip, port=port, status=status, scan_date=datetime.now())
                    session.add(new_record)
                else:
                    existing_record.status = status
                    existing_record.scan_date = datetime.now()
                    session.add(existing_record)
                await session.commit()
        self.save_date = datetime.now()
        await session.commit()
        print(f"Saving of  range {self.ip_a}-{self.ip_b} finished | {datetime.now()}")


ftp_login = Table('ftp_login', Base.metadata,
                  Column('ftp_id', Integer, ForeignKey('FTP_conn.id'), primary_key=True),
                  Column('login_id', Integer, ForeignKey('login_info.id'), primary_key=True),
                  Column('modified_at', DateTime, default=datetime.now(), onupdate=datetime.now()),
                  Column('success', Boolean),
                  )


async def create_login(session,user, password):
    result = await session.execute(
        select(LoginInfo).filter_by(user=user, password=password)
    )
    login_info = result.scalars().first()
    if login_info:
        return login_info.id
    if not login_info:
        print_s(f"Created new user {user}:{password}")
        login_info = LoginInfo(user=user, password=password)
        session.add(login_info)
        await session.commit()
        return login_info.id

async def create_ftp_login(session: AsyncSession, ftp_id: int, login_info_id: int, success: bool):
    stmt = pg_insert(ftp_login).values(
        ftp_id=ftp_id,
        login_id=login_info_id,
        success=success,
        modified_at=datetime.now()
    ).on_conflict_do_update(
        index_elements=['ftp_id', 'login_id'],
        set_=dict(success=success, modified_at=datetime.now())
    )

    await session.execute(stmt)

class FTPConn(Base):
    __tablename__ = 'FTP_conn'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    status = Column(String, nullable=True)
    scan_date = Column(DateTime, nullable=True, default=datetime.now)

    check_date = Column(DateTime, nullable=True)
    error = Column(String, nullable=True)
    path = Column(String, nullable=True)

    logins = relationship('LoginInfo', secondary=ftp_login, back_populates='ftps', lazy="selectin")

    def tuple(self):
        return self.ip, self.port

    def __str__(self):
        return f"{self.ip}:{self.port}"


async def ftp_by_id(ftp_id: int, session)-> FTPConn:
    result = await session.execute(
        select(FTPConn).filter_by(id=ftp_id)
    )
    return result.scalar_one_or_none()


async def add_login(ftp_id: int, session: AsyncSession, user: str, password: str, success: bool = False,login_info_id=None ):
    if login_info_id is None:
        login_info_id = await create_login(session, user, password)
    await create_ftp_login(session, ftp_id, login_info_id, success)


class LoginInfo(Base):
    __tablename__ = 'login_info'

    id = Column(Integer, primary_key=True, autoincrement=True)

    user = Column(String, nullable=True)
    password = Column(String, nullable=True)


    ftps = relationship('FTPConn', secondary=ftp_login, back_populates='logins', lazy="selectin")

    def __str__(self):
        return f"{self.user}:{self.password}"

async def FTP_Conns_after(after_days=CONFIG['ftp_hub']["old_delay_days"]):
    async with get_session() as session:
        seven_days_ago = datetime.now() - timedelta(days=after_days)
        result = await session.execute(
            select(FTPConn.id).filter(
                or_(
                    FTPConn.check_date < seven_days_ago,
                    FTPConn.check_date == None
                )
            ).order_by(FTPConn.check_date)
        )
        return result.scalars().all()

async def FTP_Conns_for_LogInfo(user:str, password:str):
    LoginInfoAlias = aliased(LoginInfo)
    ftp_login_subquery = select(1).select_from(
        ftp_login.join(LoginInfoAlias, ftp_login.c.login_id == LoginInfoAlias.id)).where(
        and_(
            FTPConn.id == ftp_login.c.ftp_id,
            LoginInfoAlias.user == user,
            LoginInfoAlias.password == password
        )
    )
    async with get_session() as session:
        result = await session.execute(
            select(FTPConn.id)
            .where(
                not_(exists(ftp_login_subquery))
            )
        )
        return result.scalars().all()