#!/usr/bin/env python3
"""Render a numbered whole-home tour order on a confirmed floor plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from platform_support import load_font
from validate_route import point_in_polygon, validate_topology


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rounded_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str,
                 font, *, fill: str = "#4b3b31") -> None:
    box = draw.textbbox(xy, value, font=font, anchor="lm")
    draw.rounded_rectangle((box[0] - 6, box[1] - 3, box[2] + 6, box[3] + 3),
                           radius=5, fill="#fffdfa", outline="#ba8c65", width=2)
    draw.text(xy, value, font=font, fill=fill, anchor="lm")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--furniture", type=Path, required=True)
    parser.add_argument("--recognition", type=Path, required=True)
    parser.add_argument("--topology", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new path")
    data = json.loads(args.topology.read_text(encoding="utf-8"))
    recognition = json.loads(args.recognition.read_text(encoding="utf-8"))
    mode = data.get("tour_route", {}).get("mode")
    if mode not in {"entry_to_interior", "full_tour"}:
        parser.error("tour overview requires entry_to_interior or full_tour mode")
    validation = validate_topology(data)
    for name, path in (("plan", args.plan), ("furniture", args.furniture),
                       ("recognition", args.recognition)):
        if data.get("reference_sha256", {}).get(name) != sha256(path):
            parser.error(f"{name} does not match the route's reference SHA256")
    stops = data.get("camera_stops")
    if not isinstance(stops, list) or len(stops) < 2:
        parser.error("camera_stops requires at least two stops")
    if [stop.get("order") for stop in stops] != list(range(1, len(stops) + 1)):
        parser.error("camera_stops must be consecutively numbered")
    polygons = {zone.get("id"): zone.get("render_polygon")
                for zone in recognition.get("zones", [])}
    for stop in stops:
        point = stop.get("point")
        polygon = polygons.get(stop.get("zone"))
        outside_stop = (mode == "full_tour" and stop.get("zone") == "outside"
                        and stop is stops[-1])
        valid_location = (outside_stop and isinstance(point, list) and len(point) == 2
                          and all(isinstance(v, (int, float)) for v in point)) or (
                            isinstance(point, list) and len(point) == 2
                            and isinstance(polygon, list) and len(polygon) >= 3
                            and point_in_polygon(tuple(point), polygon))
        if not valid_location:
            parser.error(f"stop {stop.get('order')} lies outside its declared zone")
        if not all(isinstance(stop.get(key), str) and stop[key].strip()
                   for key in ("label", "via", "look")):
            parser.error(f"stop {stop['order']} lacks a label, access, or camera look")

    with Image.open(args.plan) as source:
        plan = source.convert("RGB")
    width, height = plan.size
    margin, top, bottom, panel_width = 28, 112, 168, 900
    canvas_width = width + panel_width + margin * 3
    canvas_height = height + top + bottom
    canvas = Image.new("RGB", (canvas_width, canvas_height), "#f7f3ed")
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 31), "入户到出户 · 整屋第一人称参观动线",
              font=load_font(34), fill="#40352e")
    draw.text((margin, 78), "数字为停看点；真实门洞顺序已校验，连续摄像机轨迹尚未验收。",
              font=load_font(18), fill="#6e5849")
    draw.text((canvas_width - margin, 43),
              f"9 个室内区域  /  {validation['route_step_count']} 次门洞穿越",
              font=load_font(24), fill="#9a542b", anchor="ra")
    canvas.paste(plan, (margin, top))
    draw.rectangle((margin, top, margin + width - 1, top + height - 1),
                   outline="#d8c7b7", width=2)
    for stop in stops:
        x, y = stop["point"]
        x += margin
        y += top
        color = "#a76031"
        draw.ellipse((x - 20, y - 20, x + 20, y + 20),
                     fill=color, outline="#ffffff", width=4)
        draw.text((x, y), str(stop["order"]), font=load_font(19),
                  fill="#ffffff", anchor="mm")
        label_x = x + 28
        if stop["order"] in {7, 8, 9}:
            label_x = x - 166
        rounded_text(draw, (label_x, y), stop["label"], load_font(18))

    panel_x = width + margin * 2
    panel_y = top
    draw.rounded_rectangle((panel_x, panel_y, panel_x + panel_width,
                            panel_y + height), radius=14, fill="#fffdfa",
                           outline="#d8c7b7", width=2)
    draw.text((panel_x + 28, panel_y + 30), "参观次序与镜头动作",
              font=load_font(27), fill="#40352e")
    draw.text((panel_x + 28, panel_y + 70),
              "入户 → 餐厅 → 公卫 → 次卧 → 阳台 → 客厅 → 主卧 → 主卫 → 书房 → 厨房 → 出户",
              font=load_font(17), fill="#876d59")
    row_top = panel_y + 116
    row_height = (height - 136) // len(stops)
    for index, stop in enumerate(stops):
        y = row_top + index * row_height
        if index % 2 == 0:
            draw.rounded_rectangle((panel_x + 16, y - 6,
                                    panel_x + panel_width - 16, y + row_height - 10),
                                   radius=8, fill="#f7f1e9")
        draw.ellipse((panel_x + 28, y + 12, panel_x + 70, y + 54),
                     fill="#a76031")
        draw.text((panel_x + 49, y + 33), f"{stop['order']:02d}",
                  font=load_font(18), fill="#ffffff", anchor="mm")
        draw.text((panel_x + 86, y + 13), stop["label"],
                  font=load_font(22), fill="#40352e")
        draw.text((panel_x + 86, y + 49), stop["via"],
                  font=load_font(17), fill="#a35c32")
        draw.text((panel_x + 86, y + 78), stop["look"],
                  font=load_font(17), fill="#6b5a4d")
    footer_y = top + height + 25
    draw.text((margin, footer_y),
              "从左侧公卫、次卧顺行，经阳台回客厅；看完右侧房间后再进厨房，最后从原入户门出去。",
              font=load_font(21), fill="#624331")
    draw.text((margin, footer_y + 38),
              "单入口房间从同一门进出；次卧 → 阳台 → 客厅这一段贯通前行，不回头。",
              font=load_font(19), fill="#a13c31")
    draw.text((margin, footer_y + 73),
              "本图标明第一人称参观顺序；尚未生成连续视频。",
              font=load_font(18), fill="#766356")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output)
    print(json.dumps({"status": "ok", "output": str(args.output.resolve()),
                      "size": canvas.size, "route_validation": validation}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
