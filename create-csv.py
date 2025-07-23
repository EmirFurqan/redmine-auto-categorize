import requests
from dotenv import load_dotenv
import os
import pandas as pd
import time  # isteğe bağlı: aşırı istek atmayı engellemek için

# Ortam değişkenlerini yükle
load_dotenv()

BASE_URL = os.getenv("REDMINE_BASE_URL")
HEADERS = {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": os.getenv("REDMINE_API_KEY"),
}

def get_all_issues(limit=100):
    all_issues = []
    offset = 0

    while True:
        print(f"Issues çekiliyor: offset={offset}")
        response = requests.get(f"{BASE_URL}/issues.json?offset={offset}&limit={limit}", headers=HEADERS)

        if response.status_code != 200:
            print(f"Issue verileri alınamadı. Hata kodu: {response.status_code}")
            break

        data = response.json()
        issues = data.get("issues", [])
        total_count = data.get("total_count", 0)

        if not issues:
            break

        all_issues.extend(issues)
        offset += limit

        # Eğer tüm veriler çekildiyse döngüden çık
        if offset >= total_count:
            break

        time.sleep(0.5)  # isteğe bağlı: sunucuyu yormamak için küçük bir bekleme süresi

    print(f"Toplam çekilen issue sayısı: {len(all_issues)}")
    return all_issues

def export_to_csv(issues, filename="veri.csv"):
    rows = []
    for issue in issues:
        title = issue.get("subject", "")
        description = issue.get("description", "")
        title_description = f"{title}\n\n{description}"

        project = issue.get("project", {}).get("name", "")

        rows.append([title_description, project])

    df = pd.DataFrame(rows, columns=["text", "label"])
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"CSV dosyası oluşturuldu: {filename}")

def main():
    issues = get_all_issues()
    export_to_csv(issues)

if __name__ == "__main__":
    main()
