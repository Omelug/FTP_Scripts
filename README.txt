
For advice, feedback, or help, contact me:

Discord: gulemo
Github: https://github.com/Omelug

__________________________________________________________________
BEFORE START:
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

1/ create postgresSQL database
2/ Run "python3 ftp_config.py --generate_default" for generating config.json
3/ edit database connection in ftp_secret.py (optionally edit config.json)
4/ ftp_hub is main script, good luck

__________________________________________________________________
USAGE:

You can use ftp_hub.py to every command, it will be automatic redirected
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

ftp_hub.py

usage: Example: save_ranges -> scan_all_ranges -> check_all_ftp_anon | scan_all_versions

options:
      -h, --help            show this help message and exit
      --save_ranges         ranges.txt file with ranges in format <ip_start> <ip_stop> <count> <date> company
      --scan_all_ranges     --scan_all: Scan all RANGE in the database, rescan older than old_delay_days
      --scan_all_versions   --scan_all_versions : Scan version of all connected
      --print_ftp_list      Print ftp list to stdout

__________________________________________________________________
ftp_forest.py
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
usage: ftp_forest.py [-h] [--anon_all] [-d LIST] [-lvl MAX_LVL] [--quite] [--user USER] [--password PASSWORD] [--crack]

options:
  -h, --help           show this help message and exit
  --anon_all           -anon_all <n> : Try anonymous: login for all FTP_con, retry older than n days
  -d LIST              Path to database file (postgresql+asyncpg://postgres:velmi_silne_heslo@localhost:5432/ftp_hub by default).
  -lvl MAX_LVL         Set up the maximum file tree level on FTP servers.
  --quite              Do not display servers that are not responding in the terminal log.
  --user USER          Username
  --password PASSWORD  Password
  --crack              File containing user and password separated by

__________________________________________________________________
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Inspiration and maybe some code parts are from:

https://github.com/richmas-l/Anonymous-FTP-Scanner/blob/main/ftpscanner.py
https://github.com/Sunlight-Rim/FTPSearcher/tree/main?tab=readme-ov-file
https://github.com/rethyxyz/FTPAutomator/blob/main/FTPAutomator.py
https://github.com/tfwcodes/FTP-exploits.git
https://github.com/imnikola/ShodanAnomymousDirs/blob/master/ShodanOpenDirs.py

