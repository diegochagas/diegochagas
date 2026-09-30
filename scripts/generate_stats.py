"""Generate assets/stats.svg and assets/top-langs.svg from the GitHub GraphQL API."""
import json
import os
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "diegochagas")
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection { totalCommitContributions restrictedContributionsCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

BG, BORDER, TITLE, TEXT = "#151515", "#e4e2e2", "#fff", "#9f9f9f"
FONT = "font-family:'Segoe UI',Ubuntu,Sans-Serif"


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "stats-gen"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]


def card(width, height, title, body):
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="4.5" '
        f'fill="{BG}" stroke="{BORDER}"/>'
        f'<text x="25" y="35" style="{FONT};font-weight:600;font-size:18px" fill="{TITLE}">'
        f'{escape(title)}</text>{body}</svg>'
    )


def stats_svg(u):
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    c = u["contributionsCollection"]
    rows = [
        ("Total Stars", stars),
        ("Commits (last year)", c["totalCommitContributions"] + c["restrictedContributionsCount"]),
        ("Pull Requests", u["pullRequests"]["totalCount"]),
        ("Issues", u["issues"]["totalCount"]),
        ("Followers", u["followers"]["totalCount"]),
    ]
    body = "".join(
        f'<text x="25" y="{65 + i * 22}" style="{FONT};font-size:14px" fill="{TEXT}">{escape(k)}:</text>'
        f'<text x="220" y="{65 + i * 22}" style="{FONT};font-weight:700;font-size:14px" fill="{TITLE}">{v}</text>'
        for i, (k, v) in enumerate(rows)
    )
    return card(300, 180, f"{u['name'] or USER}'s GitHub Stats", body)


def langs_svg(u):
    totals, colors = {}, {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            totals[n] = totals.get(n, 0) + e["size"]
            colors[n] = e["node"]["color"] or "#888"
    top = sorted(totals.items(), key=lambda x: -x[1])[:7]
    whole = sum(s for _, s in top) or 1
    body, y = "", 65
    for name, size in top:
        pct = size / whole * 100
        body += (
            f'<text x="25" y="{y}" style="{FONT};font-size:13px" fill="{TEXT}">{escape(name)}</text>'
            f'<rect x="120" y="{y - 10}" width="120" height="8" rx="4" fill="#333"/>'
            f'<rect x="120" y="{y - 10}" width="{120 * pct / 100:.1f}" height="8" rx="4" fill="{colors[name]}"/>'
            f'<text x="250" y="{y}" style="{FONT};font-size:12px" fill="{TEXT}">{pct:.1f}%</text>'
        )
        y += 16
    return card(300, max(180, y + 10), "Most Used Languages", body)


if __name__ == "__main__":
    user = fetch()
    os.makedirs("assets", exist_ok=True)
    open("assets/stats.svg", "w").write(stats_svg(user))
    open("assets/top-langs.svg", "w").write(langs_svg(user))
