def calculate_peer_scores(rows, min_peers=3):
    """Percentile izračuna samo ob vsaj treh primerljivih podjetjih."""
    groups = {}

    for row in rows:
        groups.setdefault(row["sector"], []).append(row)

    for group_rows in groups.values():
        for row in group_rows:
            row["peer_count"] = len(group_rows)
            row["fcf_percentile"] = None
            row["valuation_percentile"] = None
            row["valuation_score"] = None
            row["sector_percentile"] = None
            row["composite_score"] = None

        # Percentil proti eni ali dvema podjetjema ni dovolj zanesljiv.
        if len(group_rows) < min_peers:
            continue

        for row in group_rows:
            fcf_peers = [
                peer["fcf_quality"]
                for peer in group_rows
                if peer.get("fcf_quality") is not None
            ]

            if len(fcf_peers) >= min_peers and row.get("fcf_quality") is not None:
                row["fcf_percentile"] = percentile_score(
                    fcf_peers,
                    row["fcf_quality"],
                    lower_is_better=False,
                )

            metric_name = row["valuation_metric"]["name"]
            valuation_peers = [
                peer["valuation_metric"]["value"]
                for peer in group_rows
                if (
                    peer["valuation_metric"]["name"] == metric_name
                    and peer["valuation_metric"]["value"] is not None
                )
            ]

            if (
                len(valuation_peers) >= min_peers
                and row["valuation_metric"]["value"] is not None
            ):
                row["valuation_percentile"] = percentile_score(
                    valuation_peers,
                    row["valuation_metric"]["value"],
                    lower_is_better=True,
                )
                if row["valuation_percentile"] is not None:
                    row["valuation_score"] = round(
                        row["valuation_percentile"] / 10,
                        1,
                    )

            # Oba percentila sta na lestvici 0–100.
            sector_parts = [
                value
                for value in (
                    row["fcf_percentile"],
                    row["valuation_percentile"],
                )
                if value is not None
            ]

            if sector_parts:
                row["sector_percentile"] = round(
                    sum(sector_parts) / len(sector_parts)
                )

            # Ne ustvarjaj skupne ocene, če ni mogoče oceniti
            # tako kakovosti denarnega toka kot vrednotenja.
            if (
                row["fcf_quality"] is not None
                and row["valuation_score"] is not None
                and row["sector_percentile"] is not None
            ):
                row["composite_score"] = round(
                    row["fcf_quality"] * 0.50
                    + row["valuation_score"] * 0.30
                    + (row["sector_percentile"] / 10) * 0.20,
                    1,
                )

    return rows
