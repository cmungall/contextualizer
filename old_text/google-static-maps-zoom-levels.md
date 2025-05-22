# Google Static Maps Zoom Levels: Range, Map Types, and Scale

## 1. Range of Zoom Levels for Google Static Maps

- **Zoom levels range from 0 (the whole world) to 21+ (building level)**, though the maximum available zoom depends on location and map type.
- **Typical range:**
  - **0:** Entire world in one tile
  - **21:** Individual buildings (in some places, especially urban areas)

---

## 2. Are All Zoom Levels Offered for All Map Types?

- **Map types:** `roadmap`, `satellite`, `terrain`, `hybrid`
- **Availability:**
  - **Roadmap:** Up to zoom 21 almost everywhere
  - **Satellite/Hybrid:** Up to zoom 21 in major cities; lower in rural/remote areas (sometimes maxes out at 18–19)
  - **Terrain:** Usually up to zoom 15; sometimes higher, but often limited
- **Not all zoom levels are available everywhere or for every map type.** If you request a zoom level that isn’t available for a given location/map type, you may get a lower-resolution image or a blank tile.

---

## 3. What Do Zoom Levels Correspond To?

- **Zoom level** is a measure of scale, where each increment doubles the resolution (halves the visible area).
- **At zoom level N, the world is divided into 2^N × 2^N tiles.**
- **Scale at Equator:**
  - At **zoom 0:** the entire world fits in one 256x256 pixel tile
  - At **zoom 1:** the world is divided into 2x2 tiles
  - At **zoom 2:** 4x4 tiles, etc.
- **Ground Resolution (meters/pixel at Equator):**
  - Formula:  
    ```
    initial_resolution = 156543.03392 meters/pixel at zoom 0
    resolution = initial_resolution / 2^zoom
    ```
  - **Examples:**

    | Zoom | Meters/Pixel (Equator) | Map Width (km) |
    |------|------------------------|---------------|
    | 0    | ~156,543               | ~40,075       |
    | 5    | ~4,892                 | ~1,252        |
    | 10   | ~152                   | ~39           |
    | 15   | ~4.78                  | ~1.2          |
    | 20   | ~0.15                  | ~0.005        |

- **Scale and ground resolution** decrease with latitude (pixels represent less ground as you move toward the poles).

---

## 4. References

- [Google Static Maps API Docs](https://developers.google.com/maps/documentation/maps-static/start)
- [Google Maps Tile System](https://developers.google.com/maps/documentation/javascript/coordinates)
- [Scale at different zoom levels](https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Resolution_and_Scale)

---

## Summary Table: Zoom Level vs. Ground Resolution (at Equator)

| Zoom | Meters/Pixel | Map Width (km) | Typical Map Type Max      |
|------|--------------|----------------|--------------------------|
| 0    | 156,543      | 40,075         | All                      |
| 5    | 4,892        | 1,252          | All                      |
| 10   | 152          | 39             | All                      |
| 15   | 4.78         | 1.2            | All, Terrain may limit   |
| 18   | 0.597        | 0.15           | Road/Sat, Terrain may limit |
| 21   | 0.0746       | 0.019          | Road/Sat (urban only)    |

---

## Key Points

- **Zoom levels:** 0–21 (practically, 0–21, but not all available everywhere)
- **Map types:** Roadmap and Satellite go highest; Terrain is often limited
- **Zoom = scale:** Each level doubles the detail (halves area shown)
- **Meters/pixel:** At zoom 21, ~7.5 cm/pixel at the equator

---

**Let me know if you want code or a calculator for specific zoom levels and locations!**
