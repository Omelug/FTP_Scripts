import masscan
import json

mas = masscan.PortScanner()
mas.scan(f"45.134.226.157-45.134.226.157", ports="21", arguments='--banners --max-rate 2500', sudo=True)
mas_res = json.loads(mas.scan_result)
print(f"{mas_res}")