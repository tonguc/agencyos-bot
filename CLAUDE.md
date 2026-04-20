# AgencyOS — Proje Hafızası

Bu dosya her yeni Claude oturumunda projeyi sıfırdan açıklamak zorunda kalmamak için tutulur.
**Her tamamlanan adımdan sonra güncellenir.**

---

## Proje Nedir?

AgencyOS, yapay zeka destekli tam otonom bir freelance dijital ajans sistemidir.

> "Jarvis gibi konuşarak yönetilen, 7/24 çalışan, lead bulan, teklif yazan ve proje teslim eden tek kişilik yapay zeka ajansı."

**Sahip:** Tonguc Karacay  
**Mevcut durum:** Step 11 tamamlandı (Sesli Asistan)

---

## Ne Yapıyor?

1. **Lead Bulucu** — Google Maps / LinkedIn'den nitelikli müşteri adayı toplar
2. **Audit Engine** — Müşterinin web sitesini analiz eder, somut bulgular çıkarır
3. **Hook Engine** — Bulgulara göre satış hook'u seçer ve yazar
4. **Outreach Writer** — 4 farklı versiyonda kişiselleştirilmiş mesaj üretir
5. **Proposal Generator** — Audit verisinden profesyonel PDF teklif oluşturur
6. **Pipeline CRM** — Lead'leri Yeni → Kapandı sürecinde takip eder

**Hedef kitle:** Klinikler, yerel işletmeler, KOBİ'ler (Türkiye pazarı, ileride Global)

---

## Mimari Kararlar

### Tech Stack
| Katman | Teknoloji | Neden |
|--------|-----------|-------|
| Backend | FastAPI (Python) | Mevcut AI/core logic Python, hızlı geliştirme |
| Frontend | Next.js (App Router) | Güçlü dashboard, SSR, TypeScript |
| Database | PostgreSQL | Hız, esneklik, JSONB audit data |
| Queue | Redis + ARQ | Async AI job'ları (audit 10s, PDF 5s) |
| AI | Claude Sonnet 4.6 | Audit/outreach/proposal generation |

### Hibrit Bot Yapısı
- **Web UI** = ana operasyon paneli (tüm iş akışı)
- **Telegram bot** = bildirimler, hızlı tetikleme, hot lead uyarıları
- Bot doğrudan core'a erişmez — FastAPI üzerinden çalışır (Step 9'da refactor)

### Multi-tenant Hazırlık
- İlk versiyon single-user (internal tool)
- `user_id` alanı tüm modellerde var ama nullable
- Auth: tek `X-API-Key` header, login ekranı yok
- SaaS'a geçiş sonraki fazda

---

## Klasör Yapısı

```
agencyos-bot/
├── CLAUDE.md                    ← bu dosya
├── .env.example
│
├── backend/                     ← FastAPI uygulaması
│   ├── main.py                  # app factory, middleware, lifespan
│   ├── config.py                # pydantic-settings, tüm env var'lar
│   ├── database.py              # SQLAlchemy async engine + get_db()
│   ├── logging_config.py        # stdout + file logging
│   ├── alembic.ini
│   │
│   ├── middleware/
│   │   └── auth.py              # X-API-Key kontrolü
│   │
│   ├── api/routes/
│   │   └── health.py            # GET /health
│   │
│   ├── models/                  # SQLAlchemy ORM (6 tablo)
│   │   ├── mixins.py            # UUIDPrimaryKey, TimestampMixin
│   │   ├── lead.py
│   │   ├── audit.py
│   │   ├── outreach.py
│   │   ├── proposal.py
│   │   ├── job.py               # status/progress/error tracking
│   │   └── activity_log.py      # immutable event log
│   │
│   ├── repositories/            # data access layer
│   │   ├── base.py              # generic CRUD
│   │   ├── lead.py              # filter(), pipeline_counts(), get_hot()
│   │   └── job.py               # mark_running/progress/completed/failed
│   │
│   ├── core/                    # Step 3'te buraya taşınacak
│   │   └── (mevcut bot core/ buraya gelecek)
│   │
│   ├── jobs/                    # Step 5'te oluşacak (ARQ workers)
│   └── migrations/
│       └── versions/
│           └── 0001_initial_schema.py
│
├── frontend/                    ← Step 6'da oluşacak (Next.js)
│
└── (eski bot dosyaları — Step 3'te taşınacak)
    ├── bot/
    ├── core/
    ├── crm/
    ├── playbooks/
    └── main.py
```

