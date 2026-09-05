"""Rebuild species_metadata.py from the individual COTW Wiki animal pages."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://thehuntercotw.fandom.com/api.php"
OUTPUT_PATH = Path(__file__).with_name("species_metadata.py")

RESERVE_IDS = {
    "Hirschfelden Hunting Reserve": 0,
    "Layton Lake District": 1,
    "Medved-Taiga National Park": 2,
    "Medved Taiga": 2,
    "Vurhonga Savanna": 3,
    "Parque Fernando": 4,
    "Yukon Valley": 6,
    "Yukon Valley Nature Reserve": 6,
    "Cuatro Colinas Game Reserve": 8,
    "Silver Ridge Peaks": 9,
    "Te Awaroa National Park": 10,
    "Rancho del Arroyo": 11,
    "Mississippi Acres Preserve": 12,
    "Revontuli Coast": 13,
    "New England Mountains": 14,
    "Emerald Coast": 16,
    "Sundarpatan": 17,
    "Salzwiesen Park": 18,
    "Askiy Ridge Hunting Preserve": 19,
    "Tòrr nan Sithean": 20,
    "Torr nan Sithean": 20,
    "Intisuyu": 21,
}

COMMON_FURS = {
    "Brown", "Dark Brown", "Light Brown", "Grey", "Gray", "Tan",
    "Red Brown", "Blonde", "Common", "Common Brown", "Common Grey",
    "Common Gray", "Common Red", "Common Black", "Common White",
}


def api_query(params: dict[str, str]) -> dict:
    query = urlencode({**params, "format": "json", "formatversion": "2"})
    request = Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": "COTWTracker metadata rebuild/1.0"},
    )
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def animal_titles() -> list[str]:
    result = api_query({
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:Animal",
        "cmtype": "page",
        "cmlimit": "500",
    })
    return [item["title"] for item in result["query"]["categorymembers"]]


def page_sources(titles: list[str]) -> dict[str, str]:
    result = api_query({
        "action": "query",
        "titles": "|".join(titles),
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
    })
    sources = {}
    for page in result["query"]["pages"]:
        revisions = page.get("revisions", [])
        if revisions:
            sources[page["title"]] = revisions[0]["slots"]["main"]["content"]
    return sources


def field(infobox: str, name: str) -> str:
    match = re.search(
        rf"^\|\s*{re.escape(name)}\s*=\s*(.*?)(?=^\|\s*[^=\n]+\s*=|\Z)",
        infobox,
        re.MULTILINE | re.DOTALL,
    )
    return " ".join(match.group(1).split()) if match else ""


def clean_link(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"\[\[([^]|]+)(?:\|[^]]+)?\]\]", r"\1", value)
    value = re.sub(r"<[^>]+>|'{2,}", "", value)
    return value.replace(",", "\n").strip()


def parse_species(title: str, source: str) -> list[tuple[int, str, dict]]:
    match = re.search(r"\{\{Infobox[_ ]animal(.*?)}}", source, re.DOTALL)
    if not match:
        return []
    infobox = re.sub(r"(?<!\n)\|", "\n|", match.group(1))
    difficulty = [int(value) for value in re.findall(r"\d+", field(infobox, "difficulty"))]
    if not difficulty:
        difficulty = [int(value) for value in re.findall(r"\d+", field(infobox, "class"))]
    scores = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", field(infobox, "score"))]
    if not difficulty or len(scores) < 3:
        return []
    max_level = max(value for value in difficulty if value <= 9)
    diamond_min = scores[2]

    fur_text = clean_link(
        field(infobox, "fur")
        or field(infobox, "skin")
        or field(infobox, "fu")
    )
    fur_text = re.sub(r"Fabled Exclusive\s*:\s*.*", "", fur_text, flags=re.IGNORECASE)
    rare_furs = []
    for value in fur_text.split(","):
        value = value.strip()
        if value and value not in COMMON_FURS and value not in rare_furs:
            rare_furs.append(value)

    locations = clean_link(field(infobox, "locations"))
    reserve_names = [name.strip() for name in locations.split("\n")]
    great_one = "Category:Animals with Great Ones" in source
    result = []
    for reserve_name in reserve_names:
        reserve_id = RESERVE_IDS.get(reserve_name)
        if reserve_id is None:
            continue
        result.append((reserve_id, title, {
            "max_level": max_level,
            "diamond_min": diamond_min,
            "rare_furs": rare_furs,
            "great_one": great_one,
        }))
    return result


def format_value(value):
    if isinstance(value, float):
        return f"{value:.2f}"
    return repr(value)


def write_metadata(metadata: dict[int, dict[str, dict]]) -> None:
    lines = ["SPECIES_METADATA = {"]
    for reserve_id in sorted(metadata):
        lines.append(f"    {reserve_id}: {{")
        for species in sorted(metadata[reserve_id]):
            info = metadata[reserve_id][species]
            lines.append(
                f"        {json.dumps(species, ensure_ascii=False)}: "
                f"{{\"max_level\": {info['max_level']}, "
                f"\"diamond_min\": {format_value(info['diamond_min'])}, "
                f"\"rare_furs\": {json.dumps(info['rare_furs'], ensure_ascii=False)}, "
                f"\"great_one\": {info['great_one']}}},"
            )
        lines.append("    },")
    lines.append("}")
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    titles = animal_titles()
    metadata: dict[int, dict[str, dict]] = {}
    parsed_pages = 0
    for start in range(0, len(titles), 50):
        sources = page_sources(titles[start:start + 50])
        for title, source in sources.items():
            entries = parse_species(title, source)
            if not entries:
                continue
            parsed_pages += 1
            for reserve_id, species, info in entries:
                metadata.setdefault(reserve_id, {})[species] = info
    write_metadata(metadata)
    print(
        f"Wrote {parsed_pages} species pages, "
        f"{sum(len(value) for value in metadata.values())} reserve entries, "
        f"{len({name for reserve in metadata.values() for name in reserve})} species."
    )


if __name__ == "__main__":
    main()