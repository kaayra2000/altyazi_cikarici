# 🎬 Otomatik Ders Videosu İndirici ve Altyazı Oluşturucu

Bu Python paketi, akademik ders videolarını otomatik olarak indirmek ve `faster-whisper` (medium modeli varsayılan olmak üzere) kullanarak `.srt` formatında altyazılarını çıkarmak için tasarlanmıştır.

## Özellikler

- **Çift Modlu Kaynak Desteği**:
  - `dersler.json` dosyası aracılığıyla uzaktaki video linklerini otomatik indirme ve işleme.
  - Yerel bir video dizinini tarayarak toplu altyazı çıkarma.
- **Akıllı Tarih & Klasörleme Mantığı**:
  - Video dosya adından tarih (`dd-mm-yyyy`) ve yıl bilgisini otomatik ayıklar.
  - En eski dersin yılına göre dinamik olarak yıl klasörleri (örn: `2021/`, `2020/`) oluşturur.
  - Tarih bulunamazsa `TARIH_BULUNAMADI/` klasörü altında toplar.
- **Akıllı Sıralama ve Haftalık İndeksleme**:
  - Ders videolarını kronolojik olarak sıralar.
  - Dersler arasında 1 haftadan (7 gün) fazla süre varsa, aradaki hafta sayısı kadar ders numarasını atlayarak isimlendirir (örn: `ders_1.srt`, `ders_2.srt`, `ders_4.srt`).
  - Tarih veya gün bilgisi çıkarılamayan dosyalar için orijinal adını korur ve `.srt` uzantısıyla kaydeder.
- **Performans & İlerleme Takibi**:
  - Video indirmede ve altyazı oluşturmada canlı ilerleme çubuğu (`tqdm`).
  - Zaten oluşturulmuş olan altyazı dosyalarını algılayarak tekrar işlemeyi atlar (zamandan tasarruf sağlar).
- **Temiz ve Modüler Yapı**:
  - SOLID prensiplerine uygun, magic string barındırmayan ve `pyproject.toml` ile paketlenmiş modern altyapı.

---

## Kurulum

Sanal ortamı aktif ettikten sonra projeyi düzenlenebilir (editable) modda kurabilirsiniz:

```bash
# Sanal ortamı etkinleştirin (Linux/macOS)
source venv/bin/activate

# Paket ve bağımlılıklarını kurun
pip install -e .
```

Geliştirici bağımlılıkları (test çalıştırmak için) ile birlikte kurmak isterseniz:

```bash
pip install -e ".[dev]"
```

---

## Kullanım

Paket kurulduktan sonra CLI üzerinden `alt-yazi-cikarici` komutunu doğrudan kullanabilirsiniz:

### 1. `dersler.json` ile İndirme ve Altyazı Çıkarma
Hem videoları indirmek hem de altyazılarını çıkarmak için:
```bash
alt-yazi-cikarici -s dersler.json -o videolar
```

### 2. Sadece Video İndirme
Altyazı işlemini yapmadan sadece videoları indirmek istiyorsanız:
```bash
alt-yazi-cikarici -s dersler.json -o videolar --download-only
```

### 3. Mevcut Videolardan Altyazı Çıkarma
Yerel bir klasördeki videoları tarayıp (indirme yapmadan) altyazılarını çıkarmak için:
```bash
alt-yazi-cikarici -s videolar --transcribe-only
```

### 4. İsimlendirme Stilleri (`--naming-style`)
- `lesson` (Varsayılan): Tarih sırasına göre `ders_1.srt`, `ders_2.srt` şeklinde haftalık atlamalı isimlendirir.
- `original`: Dosya adını değiştirmeden sonuna `.srt` ekler.
- `lesson-lab`: İlk dersin yapıldığı güne kıyasla tam 7'nin katı gün farkına sahip dersleri ana ders (`ders_X.srt`), bu haftalık ana günlerin arasına denk gelen diğer günlerdeki ek/uygulama derslerini ise laboratuvar (`ders_X_lab.srt`) olarak isimlendirir (örneğin; ilk haftadaki ana ders `ders_1.srt`, ara günde yapılan lab ise `ders_1_lab.srt` olur).

```bash
alt-yazi-cikarici -s videolar --transcribe-only --naming-style lesson-lab
```

### 5. CPU / GPU ve Model Seçimi
Varsayılan olarak `medium` modeli CPU üzerinde çalıştırılır. GPU (CUDA) desteğiniz varsa hızı artırmak için cihazı değiştirebilirsiniz:

```bash
alt-yazi-cikarici -s videolar -d cuda -m medium
```

---

## Testleri Çalıştırma

Kod tabanındaki birim testleri (unit tests) çalıştırmak için:

```bash
pytest
```
