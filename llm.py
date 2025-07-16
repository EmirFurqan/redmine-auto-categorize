import requests
import ollama

# ===== KONFIGÜRASYON =====
BASE_URL = "https://redmine-on-render.onrender.com"
PROJECT_ID = 1
ISSUES_URL = f"{BASE_URL}/issues.json"
CATEGORIES_URL = f"{BASE_URL}/projects/{PROJECT_ID}/issue_categories.json"
PUT_BASE_URL = BASE_URL

HEADERS = {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": "b6d5809602dc0844cfecd36248469bc58069a8bd",
}

# ===== REDMINE'DAN KATEGORİLERİ ÇEK =====
def get_categories():
    response = requests.get(CATEGORIES_URL, headers=HEADERS)
    if response.status_code != 200:
        print("Kategoriler çekilemedi.")
        return []
    data = response.json()
    return data.get("issue_categories", [])

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

# ===== OLLAMA İLE KATEGORİ TAHMİNİ =====
def classify_with_ollama(title, description, categories):
    prompt = f"""
Bir issue başlığı ve açıklaması vereceğim. Aşağıdaki kategorilerden sadece tam ve tek bir kategori adı olarak cevap ver.

Kategoriler:
{chr(10).join(['- ' + c for c in categories])}

Başlık: {title}
Açıklama: {description}

Cevap sadece uygun kategorinin adı olsun. Başka açıklama yapma ve kategorilerden birini direkt olarak söyle bana sadece kategorilerimden birini cevap olarak ver.
"""

    messages = [{"role": "user", "content": prompt}]

    def temizle_ve_kategori_cek(cevap):
        # <think> ve </think> taglarını temizle
        cevap = cevap.replace('<think>', '').replace('</think>', '').strip()
        # Satır satır böl
        satirlar = cevap.split('\n')
        # Boş olmayan satırları al
        satirlar = [s.strip() for s in satirlar if s.strip()]
        if not satirlar:
            return ''
        # Son satır kategori olabilir
        kategori = satirlar[-1]
        return kategori

    try:
        response = ollama.chat(model='deepseek-r1', messages=messages)
        raw_cevap = response['message']['content'].strip()
        print("Raw model cevabı:", raw_cevap)
        kategori = temizle_ve_kategori_cek(raw_cevap)
        print("Temizlenmiş model cevabı:", kategori)
        return kategori
    except Exception as e:
        print("Ollama API hatası:", e)
        return None




# ===== REDMINE ISSUE KATEGORİSİNİ GÜNCELLE =====
def update_issue_category(issue_id, category_id, assigned_to_id=None):
    update_url = f"{PUT_BASE_URL}/issues/{issue_id}.json"
    issue_data = {
        "category_id": category_id
    }
    if assigned_to_id is not None:
        issue_data["assigned_to_id"] = assigned_to_id

    payload = {
        "issue": issue_data
    }

    put_response = requests.put(update_url, json=payload, headers=HEADERS)
    if put_response.status_code in (200, 204):
        print(f"Issue #{issue_id} başarıyla güncellendi.")
    else:
        print(f"PUT isteği başarısız oldu: {put_response.status_code}")
        print(put_response.text)


# ===== ANA AKIŞ =====
def main():
    issue = get_uncategorized_issue()
    if not issue:
        return

    issue_id = issue["id"]
    title = issue.get("subject", "")
    description = issue.get("description", "")

    print(f"Kategorisiz Issue #{issue_id}: {title}")

    categories = get_categories()
    if not categories:
        print("Kategori listesi boş.")
        return
    category_names = [cat["name"] for cat in categories]

    # Ollama ile sınıflandırma
    predicted_category = classify_with_ollama(title, description, category_names)
    if not predicted_category:
        print("Kategori tahmin edilemedi.")
        return

    # Tahmin edilen kategoriyi listede bul
    matched_category = None
    for cat in categories:
        if cat["name"].lower() == predicted_category.lower():
            matched_category = cat
            break

    if not matched_category:
        print(f"Tahmin edilen kategori '{predicted_category}' kategoriler arasında bulunamadı.")
        return

    print(f"Tahmin edilen kategori: {matched_category['name']} (ID: {matched_category['id']})")

    # Eğer kategoride assigned_to varsa al
    assigned_to_id = None
    if matched_category.get("assigned_to") and "id" in matched_category["assigned_to"]:
        assigned_to_id = matched_category["assigned_to"]["id"]

    # Redmine issue'yu güncelle (assigned_to_id opsiyonel)
    update_issue_category(issue_id, matched_category["id"], assigned_to_id)


if __name__ == "__main__":
    main()