---

## Veri Modeli Özeti

```
leads          → pipeline durumu, skor, kaynak, user_id (nullable)
audits         → site verisi + Claude result JSONB + denorm hızlı erişim
outreach_msgs  → 4 versiyon + gönderim takibi (kanal, zaman, versiyon)
proposals      → Claude narrative JSONB + pdf_path
jobs           → type/status/progress_pct/progress_message/error/timing
activity_logs  → immutable event log (append-only)
```

**Job status lifecycle:** `pending → running → completed | failed`

---

## Temel Guardrail'ler (BOZULMASIN)

### A. API contract sabitleme
Trigger endpoint'leri her zaman aynı job response shape'i döner:
```json
{ "job_id": "uuid", "status": "completed|pending", "result": {} }
```
Step 4 sync → Step 5 async geçişte dış API değişmez.

### B. Job status modeli sabit
`status / progress_pct / progress_message / error_message / started_at / finished_at`
— bu alanlar Step 5'te de, UI'da da aynı.

### C. Core katmanı framework-agnostic
`backend/core/` içinde yasak:
```python
# YASAK:
from fastapi import ...
from arq import ...
from telegram import ...
```
Core sadece `dict / str / int` alır, `dict / str` döner.
Framework glue tamamen `routes/`, `jobs/`, `telegram/` katmanlarında.

---

## Build Sırası ve Durum

| # | Adım | Durum |
|---|------|-------|
| 1 | Backend foundation (FastAPI, config, DB, Alembic, auth) | ✅ Tamamlandı |
| 2 | ORM modelleri + repository pattern + migration | ✅ Tamamlandı |
| 3 | Core taşıma (Notion kaldır, service layer) | ✅ Tamamlandı |
| 4 | REST API routes (sync stub, Postman test) | ✅ Tamamlandı |
| 5 | Job queue (ARQ, async, SSE/WebSocket) | ✅ Tamamlandı |
| 6 | Frontend shell (Next.js, shadcn/ui, API client) | ✅ Tamamlandı |
| 7 | Pipeline + Lead listesi ekranları | ✅ Tamamlandı |
| 8 | Lead detay (audit/outreach/proposal/history) | ✅ Tamamlandı |
| 9 | Telegram bot → FastAPI refactor | ✅ Tamamlandı |
| 10 | Docker + deploy | ✅ Tamamlandı |
| 11 | Sesli asistan (STT + TTS + Claude tool use) | ✅ Tamamlandı |

---

## Çalıştırma

```bash
# Backend (Step 1-2 sonrası)
cd backend
uvicorn main:app --reload

# DB migration (PostgreSQL ayakta olmalı)
cd backend
alembic upgrade head

# Bağlantı testi
curl http://localhost:8000/health
```

---

## Prompt Mühendisliği Notları

### Audit prompt (v2)
- `core/prompts.py` → `AUDIT_PROMPT`
- Çıktı: `ilk_izlenim`, `killer_insight`, `ux_hatalar` (siddet), `seo_aciklar`,
  `donusum_engelleri`, `hizli_kazanimlar`, `skorlar`, `urgency`, `lead_kalitesi`,
  `en_acitan_nokta`, `kisisel_insight`
- `max_tokens=2800`, `temperature=0`

### Outreach prompt
- 4 versiyon: Meraklı / Doğrudan / Nazik / Proof-based
- V4 her zaman `behance.net/tonguc` ekler
- `kisisel_insight`, `urgency`, `lead_kalitesi` kullanır

### Proposal prompt
- Narrative sections: başlık, giriş, durum özeti, çözüm, haftalık plan,
  sonuçlar, fiyat aralığı, CTA
