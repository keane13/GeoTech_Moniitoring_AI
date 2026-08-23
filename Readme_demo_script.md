# 🎬 GeoTech Monitoring AI — Demo Script (2:00 menit)

**Target Audiens:** Juri Hack2Skill / Snowflake Hackathon
**Platform:** Streamlit in Snowflake (SiS)
**Total Durasi:** 2 menit 00 detik

---

## 🟢 [00:00 – 00:15] OPENING — Overview (15 detik)

**📍 Layar:** Halaman **Overview**

**Narrator:**
> *"GeoTech Monitoring AI adalah sistem pemantauan keselamatan bendungan tailing real-time berbasis Snowflake Cortex AI. Sistem ini mendeteksi sensor drift secara otomatis, menilai risiko geoteknik menggunakan AI, dan mendispatch insinyur lapangan melalui pipeline tiga tahap: Drift Scan → Risk Synthesis → Action Orchestrator."*

**Aksi:**
- Tampilkan halaman **Overview** dengan KPI summary (jumlah fasilitas, sensor, kasus kritis)
- Sorot angka **6 Facilities, 240 Sensors** di sidebar

---

## 🟡 [00:15 – 00:50] MENU DASHBOARD (35 detik)

**📍 Layar:** Halaman **Dashboard**

**Narrator:**
> *"Di Dashboard, operator bisa memantau kondisi real-time seluruh fasilitas. Tersedia filter per tahun dan per fasilitas. Sistem menampilkan distribusi risiko—Critical, High, Medium, Low—dan tren sensor readings per zona.*
>
> *Yang unik adalah fitur **Threshold & Scenario Simulator**: operator bisa menyimulasikan kondisi ekstrem seperti curah hujan lebat, seismic activity, atau musim kemarau, lalu melihat proyeksi berapa hari sebelum threshold dilanggar dan estimasi risk score-nya.*
>
> *Grafik ini menggunakan forecast 180 hari ke depan berdasarkan baseline drift rate masing-masing sensor."*

**Aksi:**
1. Klik tab **Dashboard**
2. Tunjukkan **KPI cards** (jumlah kasus CRITICAL, eskalasi 30 hari)
3. Scroll ke bagian **Threshold & Scenario Simulator**
4. Ubah slider skenario ke **"Extreme Rainfall"** — tunjukkan perubahan **Est. Days to Breach** dan **Risk Score**
5. Sorot chart forecast

---

## 🔴 [00:50 – 01:15] MENU AUDIT TRAIL (25 detik)

**📍 Layar:** Halaman **Case Audit Trail**

**Narrator:**
> *"Setiap kasus yang terdeteksi AI masuk ke Audit Trail dengan detail lengkap: pattern yang dipicu, risk score, severity, dan rekomendasi aksi.*
>
> *Di sinilah fitur **Human-in-the-Loop** bekerja: supervisor dapat melihat kasus yang menunggu review, lalu meng-approve atau reject tindakan yang direkomendasikan AI. Setelah dispatch di-approve, sistem secara otomatis membuat entry baru di INSPECTION_LOG di Snowflake — sepenuhnya auditable dan governance-ready."*

**Aksi:**
1. Klik tab **Case Audit Trail**
2. Filter kasus **CRITICAL / PENDING**
3. Expand salah satu kasus — tampilkan detail llm_rationale dan recommended_action
4. Klik tombol **Approve & Dispatch** — tampilkan konfirmasi sukses
5. Sorot kolom APPROVED_BY dan ACTION_TS

---

## 🔵 [01:15 – 01:37] MENU DETECTION DIAGNOSTICS (22 detik)

**📍 Layar:** Halaman **Detection Diagnostics**

**Narrator:**
> *"Di halaman Diagnostics, kita bisa mengukur akurasi model deteksi secara kuantitatif menggunakan Confusion Matrix dan Precision/Recall. Data ini bersumber dari tabel GROUND_TRUTH_LABELS yang membandingkan pattern yang sengaja disuntikkan ke sensor dengan apa yang berhasil dideteksi oleh pipeline AI.*
>
> *Hasil saat ini menunjukkan Recall 83.3% dan F1-Score 90.9% — cukup untuk operasi early-warning geoteknik."*

**Aksi:**
1. Klik tab **Detection Diagnostics**
2. Sorot **Confusion Matrix** (True Positive, False Negative)
3. Tunjukkan angka **Recall** dan **F1-Score** di metric card
4. Scroll ke **False Negative Analysis** — tunjukkan kasus yang terlewat dan pattern-nya

---

## 💬 [01:37 – 02:00] CHATBOT — 3 Pipeline Query (23 detik)

**📍 Layar:** Halaman **Data Chatbot**

**Narrator:**
> *"Terakhir, chatbot AI ini memungkinkan juri atau operator bertanya langsung tentang pipeline dan data sensor."*

**🔹 Query 1 — Drift Scan** (~7 detik)
> Ketik: **"Explain how geotech drift scan works"**
> (Chatbot menjelaskan: cek SENSOR_READINGS, hitung drift pattern, INSERT ke GEOTECH_AUDIT)

**🔹 Query 2 — Risk Synthesis** (~8 detik)
> Ketik: **"How does geotech risk synthesis assess severity?"**
> (Chatbot menjelaskan: JOIN FACILITIES + INSPECTION_LOG, panggil Cortex LLM, tulis llm_rationale)

**🔹 Query 3 — Action Orchestrator** (~8 detik)
> Ketik: **"What actions does geotech action orchestrator trigger?"**
> (Chatbot menjelaskan: baca recommended_action, branch INSPECTION / ESCALATION / MONITOR, tulis final_action)

**Narrator penutup:**
> *"Terima kasih. GeoTech Monitoring AI — built end-to-end on Snowflake Cortex, Streamlit in Snowflake, dan prinsip Human-in-the-Loop governance."*

---

## 📋 Ringkasan Timing

| Segmen | Menu | Durasi |
|--------|------|--------|
| 00:00 – 00:15 | Overview | 15 detik |
| 00:15 – 00:50 | Dashboard + Simulator | 35 detik |
| 00:50 – 01:15 | Audit Trail + HITL Dispatch | 25 detik |
| 01:15 – 01:37 | Detection Diagnostics | 22 detik |
| 01:37 – 02:00 | Chatbot (3 queries) | 23 detik |
| **Total** | | **2:00 menit** |

---

## Tips Rekaman

- Gunakan resolusi 1920x1080 dengan browser full-screen
- Pastikan **warehouse aktif** sebelum rekaman (test sekali: coba buka semua halaman)
- Siapkan teks query chatbot di notepad agar tidak typo saat rekaman
- Nonaktifkan notifikasi desktop selama merekam
