# QISO

نظام RAG متخصص في أنظمة إدارة الجودة والتدقيق الداخلي، مبني للاسترجاع والإجابة من مجموعة مستندات ISO مع إظهار المصادر وأرقام الصفحات.

---

## 1. الهدف

يهدف QISO إلى مساعدة المستخدم في البحث داخل مصادر إدارة الجودة والتدقيق الداخلي والإجابة عن الأسئلة اعتمادًا على المستندات المخزنة فقط.

النظام مصمم بحيث:

- يسترجع المعلومات من المصادر.
- يعيد ترتيب النتائج حسب الصلة.
- يمنع الإجابة عند عدم وجود دليل كافٍ.
- يولد إجابة Grounded من المصادر فقط.
- يعرض الاستشهادات والمصادر وأرقام الصفحات.
- يدعم الأسئلة العربية والإنجليزية.

---

## 2. المعمارية

```text
PDF Documents
      ↓
Preprocessing
      ↓
Chunking
      ↓
Cohere Embeddings
      ↓
Chroma Vector Database
      ↓
────────────────────────────
          User Query
              ↓
      Vector Retrieval
              +
         BM25 Search
              ↓
        Hybrid Search
            (RRF)
              ↓
          Reranker
              ↓
        Evidence Gate
              ↓
     Cohere Generation
              ↓
     Answer + Citations
              ↓
       Streamlit UI
```

---

## 3. البيانات

تمت معالجة:

```text
PDF files:       46
Pages:           421
Chunks:          1407
Vectors:         1407
```

إعدادات Chunking:

```text
Chunk size:      800
Chunk overlap:   120
Average size:    567.2
Shortest:        59
Longest:         800
```

قاعدة المتجهات:

```text
Database:        ChromaDB
Collection:      qiso_docs
Embedding model: embed-multilingual-v3.0
```

---

## 4. الاسترجاع

يستخدم QISO ثلاث مراحل:

### Vector Retrieval

البحث الدلالي باستخدام Cohere Embeddings وChromaDB.

### BM25

البحث المعجمي باستخدام:

```text
rank-bm25
```

### Hybrid Search

يتم دمج نتائج Vector Search وBM25 باستخدام:

```text
Reciprocal Rank Fusion (RRF)
```

ثم يتم تمرير النتائج إلى Reranker قبل توليد الإجابة.

---

## 5. Evidence Gate

قبل إرسال السياق إلى النموذج، يتحقق النظام من وجود دليل كافٍ.

القيمة الحالية:

```text
EVIDENCE_THRESHOLD = 0.05
```

إذا لم توجد نتائج مناسبة أو كانت درجة الدليل أقل من الحد المطلوب، لا يسمح QISO للنموذج بالإجابة من معرفته العامة.

مثال:

```text
السؤال:
ما عاصمة فرنسا؟

النتيجة:
المعلومة غير متوفرة بشكل كافٍ في المصادر.
```

---

## 6. Generation

النموذج المستخدم:

```text
command-a-03-2025
```

الخدمة:

```text
Cohere
```

إعدادات التوليد الأساسية:

```text
temperature = 0
max_tokens = 700
```

النموذج ملزم بـ:

- استخدام المصادر المسترجعة فقط.
- عدم استخدام المعرفة الخارجية.
- عدم اختراع المعلومات.
- الإجابة بنفس لغة السؤال.
- استخدام `[1]`, `[2]`, `[3]` للاستشهاد بالمصادر.
- عدم اختراع أرقام بنود ISO أو الصفحات أو أسماء المستندات.
- التمييز بين Requirement وGuidance وRecommendation.

---

## 7. واجهة المستخدم

واجهة QISO مبنية باستخدام:

```text
Streamlit 1.65.0
```

وتوفر:

- إدخال السؤال.
- عرض الإجابة.
- عرض الاستشهادات.
- ربط Citation بالمصدر المقابل.
- عرض اسم المستند.
- عرض رقم الصفحة.
- عرض النص المسترجع.
- عرض وقت التنفيذ.
- دعم العربية والإنجليزية.

الواجهة لا تنشئ Citation غير موجود في إجابة الـRAG.

---

## 8. معالجة الأخطاء

يتعامل `generator.py` مع أخطاء الخدمة بدل انهيار التطبيق.

من الحالات التي تتم معالجتها:

```text
Cohere Rate Limit
Timeout
API Error
Invalid / Empty Response
Insufficient Evidence
```

