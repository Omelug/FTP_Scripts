SELECT "FTP_conn".ip,ftp_login.file_path, "FTP_conn".product, "FTP_conn".version, "FTP_conn".os_type, login_info.user, login_info.password
FROM "FTP_conn"
JOIN ftp_login ON "FTP_conn".id = ftp_login.ftp_id
JOIN login_info ON ftp_login.login_id = login_info.id
WHERE "FTP_conn".status = 'connected';



SELECT "FTP_conn".ip, ftp_login.file_path, login_info.user, login_info.password
FROM "FTP_conn"
JOIN ftp_login ON "FTP_conn".id = ftp_login.ftp_id
JOIN login_info ON ftp_login.login_id = login_info.id
WHERE ftp_login.success = true
AND public.ftp_login.file_path LIKE '%e9d67717a49a78340ad9ee912fc9ea71%';



SELECT "FTP_conn".ip, ftp_login.file_path, ftp_login.file_name, ftp_login.file_size, ftp_login.file_date
FROM "FTP_conn", ftp_login, login_info
WHERE ftp_login.ftp_id = "FTP_conn".ftp_id AND ftp_login.login_id = login_info.id AND ftp_login.success = 1;
