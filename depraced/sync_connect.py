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
            print_e(f"Database error : {db_e}")"""