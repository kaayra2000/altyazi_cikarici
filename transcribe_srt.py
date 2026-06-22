from faster_whisper import WhisperModel
import time
import os

VIDEO = "BLM4800 - 1_12-03-2021_14-00_12-03-2021_16-50_60869131-a455-4111-baf1-84ab9088c107.mp4"


def fmt(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


baslangic = time.time()

print("Model yükleniyor...")
model = WhisperModel("small", device="cpu", compute_type="int8")

print("Transkripsiyon başlıyor...")
segments, info = model.transcribe(
    VIDEO,
    language="tr",
    vad_filter=True,
    beam_size=5
)

segments = list(segments)

with open("ders.srt", "w", encoding="utf-8") as f:
    for i, seg in enumerate(segments, 1):
        f.write(f"{i}\n")
        f.write(f"{fmt(seg.start)} --> {fmt(seg.end)}\n")
        f.write(f"{seg.text.strip()}\n\n")

bitis = time.time()

gecen_sure = bitis - baslangic
video_suresi = segments[-1].end if segments else 0

print()
print("===== İSTATİSTİK =====")
print(f"Dosya: {os.path.basename(VIDEO)}")
print(f"Video süresi: {video_suresi/60:.2f} dakika")
print(f"İşleme süresi: {gecen_sure/60:.2f} dakika")
print(f"Gerçek zaman oranı: {video_suresi/gecen_sure:.2f}x")
print("======================")
print("Bitti: ders.srt")