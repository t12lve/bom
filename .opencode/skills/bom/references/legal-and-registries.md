# Legal screening, domains and registries

BOM screens; it does not clear. A trademark attorney gives the opinion, and the
client signs. Say this sentence in every report.

## 1. The two classes that matter

| Class | Covers | When it applies |
|---|---|---|
| **9** | software, apps, downloadable programs, SaaS downloaded components | always, if the product is software |
| **42** | SaaS, PaaS, hosting, technical services, design and development | always, if the product runs as a service |

Sometimes adjacent: **35** (business management, advertising — food-cost
management could sit here), **38** (telecoms), **41** (training, content). File
9 + 42 first; add 35 only if the product genuinely does management consulting.

A name can be free in class 9 and blocked in class 42 by another SaaS. Check both,
independently.

## 2. Offices and how to search

| Office | Territory | Search entry | Cost order of magnitude (1 class) |
|---|---|---|---|
| INPI | France | data.inpi.fr | ~190 EUR, +40 EUR per extra class |
| EUIPO | EU 27 | euipo.europa.eu/eSearch | ~850 EUR, +50 EUR 2nd class, +150 EUR 3rd+ |
| USPTO | United States | tmsearch.uspto.gov | ~250-350 USD per class (TEAS) |
| WIPO | Madrid system | branddb.wipo.int | varies by country designation |
| TMview | aggregated | tmdn.org/tmview | free |

Costs are indicative, change every year, and exclude attorney fees. Never quote
them as fact — point the client at the office page.

### Method

1. **Identical** search, exact string, classes 9 and 42.
2. **Near-identical**: same root, one letter changed, phonetic equivalent
   (`prixrank` / `prirank` / `prix-ranc`).
3. **Similar goods**: same class, same consumer, confusingly similar sign. This
   is where most conflicts live; an identical search alone is not a clearance.
4. **Status**: a dead or expired mark is not a risk; a pending application is.
   Record mark number, owner, class, filing date, status.
5. **Territory**: a French mark does not block the US, but EUIPO covers France.
   If the client sells in the EU, EUIPO is the binding search.

### Risk reading

| Finding | Reading |
|---|---|
| Identical mark, live, classes 9/42, same territory | stop, do not spend |
| Near-identical, same class, same consumer | high risk, attorney opinion required |
| Identical, different class, different consumer | low-medium, proceed with a distinct logo |
| Dead / expired mark | no obstacle, keep the evidence |
| Descriptive phrase | registrable only with acquired distinctiveness — expect an objection |

BOM's automatic pre-filter removes bare dictionary nouns, known brands, common
first names and generic tech words. That prevents the obvious mistakes; it does
not replace steps 1-5.

## 3. Domain strategy

| TLD | Use it for | Reality check |
|---|---|---|
| `.com` | the brand, always | 7/25 of the technique pillar; buy it or change the name |
| `.fr` | French trust, local SEO | AFNIC rules: presence in the EU required |
| `.app` | product/PWA | HTTPS enforced by the registry (HSTS preload) |
| `.ai` | AI positioning | expensive, sometimes 4-5 figures, often parked |
| `.io` | developer audience | expensive, and `.io` has a geopolitical expiry risk |

Rules:

- If `.com` is registered and parked, check the price before falling in love.
  A 4-figure ask can still be rational; a 5-figure ask for an unproven name is
  not.
- Never build on a hyphen. `prix-rank.com` loses every dictation test.
- Buy the obvious misspellings only if the brand is already funded; otherwise it
  is a tax on a name nobody knows yet.
- Consider the `.fr` even for an English-first product if the company is French:
  it is cheap, and it blocks a local squatter.

RDAP is authoritative on registration and registrar, not on *availability to
you*: a domain can be registered and expiring, or reserved by the registry.

## 4. Code registries

| Registry | Endpoint used by BOM | What a collision means |
|---|---|---|
| GitHub account | `api.github.com/users/{name}` | a developer or org owns the handle; you will be `{name}app` |
| GitHub repos | `api.github.com/search/repositories?q={name}+in:name` | the string exists in project names; SERP noise |
| npm | `registry.npmjs.org/{name}` | `npm install {name}` would not be yours |
| PyPI | `pypi.org/pypi/{name}/json` | same for `pip install` |
| crates.io | `crates.io/api/v1/crates/{name}` | same for `cargo add` |

Unauthenticated GitHub search allows ~10 requests/minute. BOM catches `403` and
records `inconnu` — that is not a pass. Re-run later, or reduce `--workers`.

## 5. App stores and Product Hunt

- **App Store**: iTunes Search API, country `fr`. An exact name in the same
  category is fatal; another category is a warning. The API also reveals whether
  the name is already a consumer product with reviews.
- **Google Play**: no public search API. Verify manually, in the target
  country, with the exact string.
- **Product Hunt**: no public API without a token. A previous launch with the
  same name means the name is taken in the eyes of your buyers, whatever the
  trademark says.

## 6. Social handles

Check at minimum: X, LinkedIn (company page), YouTube, Instagram, TikTok, GitHub.
A split handle (`@getname`, `@name_app`, `@namehq`) fragments the entity and
costs GEO points later. Prefer a name whose handle is free everywhere, or accept
one consistent prefix across all platforms.

Free checkers exist but throttle; do the final check by hand in a private window.

## 7. What never to do

- Do not file before the domain and the handles are secured — you will be
  negotiating from weakness.
- Do not file in class 9 only and launch a SaaS; class 42 is the SaaS class.
- Do not rely on a `.fr` mark for an EU-wide business.
- Do not tell the client "the name is free". Say "no blocking mark found in the
  searches below, on this date, in these classes and territories".
- Do not let an LLM answer the trademark question. It will invent a mark number.
