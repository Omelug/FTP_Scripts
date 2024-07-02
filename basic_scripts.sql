SELECT "FTP_conn".id, "FTP_conn".ip, "FTP_conn".port,ftp_login.file_path, "FTP_conn".product, "FTP_conn".version, "FTP_conn".os_type, login_info.user, login_info.password
FROM "FTP_conn"
JOIN ftp_login ON "FTP_conn".id = ftp_login.ftp_id
JOIN login_info ON ftp_login.login_id = login_info.id
WHERE "FTP_conn".status = 'connected';