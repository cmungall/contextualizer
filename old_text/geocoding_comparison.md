# Geocoding Service Comparison

## 🔍 Nominatim (OpenStreetMap)

### ✅ Usage (Public instance)
- **Rate limit**:  
  - **1 request per second** per IP (strictly enforced)  
  - **No batch or bulk geocoding allowed**
- **User-Agent required**: Must include a valid `User-Agent` and ideally contact info (email)
- **Caching**: Required if you intend to repeatedly geocode the same queries

### ❌ Restrictions
- **No heavy use**: Not for production/commercial use without hosting your own instance
- **No high-volume** automated use (e.g., large datasets)

### ✅ Hosting Your Own Instance
- No usage limits (other than what your hardware/network can support)
- Requires ~40–60 GB for the planet data + RAM/CPU depending on region

---

## 🌍 Alternatives

### ✅ Google Maps Geocoding API
- **Free**: 100 requests/day (after enabling billing)
- **Paid**: $5 per 1000 requests (first $200/month free = 40,000 requests/month)
- **Advantages**:
  - Highly accurate, global coverage
  - Reverse geocoding, autocomplete, place details
- **Limits**: 50 QPS by default (can request higher)

### ✅ Mapbox Geocoding API
- **Free**: 100,000 requests/month
- **Paid**: Starts at $0.75 per 1000 requests
- **Great for**: Visual map integration, flexible plans

### ✅ HERE Geocoding & Search API
- **Free**: 250,000 transactions/month with Freemium plan
- **Commercial**: Volume pricing available
- **Good for**: Batch geocoding, enterprise-grade use

### ✅ Esri (ArcGIS) Geocoding
- Free limited use via developer accounts
- Commercial plans for enterprise
- Strong on address precision and parcel-level data (especially in US)

### ✅ Positionstack
- Free tier: 25,000 requests/month
- Paid plans: Start at $9/month
- Offers both forward and reverse geocoding using OpenStreetMap and other sources

### ✅ OpenCage
- Free: 2,500 requests/day
- Paid: From $50/month for 100,000 requests
- Built on OSM and other open data, includes confidence scores

---

## 🧭 Summary Comparison Table

| Provider        | Free Tier                        | Rate Limits             | Batch Support | Notes                              |
|----------------|----------------------------------|--------------------------|---------------|-------------------------------------|
| **Nominatim**   | Yes (1 rps, public instance)     | 1 rps/IP                 | ❌             | Must self-host for heavy use        |
| **Google Maps** | $200/month free (≈40,000 reqs)   | 50 QPS                   | ✅             | Very accurate, costly beyond free   |
| **Mapbox**      | 100,000 reqs/month               | Usage-based              | ✅             | Stylish maps, developer-friendly    |
| **HERE**        | 250,000/month (Freemium)         | Usage-based              | ✅             | Commercial-grade                    |
| **Esri**        | Limited via dev account          | Enterprise-focused       | ✅             | Excellent for US data               |
| **OpenCage**    | 2,500/day                        | Tier-based               | ✅             | Clean OSM-based API                 |
| **Positionstack** | 25,000/month                   | Tier-based               | ✅             | Lightweight, simple                 |