- HTML → weasyprint → PDF
- `max_tokens=1200`, `temperature=0.2`

---

## Model Seçimi

| Görev | Model |
|-------|-------|
| Bu geliştirme oturumu (kod yazma) | `claude-sonnet-4-6` |
| AgencyOS'un kendi API çağrıları | `claude-sonnet-4-6` |
| Karmaşık mimari karar / büyük refactor | **`claude-opus-4-7`'ye geç** |

**Opus'a geçiş kriterleri:**
- Birden fazla katmanı etkileyen mimari değişiklik gerektiğinde
- Step 5 (job queue) — ARQ + WebSocket + event tasarımı karmaşık
- Step 8 (lead detay) — çok sayıda bağımlılık aynı anda
- Bir şeyler beklenmedik şekilde kırılmaya başladığında

---

## Sesli Asistan (Step 11)

### Mimari
- **STT:** Browser SpeechRecognition (Chrome) veya OpenAI Whisper fallback
- **TTS:** OpenAI `tts-1` model, `nova` sesi (native Türkçe) — `OPENAI_API_KEY` gerekli
- **Chat:** Claude Sonnet 4.6 + `trigger_scrape` tool use (prompt caching ile)
- **VAD:** Web Audio API AnalyserNode, RMS threshold=0.018, min 1.2s konuşma, 900ms sessizlik

### Önemli Kararlar
- `max_tokens=400` — tool call JSON'u tamamlamak için yeterli olmalı (120 fazla düşüktü)
- History: backend 10, frontend 12 mesaj — context yitirmemek için
- Session modu: ilk tıklama başlatır, cevap sonrası otomatik dinler, tekrar tıklayınca biter
- Scrape tetiklenince `/jobs` sayfasına yönlendirir, session devam eder
- `query` parametresi: kullanıcının söylediği exact phrase Apify'a gider (sector değil)
  örn: "KBB doktoru" → query="kulak burun boğaz doktoru", sector="klinik"

### Kritik Buglar (çözüldü)
- `_get_openai_client()` def satırı kaybolmuştu → TTS/STT 500 atıyordu
- `max_tokens` çok düşük → tool call JSON kesiliyordu → job oluşmuyordu
- Session kapanıyordu scrape sonrası → buton pasif kalıyordu

### Backend Dosyaları
- `backend/api/routes/voice.py` — STT, TTS, chat endpoint + SYSTEM_PROMPT
- `backend/jobs/tasks/collect.py` — `run_collect_job(query=...)` kwarg
- `backend/services/lead_service.py` — query varsa `collect_by_query`, yoksa sektör terimi

### Frontend Dosyaları
- `frontend/components/voice/voice-assistant.tsx` — tam component (VAD, session, barge-in)
- `frontend/app/jobs/page.tsx` — 3s auto-refresh, query label gösterimi

### Deploy Notu
- `backend/entrypoint.sh` hem uvicorn hem ARQ worker'ı başlatıyor (tek container)
- `railway.toml` repo kökünde — `backend/Dockerfile` kullan der
- `OPENAI_API_KEY` Railway Variables'a eklenmiş

---

## Önemli Dosyalar (Hızlı Navigasyon)

| Dosya | Ne Yapar |
|-------|----------|
| `backend/config.py` | Tüm env var'lar |
| `backend/database.py` | DB engine + `get_db()` |
| `backend/models/job.py` | Job status modeli |
| `backend/repositories/lead.py` | Pipeline queries |
| `core/prompts.py` | Tüm Claude prompt'ları |
| `core/audit_generator.py` | Site fetch + audit generation |
| `core/proposal_generator.py` | PDF teklif üretimi |
| `playbooks/klinik.json` | Klinik sektör konfigürasyonu |
| `backend/api/routes/voice.py` | Sesli asistan backend (STT/TTS/chat) |
| `frontend/components/voice/voice-assistant.tsx` | Sesli asistan React component |
| `railway.toml` | Railway deploy config (backend/Dockerfile) |
| `backend/entrypoint.sh` | Startup: migration + ARQ worker + uvicorn |
