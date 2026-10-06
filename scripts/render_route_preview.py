#!/usr/bin/env python3
"""Render an indoor route on two confirmed, same-size plan images."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from platform_support import load_font
from validate_route import validate_topology


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label(draw: ImageDraw.ImageDraw, position: tuple[float, float], value: str,
          font, anchor: str = "mm") -> None:
    box = draw.textbbox(position, value, font=font, anchor=anchor)
    draw.rounded_rectangle((box[0] - 8, box[1] - 5, box[2] + 8, box[3] + 5),
                           radius=7, fill=(255, 255, 255, 238),
                           outline=(179, 68, 8, 255), width=2)
    draw.text(position, value, font=font, anchor=anchor, fill=(70, 36, 18, 255))


def draw_route(image: Image.Image, route: dict, topology: dict) -> Image.Image:
    result = image.convert("RGBA")
    draw = ImageDraw.Draw(result, "RGBA")
    points = [tuple(p) for p in topology["route_render_points"]]
    draw.line(points, fill=(255, 255, 255, 245), width=20, joint="curve")
    draw.line(points, fill=(221, 77, 14, 245), width=11, joint="curve")
    start, end = points[0], points[-1]
    for point, name in ((start, "起"), (end, "终")):
        x, y = point
        draw.ellipse((x - 15, y - 15, x + 15, y + 15),
                     fill=(221, 77, 14, 255), outline=(255, 255, 255, 255), width=3)
        draw.text((x, y), name, font=load_font(18), fill="white", anchor="mm")
    # Arrow follows the final segment; its position never changes the route.
    a, b = points[-2], points[-1]
    length = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    tip = (a[0] + (b[0] - a[0]) * .6, a[1] + (b[1] - a[1]) * .6)
    base = (tip[0] - ux * 18, tip[1] - uy * 18)
    side = (-uy * 10, ux * 10)
    draw.polygon([tip, (base[0] + side[0], base[1] + side[1]),
                  (base[0] - side[0], base[1] - side[1])],
                 fill=(221, 77, 14, 255), outline=(255, 255, 255, 255), width=2)
    label(draw, (start[0] + 100, start[1] - 18), route["start_label"], load_font(21))
    label(draw, (end[0] + 105, end[1] + 20), route["end_label"], load_font(21))
    return result.convert("RGB")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--furniture", type=Path, required=True)
    parser.add_argument("--topology", type=Path, required=True)
    parser.add_argument("--recognition", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new path")
    topology = json.loads(args.topology.read_text(encoding="utf-8"))
    recognition = json.loads(args.recognition.read_text(encoding="utf-8"))
    route = topology["tour_route"]
    if route.get("mode") != "indoor_segment":
        parser.error("this preview renderer requires an indoor_segment")
    result = validate_topology(topology, recognition=recognition)
    expected = topology.get("reference_sha256", {})
    for name, path in (("plan", args.plan), ("furniture", args.furniture),
                       ("recognition", args.recognition)):
        if expected.get(name) != digest(path):
            parser.error(f"{name} image does not match the route's confirmed reference hash")
    with Image.open(args.plan) as plan_image, Image.open(args.furniture) as furniture_image:
        if plan_image.size != furniture_image.size:
            parser.error("confirmed images must have the same pixel dimensions")
        width, height = plan_image.size
        for p in topology["route_render_points"]:
            if not 0 <= p[0] < width or not 0 <= p[1] < height:
                parser.error("route point is outside the reference image")
        margin, header, footer = 24, 76, 96
        canvas = Image.new("RGB", (width * 2 + margin * 3,
                                   height + header + footer + margin), "#f4efe9")
        canvas.paste(draw_route(plan_image, route, topology), (margin, header))
        canvas.paste(draw_route(furniture_image, route, topology),
                     (width + margin * 2, header))
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 25), "已确认户型图 · 室内动线", font=load_font(27),
              fill="#46372d")
    draw.text((width + margin * 2, 25), "已确认家具图 · 避让预览",
              font=load_font(27), fill="#46372d")
    draw.text((margin, header + height + 28),
              f"镜头朝向：{route['camera_facing']}  ·  {route['approx_pace']}",
              font=load_font(21), fill="#46372d")
    draw.text((margin, header + height + 62),
              "橙线为摄像机中心线示意；家具净宽与实际镜头碰撞尚未实测，待用户确认。",
              font=load_font(19), fill="#705d50")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output)
    print(json.dumps({"status": "ok", "output": str(args.output.resolve()),
                      "size": canvas.size, "validation": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
