# CBORG Vision Model Suitability for Map Images

## Selected Model: Qwen 2.5 VL Instruct 72B (CBorg Vision)

**Vision Support:** Yes  
**Context Window:** 8,000 tokens  
**Minimum Image Size:** 256×256 pixels  
**Cost:** Free (locally hosted)

---

## Image Token Consumption Estimates

| Image Size       | Estimated Token Cost |
|------------------|----------------------|
| 256×256          | ~500–1,000 tokens    |
| 512×512          | ~2,000–3,000 tokens  |
| 1024×1024        | ~4,000–6,000 tokens  |

Token usage depends on:
- Image resolution
- Format (PNG/JPEG)
- Visual complexity (dense text increases cost)

---

## Your Use Case

You provided: **600×400 pixel** images  
- ✅ Above the 256×256 minimum
- ✅ Estimated token cost: ~800–1,200
- ✅ Leaves room for additional prompt tokens

---

## Prompt Size: "Half a Printed Page"

- Estimated text length: ~150–175 words
- Estimated token usage: **~300 tokens**
- Leaves **~7,700 tokens** for image + output

---

## Combined Use Feasibility

| Image Size       | Token Estimate | Safe With 300-Token Prompt? |
|------------------|----------------|------------------------------|
| 600×400          | ~1,000         | ✅ Yes                       |
| 800×600          | ~2,000         | ✅ Yes                       |
| 1024×768         | ~3,500         | ✅ Yes                       |
| 1600×1200        | ~6,000+        | ⚠️ Near limit                |
| 2048×2048        | ~8,000+        | ❌ Exceeds limit             |

---

## Recommendation

- For a 300-token instruction prompt:
  - Use **images up to ~1024×768** comfortably
  - Stay below **1600×1200** unless prompt/output is minimal
- 600×400 images are ideal for most tasks