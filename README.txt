

 ______ _______  ______     ______   ______  ______  _____  ______  _______  ______
| |       | |   | |  | \   / |      | |     | |  | \  | |  | |  | \   | |   / |
| |----   | |   | |__|_/   '------. | |     | |__| |  | |  | |__|_/   | |   '------.
|_|       |_|   |_|         ____|_/ |_|____ |_|  \_\ _|_|_ |_|        |_|    ____|_/


For advice, feedback, or help, contact me:

Discord: gulemo
Github: https://github.com/Omelug

-----------------------------------------------------------------
DISCLAIMER:

To be honest, I am little bit angry about this project.
Doing somesthing what has been done milion times before wasnt just good idea.
It has some benefits for me, but compared to go scanners it is slow as fuck.
So if you know python, dont fork this, make brutespray wrapper or somesthing...

----------------------------------------------------------------


__________________________________________________________________
INSTALLATION:
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
On Linux:
    sudo apt-get install python3 python3-pip
    make venv_init && source .venv/bin/activate (if you use venv)
    make install
__________________________________________________________________
BEFORE START:
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

requirements: python3, postgresSQL link

1/ create postgresSQL database
2/ Run "python3 ftp_config.py --generate_default" for generating config.json
3/ edit database connection in ftp_secret.py (optionally edit config.json)
4/ ftp_hub is main script, good luck

__________________________________________________________________
USAGE:
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

You can use ftp_hub.py to every command, it will be automatic redirected

Dont forget "source .venv/bin/activate" if you are using venv

__________________________________________________________________
ftp_hub.py
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
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

usage: ftp_forest.py [-h] [--anon_all] [-d LIST] [-lvl MAX_LVL] [--quiet] [--user USER] [--password PASSWORD] [--crack]

options:
  -h, --help           show this help message and exit
  --anon_all           --anon_all <n> : Try anonymous: login for all FTP_con,
                       retry older than n days
  --quiet              TODO NOT AVAIBLE NOW | Do not display servers that are unaccessible
                       not responding in the terminal log.
  --user USER          Username
  --password PASSWORD  Password
  --crack              File containing user and password separated by :, default ftp_default_user_pass_list.txt






__________________________________________________________________
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Inspiration and maybe some code parts are from:

https://github.com/richmas-l/Anonymous-FTP-Scanner/blob/main/ftpscanner.py
https://github.com/Sunlight-Rim/FTPSearcher/tree/main?tab=readme-ov-file
https://github.com/rethyxyz/FTPAutomator/blob/main/FTPAutomator.py
https://github.com/tfwcodes/FTP-exploits.git
https://github.com/imnikola/ShodanAnomymousDirs/blob/master/ShodanOpenDirs.py


__________________________________________________________________
TODO
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

1/ control prints, add quite and debug option
2/ make cleaner Key Interrupt, leave live connections save progress (tree are not cut)
3/ progress bar
4/ optimalization, dont need open session during tree scan
5/ add count to login creds
6/ add function to create tree folder with all files from one login:passowrd pair
7/ add regex lists for search for secreat files (sprobably earch on github some scripts)
