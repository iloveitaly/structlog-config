def _collect_slow_reports(terminalreporter, threshold: float) -> list:
    slow = []
    for report in terminalreporter.stats.get("passed", []):
        if report.when == "call" and report.duration >= threshold:
            slow.append(report)
    return sorted(slow, key=lambda r: r.duration, reverse=True)
