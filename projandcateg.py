import requests
import ollama
from dotenv import load_dotenv
import os

# ===== ENV YÜKLE =====
load_dotenv()

BASE_URL = os.getenv("REDMINE_BASE_URL")
ISSUES_URL = f"{BASE_URL}/issues.json"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

HEADERS = {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": os.getenv("REDMINE_API_KEY"),
}

# ===== REDMINE'DAN PROJELERİ ÇEK =====
def get_projects():
    response = requests.get(f"{BASE_URL}/projects.json", headers=HEADERS)
    if response.status_code != 200:
        print("Projeler çekilemedi.")
        return []
    return response.json().get("projects", [])

# ===== PROJEYE AİT KATEGORİLERİ ÇEK =====
def get_categories(project_id):
    url = f"{BASE_URL}/projects/{project_id}/issue_categories.json"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print("Kategoriler çekilemedi.")
        return []
    return response.json().get("issue_categories", [])

# ===== REDMINE'DAN KATEGORİSİ OLMAYAN ISSUE'YU ÇEK =====
def get_uncategorized_issue():
    response = requests.get(ISSUES_URL, headers=HEADERS)
    if response.status_code != 200:
        print("Issue'lar çekilemedi.")
        return None
    issues = response.json().get("issues", [])
    issues_without_category = [issue for issue in issues if not issue.get("category")]
    if not issues_without_category:
        print("Kategorisiz issue bulunamadı.")
        return None
    return issues_without_category[-1]  # sonuncusu

# ===== OLLAMA PROMPT TAHMİNİ YAP =====
def classify_with_ollama(title, description, options, konu_adi="kategori"):
    prompt = f"""
Bir issue başlığı ve açıklaması vereceğim. Aşağıdaki {konu_adi}lerden sadece tam ve tek bir {konu_adi} adı olarak cevap ver.

{konu_adi.capitalize()}ler:
{chr(10).join(['- ' + c for c in options])}

Başlık: {title}
Açıklama: {description}

İçeriği iyice oku ve anla.
Cevap sadece {konu_adi} adlarından biri olsun ama tam olarak kategori adını vermeni istiyorum benim bu kategorilerimden biriyle uyuşması laızm. Açıklama yapma.
"""
    messages = [{"role": "user", "content": prompt}]
    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        raw = response['message']['content'].strip()
        print(f"{konu_adi.capitalize()} tahmini (ham):", raw)
        return raw.splitlines()[-1].strip()
    except Exception as e:
        print(f"Ollama API hatası ({konu_adi}):", e)
        return None

def classify_project_with_ollama(title, description, project_options):
    prompt = f"""
Bir issue başlığı ve açıklaması vereceğim. Aşağıdaki projelerden sadece tam ve tek bir proje adı olarak cevap ver.

Projeler:
{chr(10).join(['- ' + p for p in project_options])}

Başlık: {title}
Açıklama: {description}

Cevap sadece proje adlarından biri olsun adını birebir aynı ver. Açıklama yapma.
"""
    messages = [{"role": "user", "content": prompt}]
    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        raw = response['message']['content'].strip()
        print("Proje tahmini (ham):", raw)
        return raw.splitlines()[-1].strip()
    except Exception as e:
        print("Ollama API hatası (proje):", e)
        return None

# ===== PROJE DEĞİŞTİR =====
def update_issue_project(issue_id, project_id):
    url = f"{BASE_URL}/issues/{issue_id}.json"
    payload = {"issue": {"project_id": project_id}}
    res = requests.put(url, json=payload, headers=HEADERS)
    return res.status_code in (200, 204)

# ===== KATEGORİ GÜNCELLE =====
def update_issue_category(issue_id, category_id, assigned_to_id=None):
    url = f"{BASE_URL}/issues/{issue_id}.json"
    issue_data = {"category_id": category_id}
    if assigned_to_id:
        issue_data["assigned_to_id"] = assigned_to_id
        print("Kişi Ataması Yapıldı")
    res = requests.put(url, json={"issue": issue_data}, headers=HEADERS)
    if res.status_code in (200, 204):
        print(f"Issue #{issue_id} başarıyla güncellendi.")
    else:
        print("Güncelleme hatası:", res.status_code, res.text)

# ===== ANA AKIŞ =====
def main():
    issue = get_uncategorized_issue()
    if not issue:
        return

    issue_id = issue["id"]
    title = issue.get("subject", "")
    description = issue.get("description", "")
    current_project_name = issue["project"]["name"]

    print(f"\n📝 Issue #{issue_id}: {title} (Şu anki proje: {current_project_name})")

    projects = get_projects()
    if not projects:
        return
    project_names = [p["name"] for p in projects]

    predicted_project_name = classify_project_with_ollama(title, description, project_names)
    if predicted_project_name is None:
        print("Proje tahmini alınamadı.")
        return
    predicted_project = next((p for p in projects if p["name"].lower() == predicted_project_name.lower()), None)
    if not predicted_project:
        print("Tahmin edilen proje bulunamadı.")
        return
    predicted_project_id = predicted_project["id"]

    if predicted_project_name != current_project_name:
        print(f"📦 Issue projeyi değiştiriyor: {current_project_name} ➝ {predicted_project_name}")
        if not update_issue_project(issue_id, predicted_project_id):
            print("Proje güncellenemedi.")
            return

    categories = get_categories(predicted_project_id)
    if not categories:
        print("Kategori listesi boş.")
        return
    category_names = [cat["name"] for cat in categories]

    predicted_category_name = classify_with_ollama(title, description, category_names, "kategori")
    if predicted_category_name is None:
        print("Kategori tahmini alınamadı.")
        return
    matched_cat = next((c for c in categories if c["name"].lower() == predicted_category_name.lower()), None)
    if not matched_cat:
        print(f"Kategori '{predicted_category_name}' bulunamadı.")
        return

    print(f"🏷️  Kategori belirlendi: {matched_cat['name']} (ID: {matched_cat['id']})")

    assigned_to_id = matched_cat.get("assigned_to", {}).get("id")
    update_issue_category(issue_id, matched_cat["id"], assigned_to_id)

# ===== ÇALIŞTIR =====
if __name__ == "__main__":
    main()
