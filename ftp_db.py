import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import asyncpg
import masscan
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy import DateTime, ForeignKey, Table
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import insert
from ftp_config import CONFIG
from ftp_log import *
conf = CONFIG["ftp_db"]

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)

DATABASE_URL_ASYNC = f"sqlite+aiosqlite:///{conf['db_path']}"

engine = create_async_engine(DATABASE_URL_ASYNC, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(
    class_=AsyncSession,
    bind=engine,
    expire_on_commit=False,
    autoflush=False
)
"""DATABASE_URL_ASYNC = "postgresql+asyncpg://postgres:heslo@localhost:5432/ftp_hub"

engine = create_async_engine(DATABASE_URL_ASYNC, echo=False)

SessionLocal = sessionmaker(
    class_=AsyncSession,
    bind=engine,
    expire_on_commit=False,
    autoflush=False
)"""



class Base(DeclarativeBase):
    pass


async def get_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()


@asynccontextmanager
async def get_session():
    async for db in get_db():
        yield db


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
    if not login_info:
        print_s(f"Created new user {user}:{password}")
        login_info = LoginInfo(user=user, password=password)
        session.add(login_info)
    return login_info.id

async def create_ftp_login(session, ftp_id, login_info_id, success):
    result = await session.execute(
        select(ftp_login)
        .where(ftp_login.c.ftp_id == ftp_id)
        .where(ftp_login.c.login_id == login_info_id)
    )
    existing_entry = result.scalar_one_or_none()

    if existing_entry:
        await session.execute(
            ftp_login.update()
            .where(ftp_login.c.ftp_id == ftp_id)
            .where(ftp_login.c.login_id == login_info_id)
            .values(success=success)
        )
    else:
        await session.execute(
            insert(ftp_login)
            .values(ftp_id=ftp_id, login_id=login_info_id, success=success)
        )



class FTPConn(Base):
    __tablename__ = 'FTP_conn'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    status = Column(Integer, nullable=True)
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
    results = await session.execute(select(FTPConn).filter(FTPConn.id == ftp_id))
    return results.scalars().first()


async def add_login(ftp_id: int, session: AsyncSession, user: str, password: str, success: bool = False):
    login_info_id = await create_login(session, user, password)
    await create_ftp_login(session, ftp_id, login_info_id, success)

connect_hydra_login = Table('connect_hydra_login', Base.metadata,
                            Column('hydra_id', Integer, ForeignKey('hydra_run.id'), primary_key=True),
                            Column('login_info_id', Integer, ForeignKey('login_info.id'), primary_key=True)
                            )


class LoginInfo(Base):
    __tablename__ = 'login_info'

    id = Column(Integer, primary_key=True, autoincrement=True)

    user = Column(String, nullable=True)
    password = Column(String, nullable=True)


    ftps = relationship('FTPConn', secondary=ftp_login, back_populates='logins', lazy="selectin")
    hydra_conns = relationship('HydraRun', secondary=connect_hydra_login, back_populates='login_infos', lazy="selectin")

    def __str__(self):
        return f"{self.user}:{self.password}"


class HydraRun(Base):
    __tablename__ = 'hydra_run'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ftp_id = Column(Integer, ForeignKey('FTP_conn.id'), nullable=False)
    combo_list = Column(String, nullable=True)
    user_file = Column(String, nullable=True)
    pass_file = Column(String, nullable=True)

    save_date = Column(DateTime, nullable=True)
    login_infos = relationship('LoginInfo', secondary=connect_hydra_login, back_populates='hydra_conns',
                               lazy="selectin")


async def FTP_Conns_after(after_days=7):
    async with get_session() as session:
        seven_days_ago = datetime.now() - timedelta(days=after_days)
        result = await session.execute(
            select(FTPConn).filter(or_(
                FTPConn.check_date < seven_days_ago,
                FTPConn.check_date == None
            )).order_by(FTPConn.check_date)
        )
        return result.scalars().all()


async def FTP_Conns_failed():
    async with get_session() as session:
        result = await session.execute(
            select(FTPConn).filter(or_(
                FTPConn.status == "open",
                FTPConn.error.like('%Login Incorrect%')
            )).order_by(FTPConn.check_date)  #.limit(1) #TODO testing
        )
        return result.scalars().all()


async def FTP_Conns_for_LogInfo(user, password):
    async with get_session() as session:
        query = (
            session.query(FTPConn)
            .filter(
                ~FTPConn.id.in_(
                    session.query(ftp_login.c.ftp_conn_id)
                    .join(LoginInfo, ftp_login.c.login_info_id == LoginInfo.id)
                    .filter(LoginInfo.user == user, LoginInfo.password == password)
                )
            )
        ).limit(1) #TODO testing

        result = query.all()
        return result