في حال حدوث مشكلة، يعرض النظام رسالة واضحة للمستخدم بدل ظهور Traceback.

---

## 9. تقييم RAGAS

تم تقييم النظام على:

```text
30 / 30 questions
```

النتائج النهائية:

| Metric | Score |
|---|---:|
| Faithfulness | 0.9236 |
| Answer Relevancy | 0.9547 |
| Context Precision | 0.9358 |
| Context Relevance | 1.0000 |
| Overall Average | **0.9535** |

ملاحظة:

`0.9535` هو متوسط مقاييس RAGAS المستخدمة على مجموعة الاختبار، وليس نسبة دقة مطلقة للنظام.

ملف النتائج:

```text
ragas_results_final.csv
```

ويمكن إعادة التقييم باستخدام:

```powershell
python -X utf8 ragas_evaluation.py
```

---

## 10. اختبار الأداء

نتائج اختبار End-to-End:

```text
Fastest:   4.30 sec
Slowest:   6.96 sec
Average:   5.84 sec
```

يشمل الاختبار المسار:

```text
Question
   ↓
Retrieval
   ↓
Reranking
   ↓
Evidence Gate
   ↓
Generation
   ↓
Answer
```

---

## 11. الاختبارات النهائية

```text
RAGAS Evaluation       PASS
30 / 30 Questions      PASS
Hybrid Retrieval       PASS
Reranking              PASS
Evidence Gate          PASS
Grounded Generation    PASS
Sources                PASS
Citations              PASS
Arabic Queries         PASS
English Queries        PASS
Out-of-Scope Rejection PASS
Error Handling         PASS
Streamlit UI           PASS
```

---

## 12. هيكل المشروع

```text
QISO/
│
├── .streamlit/
├── chroma_db/
├── core/
├── docs/
├── ui/
│
├── .env
├── .gitignore
├── domain.md
├── evaluation.py
├── main.py
├── manifest.json
├── ragas_evaluation.py
├── ragas_results_final.csv
├── README_AR.md
├── requirements.txt
└── streamlit_app.py
```

### المجلدات الرئيسية

```text
docs/
```

يحتوي على مصادر PDF.

```text
core/
```

يحتوي على مكونات RAG الأساسية مثل:

```text
Preprocessing
Ingestion
Chunking
Vector Retrieval
BM25
Hybrid Search
Reranking
Generation
```

```text
chroma_db/
```

قاعدة البيانات المتجهية المحلية.

```text
ui/
```

مكونات واجهة Streamlit.

---

## 13. الإعداد

إنشاء البيئة:

```powershell
python -m venv .venv
```

تفعيلها في PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

تثبيت المتطلبات:

```powershell
pip install -r requirements.txt
```

---

## 14. إعداد Cohere

أنشئ ملف:

```text
.env
```

وأضف:

```text
COHERE_API_KEY=YOUR_KEY
```

يمكن تحديد نموذج Generation اختياريًا:

```text
COHERE_GENERATION_MODEL=command-a-03-2025
```

يجب عدم رفع `.env` إلى GitHub أو مشاركته.

---

## 15. تشغيل QISO

شغّل:

```powershell
python -m streamlit run streamlit_app.py
```

ثم افتح واجهة Streamlit في المتصفح.

---

## 16. مثال

السؤال:

```text
What is the purpose of internal audit?
```

يقوم QISO بـ:

```text
Hybrid Search
    ↓
Reranking
    ↓
Evidence Check
    ↓
Grounded Answer
    ↓
Citations
    ↓
Sources + Pages
```

ويتم إنشاء الإجابة اعتمادًا على المصادر المسترجعة فقط.

---

## 17. الأمان

لا يجب رفع العناصر التالية إلى مستودع عام:

```text
.env
.venv/
```

ويجب التأكد من وجودها في:

```text
.gitignore
```

لا يتم وضع مفتاح Cohere داخل ملفات Python.

---

## 18. الحالة الحالية

```text
Ingestion               COMPLETE
Chunking                COMPLETE
Embeddings              COMPLETE
Vector Store            COMPLETE
BM25                     COMPLETE
Hybrid Retrieval         COMPLETE
Reranking                COMPLETE
Evidence Gate            COMPLETE
Generation               COMPLETE
Citations                COMPLETE
RAGAS Evaluation         COMPLETE
Performance Test         COMPLETE
Error Handling           COMPLETE
Streamlit UI             COMPLETE
Project Cleanup          COMPLETE
```

QISO أصبح جاهزًا للانتقال إلى مرحلة النشر Deployment.