"""Generate synthetic change requests with known ground-truth facts.

Output: data/synthetic/change_requests.jsonl. Used for load tests, volume demos
and as an (easier, template-phrased) extraction benchmark next to the
hand-written golden set. All entities and jurisdictions are fictional.

    .venv/bin/python scripts/generate_synthetic.py --n 40 --seed 7
"""

import argparse
import json
import random
from pathlib import Path

from faker import Faker

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic" / "change_requests.jsonl"

PRODUCTS = [
    ("new_product", "Payments", "a {adj} payment wallet"),
    ("new_product", "Consumer Banking", "a {adj} savings account"),
    ("feature_change", "Consumer Banking", "a {adj} card feature"),
    ("new_customer_segment", "Commercial Banking", "accounts for a {adj} client segment"),
    ("new_geography", "Commercial Banking", "{adj} corporate payments in a new market"),
    ("vendor_onboarding", "Operations", "a {adj} operations vendor"),
]
ADJ = ["flexible", "next-generation", "simplified", "premium", "digital-first", "low-cost"]
CUSTOMERS = {
    "retail": "retail consumers", "small_business": "small businesses", "corporate": "corporate clients",
    "pep": "politically exposed persons", "msb": "money services businesses", "non_resident": "non-resident customers",
    "nonprofit": "non-profit organisations", "high_net_worth": "high-net-worth individuals",
}
CHANNELS = {"branch": "in branch", "online": "through online banking", "mobile": "in the mobile app",
            "api": "via API integration", "agent": "through agents", "phone": "by phone"}
FOREIGN = ["Veridia", "Tessaly", "Mirandor", "Brightland", "Calderra", "Luminor", "Nordhaven", "Westmarch", "Norvexia"]
ROLES = {"kyc": "performs KYC checks", "payments_processing": "acts as payment processor",
         "custody": "provides custody of assets", "transaction_monitoring": "performs transaction monitoring",
         "marketing": "markets the product", "it_hosting": "provides IT hosting"}
CONTROLS = {"C-KYC-01": "eKYC with liveness", "C-SAN-01": "real-time sanctions screening",
            "C-LIM-01": "transaction limits", "C-TM-01": "transaction monitoring scenarios",
            "C-EDD-01": "enhanced due diligence", "C-TPV-01": "vendor due diligence with right to audit",
            "C-FRD-01": "device fingerprinting", "C-TRV-01": "travel rule checks"}


def make_case(i: int, rng: random.Random, fake: Faker) -> dict:
    ctype, line, tmpl = rng.choice(PRODUCTS)
    cust = rng.sample(list(CUSTOMERS), rng.randint(1, 2))
    chans = rng.sample(list(CHANNELS), rng.randint(1, 2))
    foreign = rng.sample(FOREIGN, rng.choice([0, 0, 1, 2]))
    geos = ["Avalon", *foreign]
    flags = {"cross_border": bool(foreign), "cash": rng.random() < 0.15, "crypto": rng.random() < 0.1,
             "instant_payments": rng.random() < 0.25, "anonymous_or_prepaid": rng.random() < 0.1}
    roles = rng.sample(list(ROLES), rng.choice([0, 0, 1]))
    vendor = fake.company().replace(",", "") if roles else None
    value = rng.choice([500_000, 2_000_000, 8_000_000, 15_000_000, 35_000_000, 75_000_000])
    ctrls = rng.sample(list(CONTROLS), rng.randint(0, 3))

    product = tmpl.format(adj=rng.choice(ADJ))
    parts = [f"We propose {product} for {' and '.join(CUSTOMERS[c] for c in cust)},",
             f"offered {' and '.join(CHANNELS[c] for c in chans)}."]
    parts.append(f"Customers are located in {', '.join(geos)}." if foreign else "Activity is limited to Avalon.")
    if flags["cross_border"]:
        parts.append("Payments will be cross-border.")
    if flags["cash"]:
        parts.append("Customers can fund the product with cash.")
    if flags["crypto"]:
        parts.append("The product includes crypto asset transfers.")
    if flags["instant_payments"]:
        parts.append("Payments settle instantly.")
    if flags["anonymous_or_prepaid"]:
        parts.append("It is a prepaid, reloadable instrument.")
    if roles:
        parts.append(f"Our partner {vendor} {ROLES[roles[0]]}.")
    parts.append(f"Expected monthly value is USD {value:,}.")
    if ctrls:
        parts.append("Controls: " + ", ".join(CONTROLS[c] for c in ctrls) + ".")
    return {
        "id": f"S{i:03d}",
        "title": f"{product[0].upper()}{product[1:]} ({fake.word()})",
        "change_type": ctype,
        "business_line": line,
        "description": parts[0].rstrip(","),
        "document": " ".join(parts),
        "expected": {"facts": {"customer_types": cust, "geographies": geos, "channels": chans,
                               "third_party_roles": roles, **flags, "monthly_value_usd": value, "controls": ctrls}},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    fake = Faker()
    Faker.seed(args.seed)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for i in range(1, args.n + 1):
            f.write(json.dumps(make_case(i, rng, fake)) + "\n")
    print(f"wrote {args.n} cases to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
