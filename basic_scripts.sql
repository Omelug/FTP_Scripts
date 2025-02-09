SELECT "FTP_conn".ip,ftp_login.file_path, "FTP_conn".product, "FTP_conn".version, "FTP_conn".os_type, login_info.user, login_info.password
FROM "FTP_conn"
JOIN ftp_login ON "FTP_conn".id = ftp_login.ftp_id
JOIN login_info ON ftp_login.login_id = login_info.id
WHERE "FTP_conn".status = 'connected';


SELECT "FTP_conn".ip,ftp_login.file_path, login_info.user, login_info.password
FROM "FTP_conn"
JOIN ftp_login ON "FTP_conn".id = ftp_login.ftp_id
JOIN login_info ON ftp_login.login_id = login_info.id
WHERE "FTP_conn".status = 'connected';


SELECT "FTP_conn".ip, ftp_login.file_path, login_info.user, login_info.password
FROM "FTP_conn"
JOIN ftp_login ON "FTP_conn".id = ftp_login.ftp_id
JOIN login_info ON ftp_login.login_id = login_info.id
WHERE ftp_login.success = true
AND public.ftp_login.file_path LIKE '%2e16dc550bd37e9452ce7cc9ea8554ae%';

WITH user_pass_stats AS (
    SELECT
        CONCAT(login_info.user, ':', login_info.password) AS user_pass,
        COUNT(*) AS total_attempts,
        SUM(CASE WHEN ftp_login.success = true THEN 1 ELSE 0 END) AS successful_attempts
    FROM
        "FTP_conn"
    JOIN
        ftp_login ON "FTP_conn".id = ftp_login.ftp_id
    JOIN
        login_info ON ftp_login.login_id = login_info.id
    GROUP BY
        user_pass
)
SELECT
    user_pass,
    total_attempts,
    successful_attempts,
    (successful_attempts * 100.0 / total_attempts) AS success_rate
FROM
    user_pass_stats
ORDER BY
    success_rate DESC;

