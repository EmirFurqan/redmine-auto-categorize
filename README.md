# redmine-auto-categorize


# README.md

Bu doküman, `categorizebyid.py` betiğini orta düzey bir geliştirici için hızlıca kurup çalıştıracak şekilde hazırlanmıştır. Temel Python bilgisi varsayılır.

---

## İçindekiler

1. [Ön Koşullar](#ön-koşullar)
2. [Kurulum](#kurulum)
3. [Yapılandırma](#yapilandirma)
4. [Çalıştırma](#calistirma)

## Ön Koşullar

- **Python 3.7+** (varsayılan sanal ortam kullanımı önerilir)
- `requests`, `ollama` kütüphaneleri
- Redmine API erişim bilgileri

> Sanal ortam oluşturma ve aktifleştirme adımları hakkında bilginizin olduğunu varsayıyoruz.

---

## Kurulum

1. Depoyu klonlayın veya ZIP ile indirin.
2. Proje kökünde sanal ortamı oluşturup aktif edin:
   ```bash
   python -m venv venv
   source venv/bin/activate  # veya Windows: venv\Scripts\activate
   ```
3. Gerekli paketleri yükleyin:
   ```bash
   pip install --upgrade pip
   pip install requests ollama
   ```

---

## Yapılandırma

`.env` oluşturun ve içerisindeki temel değişkenleri güncelleyin:

```python
REDMINE_API_KEY= api key
REDMINE_BASE_URL=https://example.redmine.com
OLLAMA_MODEL=deepseek-r1
```

> Alternatif model veya ek parametreler gerektiriyorsa, bu değerleri `ollama.chat()` çağrısında kullanabilirsiniz.

---

## Çalıştırma

Aşağıdaki komut ile betiği başlatın:

```bash
python categorizebyid.py [issue_id]
```

- Betik, issue id olarak verdiğiniz issue’yu çekip başlık ve açıklamayı sınıflandırır.
- Sınıflama sonucunu alıp ilgili issue’nun kategorisini günceller.
