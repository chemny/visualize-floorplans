"""One explicit design scheme shared by image tasks and their approvals."""
import json
import hashlib


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",", ":")).encode()).hexdigest()


def chosen_style(design):
    selected = design.get("selected_style")
    options = {item["id"]: item for item in design.get("style_options", [])}
    if selected == "custom":
        custom = design.get("custom_style", {})
        if not isinstance(custom,dict) or not isinstance(custom.get("name"),str) or not custom["name"].strip():
            raise ValueError("custom_style requires a name and explicit description")
        if not isinstance(custom.get("description"),str) or not custom["description"].strip():
            raise ValueError("custom_style requires description")
        for field in ("palette","materials"):
            values = custom.get(field,[])
            if not isinstance(values,list) or not all(isinstance(v,str) and v.strip() for v in values):
                raise ValueError(f"custom_style.{field} must be a list of non-empty strings")
        return {"id":"custom", "name":custom["name"], "palette":custom.get("palette",[]),
                "materials":custom.get("materials",[]), "description":custom["description"]}
    if selected not in options:
        raise ValueError("selected_style must name a default option or custom")
    return options[selected]


def design_block(design, visible_rooms=None):
    chosen = chosen_style(design) if design.get("selected_style") else {}
    # User palette/materials take precedence over defaults; do not emit two
    # conflicting directions into different parts of the same prompt.
    scheme = {"style": chosen.get("name"), "description":chosen.get("description", ""),
              "palette":design.get("palette") or chosen.get("palette",[]),
              "materials":design.get("materials") or chosen.get("materials",[]),
              "household":design.get("household", ""), "budget_tier":design.get("budget_tier", ""),
              "requirements":design.get("requirements",[]), "preserve_furniture":design.get("preserve_furniture",[]),
              "scheme":design.get("scheme",{})}
    scheme["scheme"] = {k:v for k,v in scheme["scheme"].items() if k != "version"}
    scheme["room_schemes"] = {k:v for k,v in design.get("room_schemes",{}).items()
                              if visible_rooms is None or k in visible_rooms}
    return ("Current shared design scheme (user instructions override preset defaults):\n"+
            json.dumps(scheme,ensure_ascii=False,sort_keys=True)+
            "\nUse the same layout, furniture identities and positions, and finishes in every view. "
            "The furnished plan expresses this scheme; it must not design a second furniture layout.")
