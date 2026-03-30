from src.parser.awr_parser import parse_awr_file


def print_section_preview(
    name: str, info: dict, lines: list[str], max_lines: int = 40
) -> None:
    start = info["start_line"] - 1
    end = min(info["end_line"], start + max_lines)

    print(f"\n{'=' * 80}")
    print(f"SECTION: {name}")
    print(
        f"START: {info['start_line']}  END: {info['end_line']}  PATTERN: {info['matched_pattern']}"
    )
    print(f"{'-' * 80}")

    for i, line in enumerate(lines[start:end], start=info["start_line"]):
        print(f"{i:04d}: {line}")

    if info["end_line"] > end:
        print(f"... truncated after {max_lines} lines ...")


if __name__ == "__main__":
    result = parse_awr_file("data/input/sample_awr_01.out")

    with open("data/input/sample_awr_01.out", encoding="utf-8", errors="replace") as f:
        raw_lines = f.read().replace("\r\n", "\n").replace("\r", "\n").splitlines()

    for section_name in ("cpu", "waits"):
        info = result.sections_found.get(section_name)
        if info:
            print_section_preview(section_name, info, raw_lines, max_lines=40)
