# CONVENTIONS.md — Coordinate System

Single source of truth for how zone/tripwire geometry is represented,
stored, and interpreted. Both the **edge** (Zone/Tripwire Engine) and
the **frontend** (Zone Editor) must follow this exactly — a mismatch
here produces zones that look right in the dashboard but misfire (or
never fire) on the edge.

This resolves the ambiguity left open in `ARCHITECTURE.md` around
tripwire direction — treat this document as the authoritative version
of that part of the spec.

---

## 1. Origin and Axes

- Origin `(0, 0)` is the **top-left** corner of the frame.
- `x` increases to the right, `y` increases downward.
- This matches standard image-coordinate convention (OpenCV, most
  camera/ML pipelines) — no flipping needed when going from a decoded
  video frame to stored geometry.

## 2. Normalization

All stored coordinates (in `zones.polygon`, `tripwires.line`, and in
every point inside a Kafka `trajectory` array) are **normalized to
`[0.0, 1.0]`**, not raw pixels:

```
x_norm = x_pixel / frame_width
y_norm = y_pixel / frame_height
```

**Why:** the frontend draws on a reference snapshot that may be a
different resolution than what the edge decodes from RTSP (e.g. the
dashboard might request a lower-res JPEG snapshot than the edge's
inference resolution, or a camera firmware update changes stream
resolution). Normalized coordinates make geometry resolution-independent
as long as **aspect ratio is preserved** end to end (see §5).

## 3. Anchor Point (for zone membership)

A tracked object's position, for the purpose of zone-membership
testing, is its **bottom-center point** of the bounding box:

```
anchor_x = bbox_x + bbox_w / 2
anchor_y = bbox_y + bbox_h
```

This approximates where the person/vehicle contacts the ground, which
is the geometrically correct point to test against a zone drawn on the
ground plane (a point at the top of a tall bounding box can visually
sit inside a zone on-screen while the person is actually standing well
outside it).

## 4. Polygon Format (Zones)

- `polygon`: ordered array of `[x, y]` normalized points,
  `[[x1,y1], [x2,y2], ..., [xn,yn]]`.
- Minimum 3 points.
- **Do not repeat the first point as the last** — the polygon is
  implicitly closed between the last and first point.
- Must be a simple polygon (edges do not self-intersect). Validate this
  on save in `zones.py`, not just on the edge — catch bad geometry at
  authoring time.
- Winding order (clockwise vs counter-clockwise) does not matter for
  point-in-polygon testing (standard ray-casting / winding-number
  algorithms handle both) — don't enforce one.

**Membership test:** standard point-in-polygon (ray casting is fine at
this scale — zones have a handful of vertices, not thousands).

## 5. Line Format & Direction (Tripwires)

- `line`: exactly two normalized points, `[[x1, y1], [x2, y2]]`. Call
  these `P1` (line start) and `P2` (line end) — **order matters**, it
  defines direction (see below).
- `watched_direction`: one of `"a_to_b"`, `"b_to_a"`, or `"both"`.

### Defining side A / side B

The line direction vector is `d = P2 - P1`. Side B is the side the
vector `d` rotated **90° clockwise** points toward (in screen
coordinates, clockwise from `d` means: `normal = (d.y, -d.x)`... using
the y-down convention from §1, a 90° clockwise rotation of vector
`(dx, dy)` is `(-dy, dx)`). Concretely:

```
dx, dy = P2.x - P1.x, P2.y - P1.y
normal = (-dy, dx)          # points toward side B
```

For any point `Q`, compute which side it's on via the sign of the
cross product of `d` and `(Q - P1)`:

```
cross = dx * (Q.y - P1.y) - dy * (Q.x - P1.x)
# cross > 0  → Q is on side B
# cross < 0  → Q is on side A
# cross == 0 → Q is exactly on the line
```

**Crossing event:** on each frame, check the sign of `cross` for a
track's anchor point against its sign on the previous frame. A sign
flip from A→B (previous `cross < 0`, current `cross > 0`) is an
`"a_to_b"` crossing; the reverse is `"b_to_a"`. `watched_direction:
"both"` fires on either flip.

This replaces the earlier placeholder value `"left_to_right"` in
`ARCHITECTURE.md §6` — that phrasing is ambiguous because "left" and
"right" depend on how the operator happened to draw the line. `a_to_b`
/ `b_to_a` is unambiguous given `P1`/`P2` order, which the Zone Editor
controls directly (see §6).

### Frontend responsibility

When the operator draws a tripwire, the **first click is `P1`, the
second click is `P2`** — the editor should visually indicate this
(e.g. an arrowhead or "A"/"B" labels at each end, or an arrow showing
the `a_to_b` direction) so the operator can reason about which
direction they're selecting, rather than guessing from raw coordinates.

## 6. Trajectory Points (Kafka payload)

The `trajectory` array in `intrusion_confirmed` events uses the same
normalized `[x, y]` anchor-point convention as §3 — it's a short
recent-history sample of the anchor point, not the full bounding box,
for lightweight visualization on the incident detail view.

## 7. Aspect Ratio Guard

Because normalization removes absolute resolution but not aspect
ratio, `zones.py` / `tripwires.py` should store the reference frame's
`aspect_ratio` (or `width`/`height`) alongside the geometry at save
time, and the edge's config-pull client should warn (log, not crash)
if its live stream's aspect ratio differs meaningfully (e.g. >1%) from
what the zone was authored against. A mismatch means the zone will be
geometrically distorted relative to what the operator drew.

## 8. Worked Example

A 1920×1080 frame. Operator draws a zone near the bottom of frame,
roughly a horizontal band:

- Pixel points: `(200, 900)`, `(1700, 900)`, `(1700, 1050)`, `(200, 1050)`
- Normalized: `(0.104, 0.833)`, `(0.885, 0.833)`, `(0.885, 0.972)`, `(0.104, 0.972)`

A person detected with bbox `(x=800, y=920, w=80, h=160)` on that same
1920×1080 frame:

- Anchor point (pixel): `(800 + 40, 920 + 160) = (840, 1080)`
- Anchor point (normalized): `(0.4375, 1.0)`

Testing `(0.4375, 1.0)` against the normalized zone polygon above
confirms the point is inside → zone membership check passes for this
frame; dwell timer accumulates per `ARCHITECTURE.md §4`.