Inspiraci a kousky kódu jsem bral z těchto míst.

https://github.com/richmas-l/Anonymous-FTP-Scanner/blob/main/ftpscanner.py
https://github.com/Sunlight-Rim/FTPSearcher/tree/main?tab=readme-ov-file
https://github.com/rethyxyz/FTPAutomator/blob/main/FTPAutomator.py
https://github.com/tfwcodes/FTP-exploits.git

Pokud máte Shodan API:
https://github.com/imnikola/ShodanAnomymousDirs/blob/master/ShodanOpenDirs.py



Použití:

ftp_hub.py:
    - uložení ranges,
    - uložení masscan výsledků do databáze
    - anonymmní přihlášení (na to volá ftp)forest)
    - uožení do stromů ./out/tree/

IN: ranges.txt
WORK_WITH: ftp_hub.db
  -h, --help            show this help message and exit
  --save_ranges [SAVE_RANGES]
                        ranges.txt file with ranges in format
                        <ip_start> <ip_stop> <count> <date> company
  --scan_all_ranges [SCAN_ALL_RANGES]
                        -scan_all <n> : Scan all RANGE in the
                        database, rescan older than n days, default
                        7
  --last LAST           -anon_all <n> : Try anonymous: login for
                        all FTP_con, retry older than n days,
                        default 7
  --anon_all [ANON_ALL]
                        -anon_all <n> : Try anonymous: login for
                        all FTP_con, retry older than n days,
                        default 7
  --print_ftp_list PRINT_FTP_LIST
                        Print ftp list to stdout
